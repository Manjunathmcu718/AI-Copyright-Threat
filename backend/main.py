from __future__ import annotations

import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.discovery import is_public_http_url, scan_public_sources, search_public_web
from backend.demo_copy import create_controlled_copy
from backend.investigator import build_investigation
from backend.media_scan import scan_folder
from backend.url_media import (
    download_direct_media_candidate,
    normalize_candidate_urls,
    url_verification_boundary,
    validate_direct_media_url,
)


app = FastAPI(title="CineShield local scan API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parents[1]
PROTECTED_DIR = BASE_DIR / "data" / "protected"
CANDIDATE_DIR = BASE_DIR / "data" / "candidates"
URL_CANDIDATE_DIR = BASE_DIR / "data" / "url_candidates"
DEMO_COPY_DIR = BASE_DIR / "data" / "demo_copies"
CONTROLLED_PUBLIC_SOURCE_MEDIA_LIMIT = 8
CONTROLLED_PUBLIC_SOURCE_RETRY_DELAYS = (0, 4, 10)


def load_local_env() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_local_env()
# An optional owned-source connector is deployment configuration, not application
# code. With no configured connector, discovery relies on public search providers.
CONTROLLED_PUBLIC_SOURCE_URL = os.environ.get("CINESHIELD_CONTROLLED_SOURCE_URL", "").strip().rstrip("/")
PROTECTED_DIR.mkdir(parents=True, exist_ok=True)
CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)
URL_CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)
DEMO_COPY_DIR.mkdir(parents=True, exist_ok=True)


class DiscoveryScanRequest(BaseModel):
    title: str
    aliases: List[str] = Field(default_factory=list)
    seedUrls: List[str] = Field(default_factory=list)
    authorizedDomains: List[str] = Field(default_factory=list)
    maxPages: int = 6


class DiscoverySearchRequest(BaseModel):
    title: str
    aliases: List[str] = Field(default_factory=list)
    seedUrls: List[str] = Field(default_factory=list)
    authorizedDomains: List[str] = Field(default_factory=list)
    sourceDomains: List[str] = Field(default_factory=list)
    riskTerms: List[str] = Field(default_factory=list)
    providers: List[str] = Field(default_factory=lambda: ["brave", "bing", "google", "commoncrawl"])
    maxQueryVariants: int = 6
    maxResults: int = 12
    deepScanPages: int = 6
    expandDepth: int = 1
    expandPages: int = 16
    perDomainPageLimit: int = 4
    country: str = "IN"
    searchLang: str = "en"


class OriginalLinkSearchRequest(BaseModel):
    originalUrl: str
    title: str = ""


def inferred_work_title(value: str) -> str:
    """Use a readable title when a controlled discovery run has no user label."""
    title = Path(value or "protected video").stem.replace("_", " ").replace("-", " ")
    title = re.sub(r"\s+", " ", title).strip()
    return title or "protected video"


def direct_media_targets(discovery: Dict[str, object]) -> List[Dict[str, str]]:
    """Collect supported public direct-video references from scanned pages."""
    allowed = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
    targets: List[Dict[str, str]] = []
    seen: set[str] = set()

    def add_reference(reference: object, page_url: object, host: object) -> None:
        if not isinstance(reference, dict):
            return
        url = str(reference.get("url") or "").strip()
        if not url or Path(url.split("?", 1)[0]).suffix.lower() not in allowed or url in seen:
            return
        seen.add(url)
        targets.append(
            {
                "url": url,
                "pageUrl": str(page_url or "").strip(),
                "host": str(host or "").strip(),
            }
        )

    for source in discovery.get("sourcesScanned", []):
        if not isinstance(source, dict):
            continue
        for reference in source.get("mediaReferenceDetails", []):
            add_reference(reference, source.get("url"), source.get("host"))

    for candidate in discovery.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        for reference in candidate.get("mediaReferences", []):
            add_reference(reference, candidate.get("sourcePage") or candidate.get("url"), candidate.get("host"))

    return targets[:CONTROLLED_PUBLIC_SOURCE_MEDIA_LIMIT]


