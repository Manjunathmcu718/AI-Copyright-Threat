from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Iterable, List
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from backend.discovery import USER_AGENT, is_public_http_url


ALLOWED_DIRECT_MEDIA_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
MAX_CANDIDATE_BYTES = 75 * 1024 * 1024


def normalize_candidate_urls(urls: Iterable[str]) -> List[str]:
    normalized: List[str] = []
    seen: set[str] = set()
    for url in urls:
        cleaned = str(url or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized[:6]


def media_suffix(url: str) -> str:
    return Path(urlparse(url).path).suffix.lower()


def validate_direct_media_url(url: str) -> tuple[bool, str]:
    suffix = media_suffix(url)
    if suffix not in ALLOWED_DIRECT_MEDIA_SUFFIXES:
        return (
            False,
            "Only direct public video file URLs are accepted for URL verification. HLS/DASH playlists, webpages, and hidden players are not downloaded.",
        )

    ok, reason = is_public_http_url(url)
    if not ok:
        return False, reason

    return True, ""


def candidate_filename(url: str, index: int) -> str:
    suffix = media_suffix(url) or ".mp4"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    return f"url_candidate_{index + 1:02d}_{digest}{suffix}"


def download_direct_media_candidate(url: str, destination_dir: Path, index: int, timeout: float = 14.0) -> Dict[str, object]:
    ok, reason = validate_direct_media_url(url)
    if not ok:
        raise ValueError(reason)

    destination_dir.mkdir(parents=True, exist_ok=True)
    target = destination_dir / candidate_filename(url, index)
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "video/*,application/octet-stream;q=0.8,*/*;q=0.2",
        },
    )

    with urlopen(request, timeout=timeout) as response:
        final_url = response.geturl()
        ok, reason = is_public_http_url(final_url)
        if not ok:
            raise ValueError(reason)

        content_type = response.headers.get("content-type", "")
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > MAX_CANDIDATE_BYTES:
            raise ValueError(f"Candidate media is larger than {MAX_CANDIDATE_BYTES // (1024 * 1024)} MB.")

        total = 0
        with target.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 512)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_CANDIDATE_BYTES:
                    handle.close()
                    target.unlink(missing_ok=True)
                    raise ValueError(f"Candidate media exceeded {MAX_CANDIDATE_BYTES // (1024 * 1024)} MB.")
                handle.write(chunk)

    return {
        "url": url,
        "finalUrl": final_url,
        "fileName": target.name,
        "path": str(target),
        "bytes": total,
        "contentType": content_type,
    }


def url_verification_boundary() -> List[str]:
    return [
        "Requires authorization confirmation before candidate media ingestion",
        "Direct public media files only",
        "No HLS/DASH stream capture or segment downloading",
        "No login, CAPTCHA, DRM, Cloudflare, paywall, or hidden-site bypass",
        "Downloaded candidate is used only for Content DNA comparison and human-reviewed evidence",
    ]
