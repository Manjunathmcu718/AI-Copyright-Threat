from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.discovery import scan_public_sources, search_public_web
from backend.investigator import build_investigation
from backend.media_scan import scan_folder
from backend.url_media import (
    download_direct_media_candidate,
    normalize_candidate_urls,
    url_verification_boundary,
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
PROTECTED_DIR.mkdir(parents=True, exist_ok=True)
CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)
URL_CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)


class DiscoveryScanRequest(BaseModel):
    title: str
    aliases: List[str] = Field(default_factory=list)
    seedUrls: List[str] = Field(default_factory=list)
    authorizedDomains: List[str] = Field(default_factory=list)
    maxPages: int = 6


class DiscoverySearchRequest(BaseModel):
    title: str
    aliases: List[str] = Field(default_factory=list)
    authorizedDomains: List[str] = Field(default_factory=list)
    sourceDomains: List[str] = Field(default_factory=list)
    providers: List[str] = Field(default_factory=lambda: ["brave", "bing", "google", "commoncrawl"])
    maxResults: int = 12
    deepScanPages: int = 6
    expandDepth: int = 1
    expandPages: int = 16
    perDomainPageLimit: int = 4
    country: str = "IN"
    searchLang: str = "en"


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


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
    protected_path = PROTECTED_DIR / protected.filename
    protected_path.parent.mkdir(parents=True, exist_ok=True)
    with protected_path.open("wb") as handle:
        while chunk := await protected.read(65536):
            handle.write(chunk)

    candidate_dir = CANDIDATE_DIR
    candidate_dir.mkdir(parents=True, exist_ok=True)

    for candidate in candidates:
        if not candidate.filename:
            continue
        target = candidate_dir / candidate.filename
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
    protected_path = PROTECTED_DIR / protected_name
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
        result["evidenceLevel"] = 4
        result["evidenceLevelLabel"] = "Multimodal match"

    return {
        "scanned": len(results),
        "results": results,
        "investigation": build_investigation(results),
        "downloadedCandidates": downloaded,
        "rejectedCandidates": rejected,
        "boundary": url_verification_boundary(),
    }


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
        authorized_domains=request.authorizedDomains,
        source_domains=request.sourceDomains,
        providers=request.providers,
        max_results=request.maxResults,
        deep_scan_pages=request.deepScanPages,
        expand_depth=request.expandDepth,
        expand_pages=request.expandPages,
        per_domain_page_limit=request.perDomainPageLimit,
        country=request.country,
        search_lang=request.searchLang,
    )