def configured_source_discovery(work_title: str, source_url: str) -> Dict[str, object]:
    """Discover public watch pages before collecting their direct video evidence.

    The first bounded pass reads the public landing page and sitemap.  Its same-host
    links are then used as explicit seeds for one more bounded pass, so a video
    remains discoverable even when the page title differs from the uploaded file.
    """
    initial = scan_public_sources(
        title=work_title,
        aliases=[],
        seed_urls=[source_url],
        authorized_domains=[],
        max_pages=8,
        include_same_host_links=True,
    )

    page_urls: List[str] = []
    seen_pages: set[str] = set()
    for source in initial.get("sourcesScanned", []):
        if not isinstance(source, dict):
            continue
        for page_url in source.get("sameHostPages", []):
            cleaned = str(page_url or "").strip()
            if cleaned and cleaned not in seen_pages:
                seen_pages.add(cleaned)
                page_urls.append(cleaned)
            if len(page_urls) >= 7:
                break
        if len(page_urls) >= 7:
            break

    if not page_urls:
        return initial

    expanded = scan_public_sources(
        title=work_title,
        aliases=[],
        seed_urls=[source_url, *page_urls],
        authorized_domains=[],
        max_pages=8,
    )

    merged_sources: List[Dict[str, object]] = []
    seen_source_urls: set[str] = set()
    for report in (initial, expanded):
        for source in report.get("sourcesScanned", []):
            if not isinstance(source, dict):
                continue
            key = str(source.get("url") or "").strip()
            if key and key in seen_source_urls:
                continue
            if key:
                seen_source_urls.add(key)
            merged_sources.append(source)

    combined = dict(expanded)
    combined["sourcesScanned"] = merged_sources
    combined["seedCount"] = len({source_url, *page_urls})
    combined["sitemapPagesDiscovered"] = int(initial.get("sitemapPagesDiscovered", 0)) + int(
        expanded.get("sitemapPagesDiscovered", 0)
    )
    return combined


def public_media_discovery(work_title: str) -> Dict[str, object]:
    """Use an external owned-source connector when present, else public indexes."""
    if CONTROLLED_PUBLIC_SOURCE_URL:
        return configured_source_discovery(work_title, CONTROLLED_PUBLIC_SOURCE_URL)

    return search_public_web(
        title=work_title,
        aliases=[],
        seed_urls=[],
        authorized_domains=[],
        providers=["brave", "bing", "google", "commoncrawl"],
        query_limit=4,
        max_results=8,
        deep_scan_pages=6,
        expand_depth=1,
        expand_pages=12,
        per_domain_page_limit=3,
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/discovery/original-link")
def search_from_original_link(request: OriginalLinkSearchRequest) -> dict:
    """Search indexed pages using a public original page's title or a supplied title."""
    original_url = request.originalUrl.strip()
    allowed, reason = is_public_http_url(original_url)
    if not allowed:
        raise HTTPException(status_code=400, detail=reason)

    # Metadata access can fail for subscription sites; a user-supplied title is
    # a legitimate fallback, but never implies access to the underlying video.
    page = scan_public_sources(title="original", aliases=[], seed_urls=[original_url], max_pages=1)
    sources = page.get("sourcesScanned", [])
    source = sources[0] if sources else {}
    page_title = str(source.get("title") or "").strip() if source.get("ok") else ""
    explicit_title = request.title.strip()
    title = explicit_title or re.split(r"\s+[|–—]\s+", page_title, maxsplit=1)[0].strip()
    if not title or title.lower() in {"netflix", "watch netflix", (urlparse(original_url).hostname or "").lower()}:
        raise HTTPException(status_code=400, detail="Could not read a usable title from the original page. Enter the movie title and try again.")

    original_host = urlparse(original_url).hostname or ""
    discovery = search_public_web(
        title=title,
        aliases=[],
        seed_urls=[],
        authorized_domains=[original_host],
        providers=["brave"],
        query_limit=6,
        max_results=12,
        deep_scan_pages=4,
        expand_depth=0,
        expand_pages=0,
    )
    return {
        "originalUrl": original_url,
        "originalPageAccessible": bool(source.get("ok")),
        "originalPageError": str(source.get("error") or ""),
        "title": title,
        "titleSource": "provided" if explicit_title else "page metadata",
        "discovery": discovery,
        "verificationStatus": "UNVERIFIED_METADATA_LEADS",
    }


@app.post("/api/content/register")
async def register_content(file: UploadFile = File(...)) -> dict:
    destination = PROTECTED_DIR / file.filename
    if not file.filename:
        raise ValueError("No file uploaded")
    with destination.open("wb") as handle:
        while chunk := await file.read(65536):
            handle.write(chunk)
    return {"ok": True, "path": str(destination), "filename": file.filename}


@app.post("/api/scan")
async def scan_content(protected: UploadFile = File(...), candidates: List[UploadFile] = File(...)) -> dict:
    protected_name = Path(protected.filename or "").name
    selected_candidates = [candidate for candidate in candidates if candidate.filename]
    if not protected_name:
        raise HTTPException(status_code=400, detail="Original video file is required.")
    if not selected_candidates:
        raise HTTPException(status_code=400, detail="At least one candidate video is required.")

    # Every local comparison uses an empty temporary workspace.  This prevents a
    # previous candidate upload from being included in a later result.
    with tempfile.TemporaryDirectory(prefix="cineshield-local-scan-") as temporary_dir:
        run_dir = Path(temporary_dir)
        protected_path = run_dir / "protected" / protected_name
        protected_path.parent.mkdir(parents=True, exist_ok=True)
        with protected_path.open("wb") as handle:
            while chunk := await protected.read(65536):
                handle.write(chunk)

        candidate_dir = run_dir / "candidates"
        candidate_dir.mkdir(parents=True, exist_ok=True)
        for candidate in selected_candidates:
            target = candidate_dir / Path(candidate.filename or "candidate.mp4").name
            with target.open("wb") as handle:
                while chunk := await candidate.read(65536):
                    handle.write(chunk)

        results = scan_folder(protected_path, candidate_dir)

    return {"scanned": len(results), "results": results, "investigation": build_investigation(results)}


@app.post("/api/scan/url-candidates")
async def scan_url_candidates(protected: UploadFile = File(...), request: str = Form(...)) -> dict:
    try:
        payload = json.loads(request or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid URL verification request JSON.") from exc

    if not payload.get("authorizationConfirmed"):
        raise HTTPException(
            status_code=400,
            detail="URL candidate verification requires authorization confirmation before media ingestion.",
        )

    candidate_urls = normalize_candidate_urls(payload.get("candidateUrls", []))
    if not candidate_urls:
        raise HTTPException(status_code=400, detail="At least one direct candidate media URL is required.")

    if not protected.filename:
        raise HTTPException(status_code=400, detail="Protected video file is required.")

    protected_name = Path(protected.filename).name
    # Keep URL-verification runs isolated so a previously uploaded file cannot
    # be overwritten or held open by another scan on Windows.
    protected_path = PROTECTED_DIR / f"{uuid4().hex}_{protected_name}"
    protected_path.parent.mkdir(parents=True, exist_ok=True)
    with protected_path.open("wb") as handle:
        while chunk := await protected.read(65536):
            handle.write(chunk)

    run_dir = URL_CANDIDATE_DIR / uuid4().hex
    downloaded = []
    rejected = []
    for index, url in enumerate(candidate_urls):
        try:
            downloaded.append(download_direct_media_candidate(url, run_dir, index))
        except Exception as exc:  # noqa: BLE001 - URL ingestion reports per-candidate failures.
            rejected.append({"url": url, "error": str(exc)[:240]})

    results = scan_folder(protected_path, run_dir) if downloaded else []
    source_by_filename = {item["fileName"]: item for item in downloaded}
    for result in results:
        source = source_by_filename.get(str(result.get("fileName", "")), {})
        result["sourceUrl"] = source.get("finalUrl") or source.get("url")
        result["sourceBytes"] = source.get("bytes", 0)
        result["accessType"] = "Authorized direct public media URL"
        result["evidenceLevel"] = 4 if result.get("decision") == "Match" else 3
        result["evidenceLevelLabel"] = "Multimodal match" if result.get("decision") == "Match" else "Content fingerprint"

    investigation = build_investigation(results)
    investigation["sourceBoundary"] = (
        "This investigation uses an authorized direct public candidate media URL. "
        "The downloaded file is used only for Content DNA comparison and human-reviewed evidence."
    )

    return {
        "scanned": len(results),
        "results": results,
        "investigation": investigation,
        "downloadedCandidates": downloaded,
        "rejectedCandidates": rejected,
        "boundary": url_verification_boundary(),
    }


def save_protected_upload(protected: UploadFile) -> Path:
    """Return a unique path reserved for an uploaded protected video."""
    return PROTECTED_DIR / f"{uuid4().hex}_{Path(protected.filename or 'protected-video').name}"


def verify_public_media_targets(
    protected_path: Path,
    discovery: Dict[str, object],
    targets: List[Dict[str, str]],
) -> dict:
    """Run the regular Content-DNA scan on public media exposed by a page.

    The helper is deliberately shared by discovery and a user-supplied link so
    every public-media result gets the same visual, scene, temporal, duration,
    and coverage checks as a local candidate upload.
    """
    if not targets:
        return {
            "foundMatch": False,
            "foundEvidence": False,
            "message": "No verifiable public video was found at this time.",
            "result": None,
            "discovery": discovery,
            "checkedMedia": 0,
            "matchedMedia": 0,
            "rejectedCandidates": [],
            "boundary": url_verification_boundary(),
        }

    rejected: List[Dict[str, str]] = []
    checked = 0
    verified_evidence: List[Dict[str, object]] = []
    for index, target in enumerate(targets):
        run_dir = URL_CANDIDATE_DIR / uuid4().hex
        try:
            downloaded = download_direct_media_candidate(target["url"], run_dir, index)
            result = scan_folder(protected_path, run_dir)[0]
        except Exception as exc:  # noqa: BLE001 - report each public-media failure without stopping the run.
            rejected.append({"url": target["url"], "error": str(exc)[:240]})
            continue

        checked += 1
        decision = str(result.get("decision") or "")
        result.update(
            {
                "sourceUrl": downloaded.get("finalUrl") or target["url"],
                "sourceMediaUrl": downloaded.get("finalUrl") or target["url"],
                "sourcePage": target["pageUrl"],
                "sourceHost": target["host"],
                "sourceBytes": downloaded.get("bytes", 0),
                "accessType": "Authorized direct public media URL",
                "evidenceLevel": 4 if decision == "Match" else 3,
                "evidenceLevelLabel": "Multimodal match" if decision == "Match" else "Partial Content DNA evidence",
            }
        )
        # A clipped candidate can still be a real ordered segment of the work.
        # Preserve it as reviewable evidence instead of presenting it as a full match.
        if decision in {"Match", "Review"}:
            verified_evidence.append(result)

    if not verified_evidence:
        return {
            "foundMatch": False,
            "foundEvidence": False,
            "message": "No matching public copy was found through public discovery.",
            "result": None,
            "discovery": discovery,
            "checkedMedia": checked,
            "matchedMedia": 0,
            "rejectedCandidates": rejected,
            "boundary": url_verification_boundary(),
        }

    strongest_match = max(verified_evidence, key=lambda item: float(item.get("confidence", 0) or 0))
    matched_sources = [
        {
            "pageUrl": str(item.get("sourcePage") or ""),
            "mediaUrl": str(item.get("sourceMediaUrl") or item.get("sourceUrl") or ""),
            "confidence": float(item.get("confidence", 0) or 0),
        }
        for item in verified_evidence
    ]
    investigation = build_investigation([strongest_match])
    investigation["sourceBoundary"] = (
        "CineShield compared publicly exposed direct media with the uploaded original. "
        "The result is evidence for authorized human review."
    )
    return {
        "foundMatch": strongest_match.get("decision") == "Match",
        "foundEvidence": True,
        "message": (
            "Web discovery found a full public-video match."
            if strongest_match.get("decision") == "Match"
            else "Web discovery found partial public-video evidence that requires review."
        ),
        "result": strongest_match,
        "discovery": discovery,
        "checkedMedia": checked,
        "matchedMedia": len(verified_evidence),
        "matchedSources": matched_sources,
        "rejectedCandidates": rejected,
        "investigation": investigation,
        "boundary": url_verification_boundary(),
    }


@app.post("/api/discovery/verify")
async def discover_public_copy(
    protected: UploadFile = File(...),
    authorization_confirmed: bool = Form(False),
    title: str = Form(""),
) -> dict:
    """Discover public direct media and verify it against an authorized original."""
    if not authorization_confirmed:
        raise HTTPException(status_code=400, detail="Public media verification requires authorization confirmation.")
    if not protected.filename:
        raise HTTPException(status_code=400, detail="Protected video file is required.")

    protected_path = save_protected_upload(protected)
    with protected_path.open("wb") as handle:
        while chunk := await protected.read(65536):
            handle.write(chunk)

    work_title = inferred_work_title(title or protected.filename)
    discovery: Dict[str, object] = {}
    # A sleeping connector can need one bounded retry. Public-index runs have
    # their own provider timeouts and must return promptly.
    retry_delays = CONTROLLED_PUBLIC_SOURCE_RETRY_DELAYS if CONTROLLED_PUBLIC_SOURCE_URL else (0,)
    for retry_delay in retry_delays:
        if retry_delay:
            time.sleep(retry_delay)
        discovery = public_media_discovery(work_title)
        if any(bool(source.get("ok")) for source in discovery.get("sourcesScanned", []) if isinstance(source, dict)):
            break
    return verify_public_media_targets(protected_path, discovery, direct_media_targets(discovery))


@app.post("/api/discovery/verify-link")
async def verify_public_link(
    protected: UploadFile = File(...),
    public_url: str = Form(""),
    authorization_confirmed: bool = Form(False),
    title: str = Form(""),
) -> dict:
    """Inspect one public page or direct video URL with the normal DNA pipeline."""
    if not authorization_confirmed:
        raise HTTPException(status_code=400, detail="Public link verification requires authorization confirmation.")
    if not protected.filename:
        raise HTTPException(status_code=400, detail="Protected video file is required.")

    link = str(public_url or "").strip()
    is_public, reason = is_public_http_url(link)
    if not is_public:
        raise HTTPException(status_code=400, detail=reason)

    protected_path = save_protected_upload(protected)
    with protected_path.open("wb") as handle:
        while chunk := await protected.read(65536):
            handle.write(chunk)

    work_title = inferred_work_title(title or protected.filename)
    is_direct_media, _ = validate_direct_media_url(link)
    if is_direct_media:
        parsed = urlparse(link)
        discovery: Dict[str, object] = {
            "sourcesScanned": [],
            "submittedLink": link,
            "mode": "direct-public-media",
        }
        targets = [{"url": link, "pageUrl": link, "host": parsed.netloc.lower()}]
    else:
        # Public free-tier hosts can briefly return 503 while waking. Retry a
        # small fixed number of times before reporting that no public media was found.
        discovery: Dict[str, object] = {}
        for retry_delay in CONTROLLED_PUBLIC_SOURCE_RETRY_DELAYS:
            if retry_delay:
                time.sleep(retry_delay)
            discovery = configured_source_discovery(work_title, link)
            if any(bool(source.get("ok")) for source in discovery.get("sourcesScanned", []) if isinstance(source, dict)):
                break
        targets = direct_media_targets(discovery)

    return verify_public_media_targets(protected_path, discovery, targets)


@app.post("/api/demo/transformed-copy")
async def create_transformed_copy(video: UploadFile = File(...)) -> dict:
    if not video.filename:
        raise HTTPException(status_code=400, detail="Original video file is required.")

    run_dir = DEMO_COPY_DIR / uuid4().hex
    run_dir.mkdir(parents=True, exist_ok=True)
    source_path = run_dir / Path(video.filename).name
    with source_path.open("wb") as handle:
        while chunk := await video.read(65536):
            handle.write(chunk)

    output_path = run_dir / f"{source_path.stem}_test_copy.mp4"
    try:
        create_controlled_copy(source_path, output_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "fileName": output_path.name,
        "downloadUrl": f"/api/demo/transformed-copy/{run_dir.name}/{output_path.name}",
        "message": "Controlled transformed test copy created.",
    }


@app.get("/api/demo/transformed-copy/{run_id}/{file_name}")
def download_transformed_copy(run_id: str, file_name: str):
    from fastapi.responses import FileResponse

    if Path(run_id).name != run_id or Path(file_name).name != file_name:
        raise HTTPException(status_code=400, detail="Invalid test-copy path.")

    output_path = DEMO_COPY_DIR / run_id / file_name
    if not output_path.exists() or output_path.suffix.lower() != ".mp4":
        raise HTTPException(status_code=404, detail="Test copy not found.")
    return FileResponse(output_path, media_type="video/mp4", filename=output_path.name)


@app.get("/api/scan/demo")
def demo_scan() -> dict:
    demo_protected = BASE_DIR / "media" / "real_benchmark" / "videos" / "work_01_original.avi"
    demo_candidates = BASE_DIR / "media" / "real_benchmark" / "videos"
    results = scan_folder(demo_protected, demo_candidates)
    return {"scanned": len(results), "results": results, "investigation": build_investigation(results)}


@app.post("/api/discovery/scan")
def discovery_scan(request: DiscoveryScanRequest) -> dict:
    return scan_public_sources(
        title=request.title,
        aliases=request.aliases,
        seed_urls=request.seedUrls,
        authorized_domains=request.authorizedDomains,
        max_pages=request.maxPages,
    )


@app.post("/api/discovery/search")
def discovery_search(request: DiscoverySearchRequest) -> dict:
    return search_public_web(
        title=request.title,
        aliases=request.aliases,
        seed_urls=request.seedUrls,
        authorized_domains=request.authorizedDomains,
        source_domains=request.sourceDomains,
        risk_terms=request.riskTerms,
        providers=request.providers,
        query_limit=request.maxQueryVariants,
        max_results=request.maxResults,
        deep_scan_pages=request.deepScanPages,
        expand_depth=request.expandDepth,
        expand_pages=request.expandPages,
        per_domain_page_limit=request.perDomainPageLimit,
        country=request.country,
        search_lang=request.searchLang,
    )
