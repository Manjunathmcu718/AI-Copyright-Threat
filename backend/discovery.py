from __future__ import annotations

import html
import json
import os
import ipaddress
import re
import socket
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Callable, Dict, Iterable, List, Optional
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen


MAX_RESPONSE_BYTES = 450_000
USER_AGENT = "CineShieldDiscovery/0.2 (+public-metadata-only)"
BRAVE_SEARCH_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
BING_SEARCH_ENDPOINT = "https://api.bing.microsoft.com/v7.0/search"
GOOGLE_CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"
COMMON_CRAWL_COLLINFO_ENDPOINT = "https://index.commoncrawl.org/collinfo.json"
SEARCH_RESULT_LIMIT = 20
MAX_EXPANSION_PAGES = 32
COMMON_CRAWL_QUERY_LIMIT = 1
_COMMON_CRAWL_COLLECTION_CACHE: List[Dict[str, str]] = []
TRACKING_QUERY_PARAMS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "igshid",
    "ref",
}
MEDIA_HINTS = {
    "watch",
    "stream",
    "video",
    "videos",
    "movie",
    "movies",
    "episode",
    "episodes",
    "series",
    "season",
    "show",
    "download",
    "hd",
    "web-dl",
    "webrip",
    "hdrip",
    "camrip",
    "dvdscr",
    "webdl",
    "720p",
    "1080p",
    "480p",
    "telegram",
    "torrent",
}
WEAK_DISTRIBUTION_HINTS = {
    "watch",
    "online",
    "stream",
    "streaming",
    "free",
}
MEDIUM_DISTRIBUTION_HINTS = {
    "link",
    "links",
    "mirror",
    "full",
    "dubbed",
    "dual",
    "audio",
    "leak",
    "leaked",
}
STRONG_COPY_HINTS = {
    "download",
    "camrip",
    "dvdscr",
    "hdrip",
    "webrip",
    "webdl",
    "web-dl",
    "720p",
    "1080p",
    "2160p",
    "4k",
    "telegram",
    "torrent",
    "magnet",
    "bluray",
    "rip",
}
DEFAULT_RISK_ECOSYSTEM_TERMS = (
    "movierulz",
    "netmirror",
    "ibomma",
    "tamilrockers",
    "filmyzilla",
    "9xmovies",
    "telegram",
    "torrent",
)
RISK_ECOSYSTEM_TERM_SET = set(DEFAULT_RISK_ECOSYSTEM_TERMS)
SUSPECT_HINTS = WEAK_DISTRIBUTION_HINTS | MEDIUM_DISTRIBUTION_HINTS | STRONG_COPY_HINTS
INFORMATIONAL_HINTS = {
    "news",
    "review",
    "reviews",
    "rating",
    "ratings",
    "wikipedia",
    "wiki",
    "encyclopedia",
    "plot",
    "cast",
    "crew",
    "trailer",
    "teaser",
    "box",
    "office",
    "collection",
    "interview",
    "explained",
    "analysis",
}
MEDIA_REFERENCE_EXTENSIONS = {
    ".mp4",
    ".m4v",
    ".mov",
    ".webm",
    ".mkv",
    ".avi",
    ".m3u8",
    ".mpd",
}
DEFAULT_AUTHORIZED_DOMAINS = {
    "netflix.com",
    "primevideo.com",
    "amazon.com",
    "hotstar.com",
    "disneyplus.com",
    "jiocinema.com",
    "sonyliv.com",
    "zee5.com",
    "aha.video",
    "sunnxt.com",
    "youtube.com",
}
DEFAULT_LOW_RISK_DOMAINS = {
    "justwatch.com",
    "imdb.com",
    "wikipedia.org",
    "wikimedia.org",
    "rottentomatoes.com",
    "metacritic.com",
    "letterboxd.com",
    "thehindu.com",
    "indiatimes.com",
    "timesofindia.indiatimes.com",
    "bookmyshow.com",
    "airtelxstream.in",
    "myvi.in",
}
EVIDENCE_LEVEL_LABELS = {
    0: "Search lead",
    1: "Page evidence",
    2: "Media reference",
    3: "Content fingerprint",
    4: "Multimodal match",
}
STOPWORDS = {
    "a",
    "an",
    "and",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int
    content_type: str
    text: str


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: List[str] = []
        self.description = ""
        self.anchors: List[Dict[str, str]] = []
        self.media_references: List[Dict[str, str]] = []
        self.text_parts: List[str] = []
        self._in_title = False
        self._skip_depth = 0
        self._current_href: Optional[str] = None
        self._current_anchor: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        attrs_dict = {name.lower(): value or "" for name, value in attrs}
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            name = (attrs_dict.get("name") or attrs_dict.get("property") or "").lower()
            if name in {"description", "og:description", "twitter:description"} and not self.description:
                self.description = attrs_dict.get("content", "").strip()
            if name in {"og:video", "og:video:url", "og:video:secure_url", "twitter:player"}:
                media_url = attrs_dict.get("content", "").strip()
                if media_url:
                    self.media_references.append({"url": media_url, "kind": name})
        if tag in {"video", "source", "iframe", "embed"}:
            media_url = (attrs_dict.get("src") or attrs_dict.get("data-src") or "").strip()
            if media_url:
                self.media_references.append({"url": media_url, "kind": tag})
        if tag == "a":
            self._current_href = attrs_dict.get("href", "").strip()
            self._current_anchor = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "title":
            self._in_title = False
        if tag == "a" and self._current_href:
            label = collapse_space(" ".join(self._current_anchor))
            self.anchors.append({"href": self._current_href, "text": label[:180]})
            self._current_href = None
            self._current_anchor = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        cleaned = collapse_space(data)
        if not cleaned:
            return
        if self._in_title:
            self.title_parts.append(cleaned)
        elif self._current_href is not None:
            self._current_anchor.append(cleaned)
        else:
            self.text_parts.append(cleaned)

    @property
    def title(self) -> str:
        return collapse_space(" ".join(self.title_parts))

    @property
    def body_text(self) -> str:
        return collapse_space(" ".join(self.text_parts))[:12_000]


def collapse_space(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def normalize_search_phrase(value: str) -> str:
    cleaned = re.sub(r"[_+.]+", " ", value or "")
    return collapse_space(cleaned)


def describe_connector_error(exc: Exception) -> str:
    if isinstance(exc, HTTPError):
        reason = collapse_space(str(exc.reason or ""))
        body = ""
        try:
            body = collapse_space(exc.read().decode("utf-8", errors="replace"))[:280]
        except Exception:  # noqa: BLE001 - body is optional diagnostic data.
            body = ""
        if "SUBSCRIPTION_TOKEN_INVALID" in body:
            return "HTTP 422: search provider subscription token is invalid; replace the backend API key and restart the backend"
        if exc.code == 401:
            return f"HTTP 401: search provider key is missing or invalid{f' / {body}' if body else ''}"
        if exc.code == 403:
            return f"HTTP 403: provider denied the request; check quota, billing, or permissions{f' / {body}' if body else ''}"
        if exc.code == 422:
            return f"HTTP 422: provider rejected the request; check query text and provider settings{f' / {body}' if body else ''}"
        if exc.code == 429:
            return f"HTTP 429: provider rate limit reached{f' / {body}' if body else ''}"
        return f"HTTP {exc.code}: {reason or 'search provider request failed'}{f' / {body}' if body else ''}"
    message = str(exc)
    if "timed out" in message.lower():
        return "network timeout; broad archive-index search is best-effort, use Brave/Bing/Google keys for reliable live discovery"
    if "WinError 10013" in message:
        return "outbound network blocked for this backend process; restart the backend with network permission"
    return message[:180]


def normalize_seed_url(raw_url: str) -> str:
    value = raw_url.strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if not parsed.scheme:
        value = f"https://{value}"
    return value


def normalize_domain(value: str) -> str:
    raw = value.strip().lower()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = parsed.hostname or raw
    if host.startswith("www."):
        host = host[4:]
    return host


def normalize_domains(domains: Optional[Iterable[str]]) -> set[str]:
    normalized = {normalize_domain(domain) for domain in domains or []}
    return DEFAULT_AUTHORIZED_DOMAINS | {domain for domain in normalized if domain}


def low_risk_domain_matches(host: str) -> bool:
    return domain_matches(host, DEFAULT_LOW_RISK_DOMAINS)


def domain_matches(host: str, domains: set[str]) -> bool:
    normalized_host = normalize_domain(host)
    return any(normalized_host == domain or normalized_host.endswith(f".{domain}") for domain in domains)


def tokenize(*values: str) -> set[str]:
    joined = " ".join(values).lower()
    tokens = set(re.findall(r"[a-z0-9]+", joined))
    return {token for token in tokens if len(token) > 1 and token not in STOPWORDS}


def is_media_reference_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    return any(path.endswith(extension) for extension in MEDIA_REFERENCE_EXTENSIONS)


def describe_media_reference(url: str, kind: str) -> Dict[str, str]:
    parsed = urlparse(url)
    path = parsed.path.lower()
    extension = next((item for item in MEDIA_REFERENCE_EXTENSIONS if path.endswith(item)), "embedded")
    return {
        "url": unique_url(url),
        "kind": kind,
        "host": normalize_domain(parsed.hostname or ""),
        "type": extension.replace(".", "").upper(),
    }


def collect_media_references(parser: PageParser, base_url: str) -> List[Dict[str, str]]:
    references: List[Dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for reference in parser.media_references:
        absolute_url = urljoin(base_url, reference["url"])
        described = describe_media_reference(absolute_url, reference["kind"])
        key = (described["kind"], described["host"], described["type"])
        if key not in seen:
            seen.add(key)
            references.append(described)

    for anchor in parser.anchors:
        href = anchor.get("href", "")
        absolute_url = urljoin(base_url, href)
        if not is_media_reference_url(absolute_url):
            continue
        described = describe_media_reference(absolute_url, "link")
        key = (described["kind"], described["host"], described["type"])
        if key not in seen:
            seen.add(key)
            references.append(described)

    return references[:12]


def classify_source(
    host: str,
    text: str,
    score: int,
    authorized_domains: set[str],
    media_references: Optional[List[Dict[str, str]]] = None,
    metadata_score: int = 0,
) -> str:
    if domain_matches(host, authorized_domains):
        return "AUTHORIZED"
    if low_risk_domain_matches(host):
        return "LEGITIMATE"

    tokens = tokenize(text)
    strong_or_medium = tokens & (STRONG_COPY_HINTS | MEDIUM_DISTRIBUTION_HINTS)
    if media_references and (strong_or_medium or score >= 35):
        return "SUSPECTED"
    if media_references and score >= 25:
        return "UNKNOWN"
    if score >= 60 and strong_or_medium:
        return "SUSPECTED"
    if metadata_score >= 45 or score >= 25:
        return "UNKNOWN"
    return "LOW_SIGNAL"


def is_public_http_url(url: str) -> tuple[bool, str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False, "Only public http/https URLs can be scanned."

    host = parsed.hostname or ""
    if host.lower() in {"localhost"} or host.endswith(".local"):
        return False, "Local/private network targets are blocked."

    try:
        addresses = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False, "DNS lookup failed."

    for address in {item[4][0] for item in addresses}:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            return False, "Local/private network targets are blocked."

    return True, ""


def fetch_url(url: str, timeout: float = 8.0) -> FetchResult:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(MAX_RESPONSE_BYTES)
        content_type = response.headers.get("content-type", "")
        charset = response.headers.get_content_charset() or "utf-8"
        text = raw.decode(charset, errors="replace")
        return FetchResult(
            url=url,
            final_url=response.geturl(),
            status=getattr(response, "status", 200),
            content_type=content_type,
            text=text,
        )


def score_candidate(query_tokens: set[str], title: str, url: str, context: str) -> Dict[str, object]:
    url_tokens = tokenize(url.replace("-", " ").replace("_", " "))
    title_tokens = tokenize(title)
    context_tokens = tokenize(context)
    all_tokens = title_tokens | url_tokens | context_tokens
    media_tokens = all_tokens & MEDIA_HINTS
    weak_tokens = all_tokens & WEAK_DISTRIBUTION_HINTS
    medium_tokens = all_tokens & MEDIUM_DISTRIBUTION_HINTS
    strong_tokens = all_tokens & STRONG_COPY_HINTS
    distribution_tokens = weak_tokens | medium_tokens | strong_tokens
    informational_tokens = all_tokens & INFORMATIONAL_HINTS
    risk_surface_tokens = all_tokens & RISK_ECOSYSTEM_TERM_SET

    title_hits = len(query_tokens & title_tokens)
    url_hits = len(query_tokens & url_tokens)
    context_hits = len(query_tokens & context_tokens)
    total_query = max(len(query_tokens), 1)
    score_normalizer = max(1, min(total_query, max(title_hits, url_hits, context_hits, 1)))

    title_score = min(45, round((title_hits / score_normalizer) * 45))
    url_score = min(25, round((url_hits / score_normalizer) * 25))
    context_score = min(20, round((context_hits / score_normalizer) * 20))
    metadata_score = min(100, title_score + url_score + context_score)
    title_relevance_score = min(
        25,
        round((title_hits / score_normalizer) * 12)
        + round((url_hits / score_normalizer) * 8)
        + round((context_hits / score_normalizer) * 5),
    )
    weak_score = min(3, len(weak_tokens))
    medium_score = min(6, len(medium_tokens) * 3)
    strong_score = min(12, len(strong_tokens) * 4)
    distribution_score = min(15, weak_score + medium_score + strong_score)
    direct_media_url_score = 10 if is_media_reference_url(url) else 0
    risk_surface_score = min(12, len(risk_surface_tokens) * 6)
    domain_context_score = min(
        15,
        direct_media_url_score
        + len(strong_tokens & url_tokens) * 3
        + len(medium_tokens & url_tokens) * 2
        + len(risk_surface_tokens & url_tokens) * 5,
    )
    independent_signal_count = 0
    if title_hits:
        independent_signal_count += 1
    if url_hits:
        independent_signal_count += 1
    if context_hits:
        independent_signal_count += 1
    if weak_tokens:
        independent_signal_count += 1
    if medium_tokens:
        independent_signal_count += 1
    if strong_tokens:
        independent_signal_count += 2
    if risk_surface_tokens:
        independent_signal_count += 2
    if direct_media_url_score:
        independent_signal_count += 2
    independent_score = min(20, independent_signal_count * 3)
    media_context_score = min(10, len(media_tokens) * 2)
    information_penalty = min(30, len(informational_tokens) * 8)
    risk_score = max(
        0,
        min(
            75,
            round(title_relevance_score * 0.2)
            + distribution_score
            + media_context_score
            + domain_context_score
            + risk_surface_score
            + independent_score
            - information_penalty,
        ),
    )

    reasons: List[str] = []
    if title_hits:
        reasons.append(f"{title_hits} protected-title token(s) found in page title or link text")
    if url_hits:
        reasons.append(f"{url_hits} protected-title token(s) found in URL")
    if context_hits:
        reasons.append(f"{context_hits} protected-title token(s) found in surrounding page text")
    if weak_tokens:
        reasons.append(f"Weak distribution-language signal: {', '.join(sorted(weak_tokens)[:4])}")
    if medium_tokens:
        reasons.append(f"Medium distribution-language signal: {', '.join(sorted(medium_tokens)[:4])}")
    if strong_tokens:
        reasons.append(f"Strong copy-like signal: {', '.join(sorted(strong_tokens)[:4])}")
    if risk_surface_tokens:
        reasons.append(f"Risk-surface term found in public metadata: {', '.join(sorted(risk_surface_tokens)[:4])}")
    if media_tokens:
        reasons.append(f"Media-page hint detected: {', '.join(sorted(media_tokens)[:3])}")
    if informational_tokens:
        reasons.append(f"Informational-page signal reduced risk: {', '.join(sorted(informational_tokens)[:3])}")
    if not reasons:
        reasons.append("No strong title, URL, or context overlap with the protected work")

    return {
        "score": risk_score,
        "riskScore": risk_score,
        "metadataScore": metadata_score,
        "relevanceScore": metadata_score,
        "titleRelevanceScore": title_relevance_score,
        "distributionScore": distribution_score,
        "domainContextScore": domain_context_score,
        "riskSurfaceScore": risk_surface_score,
        "independentSignalScore": independent_score,
        "mediaContextScore": media_context_score,
        "informationPenalty": information_penalty,
        "weakDistributionSignals": sorted(weak_tokens),
        "mediumDistributionSignals": sorted(medium_tokens),
        "strongCopySignals": sorted(strong_tokens),
        "riskSurfaceSignals": sorted(risk_surface_tokens),
        "signals": {
            "Metadata relevance": metadata_score,
            "Title relevance": title_relevance_score,
            "Distribution signals": distribution_score,
            "Media evidence": 0,
            "Domain/context": domain_context_score,
            "Risk surface": risk_surface_score,
            "Independent signals": independent_score,
            "Informational penalty": information_penalty,
        },
        "reasons": reasons,
    }


def candidate_decision(score: int, media_evidence_score: int = 0, evidence_level: int = 0) -> str:
    if evidence_level >= 4:
        return "Match"
    if score >= 65 and media_evidence_score > 0:
        return "High-risk lead"
    if score >= 35:
        return "Investigate"
    return "Relevant metadata"


def candidate_risk_label(
    score: int,
    source_class: str,
    authorized: bool,
    media_evidence_score: int = 0,
    evidence_level: int = 0,
) -> str:
    if authorized:
        return "Authorized"
    if source_class == "LEGITIMATE":
        return "Low-risk relevant"
    if evidence_level >= 4 and score >= 86:
        return "Verified match"
    if media_evidence_score > 0 and (source_class == "SUSPECTED" or score >= 65):
        return "High-risk lead"
    if score >= 35 or (source_class == "UNKNOWN" and score >= 15):
        return "Investigate"
    return "Low-risk relevant"


def add_candidate(
    candidates: List[Dict[str, object]],
    excluded_candidates: List[Dict[str, object]],
    candidate: Dict[str, object],
) -> None:
    if candidate.get("authorized"):
        excluded_candidates.append(candidate)
        return
    candidates.append(candidate)


def build_search_queries(
    title: str,
    aliases: Optional[Iterable[str]] = None,
    source_domains: Optional[Iterable[str]] = None,
    risk_terms: Optional[Iterable[str]] = None,
) -> List[str]:
    protected_title = normalize_search_phrase(title)
    alias_list = [normalize_search_phrase(alias) for alias in aliases or [] if normalize_search_phrase(alias)]
    names = [name for name in [protected_title, *alias_list] if name]
    domains = [normalize_domain(domain) for domain in source_domains or [] if normalize_domain(domain)]
    surface_terms = [
        normalize_search_phrase(term)
        for term in (risk_terms if risk_terms is not None else DEFAULT_RISK_ECOSYSTEM_TERMS)
        if normalize_search_phrase(term)
    ]
    queries: List[str] = []
    content_intents = [""]
    distribution_intents = [
        "full movie",
        "watch online",
        "free streaming",
        "download",
        "1080p",
        "720p",
        "4K",
        "dubbed",
        "stream",
    ]
    copy_like_intents = [
        "WEB-DL",
        "HDRip",
        "BluRay",
        "480p",
        "dual audio",
        "torrent",
    ]

    if domains:
        for domain in domains[:6]:
            for name in names[:3]:
                queries.append(f'site:{domain} "{name}"')
                queries.append(f'site:{domain} "{name}" "watch online"')
                queries.append(f'site:{domain} "{name}" "download"')
    else:
        for name in names[:3]:
            for intent in content_intents:
                queries.append(f'"{name}" {intent}'.strip())
            for term in surface_terms[:8]:
                queries.append(f'"{name}" "{term}"')
            for term in surface_terms[:4]:
                queries.append(f'"{name}" "{term}" "download"')
            for intent in distribution_intents:
                queries.append(f'"{name}" "{intent}"')
            for intent in copy_like_intents:
                queries.append(f'"{name}" "{intent}"')

    deduped: List[str] = []
    seen: set[str] = set()
    for query in queries:
        cleaned = collapse_space(query)[:380]
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            deduped.append(cleaned)
    return deduped[:28]


def brave_search(
    query: str,
    api_key: str,
    count: int = 10,
    country: str = "IN",
    search_lang: str = "en",
    timeout: float = 8.0,
) -> Dict[str, object]:
    params = {
        "q": query,
        "count": str(max(1, min(int(count or 10), SEARCH_RESULT_LIMIT))),
        "country": (country or "IN").upper()[:2],
        "search_lang": (search_lang or "en")[:8],
        "text_decorations": "false",
    }
    request = Request(
        f"{BRAVE_SEARCH_ENDPOINT}?{urlencode(params)}",
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "X-Subscription-Token": api_key,
        },
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(MAX_RESPONSE_BYTES)
        return json.loads(raw.decode("utf-8", errors="replace"))


def bing_search(
    query: str,
    api_key: str,
    count: int = 10,
    country: str = "IN",
    search_lang: str = "en",
    timeout: float = 8.0,
) -> Dict[str, object]:
    market = f"{(search_lang or 'en')[:2]}-{(country or 'IN').upper()[:2]}"
    params = {
        "q": query,
        "count": str(max(1, min(int(count or 10), SEARCH_RESULT_LIMIT))),
        "mkt": market,
        "responseFilter": "Webpages",
        "safeSearch": "Moderate",
        "textDecorations": "false",
    }
    request = Request(
        f"{BING_SEARCH_ENDPOINT}?{urlencode(params)}",
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "Ocp-Apim-Subscription-Key": api_key,
        },
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(MAX_RESPONSE_BYTES)
        return json.loads(raw.decode("utf-8", errors="replace"))


def google_cse_search(
    query: str,
    api_key: str,
    search_engine_id: str,
    count: int = 10,
    country: str = "IN",
    search_lang: str = "en",
    timeout: float = 8.0,
) -> Dict[str, object]:
    params = {
        "key": api_key,
        "cx": search_engine_id,
        "q": query,
        "num": str(max(1, min(int(count or 10), 10))),
        "gl": (country or "IN").lower()[:2],
        "lr": f"lang_{(search_lang or 'en')[:2]}",
        "safe": "off",
    }
    request = Request(
        f"{GOOGLE_CSE_ENDPOINT}?{urlencode(params)}",
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(MAX_RESPONSE_BYTES)
        return json.loads(raw.decode("utf-8", errors="replace"))


def common_crawl_collections(limit: int = 1, timeout: float = 8.0) -> List[Dict[str, str]]:
    global _COMMON_CRAWL_COLLECTION_CACHE
    cache_limit = max(1, min(int(limit or 1), 3))
    if _COMMON_CRAWL_COLLECTION_CACHE:
        return _COMMON_CRAWL_COLLECTION_CACHE[:cache_limit]

    request = Request(
        COMMON_CRAWL_COLLINFO_ENDPOINT,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(MAX_RESPONSE_BYTES)
        payload = json.loads(raw.decode("utf-8", errors="replace"))

    collections: List[Dict[str, str]] = []
    if not isinstance(payload, list):
        return collections

    for item in payload:
        if not isinstance(item, dict):
            continue
        collection_id = collapse_space(str(item.get("id") or ""))
        if not collection_id:
            continue
        cdx_api = collapse_space(str(item.get("cdx-api") or f"https://index.commoncrawl.org/{collection_id}-index"))
        collections.append({"id": collection_id, "api": cdx_api.rstrip("/")})

    _COMMON_CRAWL_COLLECTION_CACHE = sorted(collections, key=lambda item: item["id"], reverse=True)
    return _COMMON_CRAWL_COLLECTION_CACHE[:cache_limit]


def common_crawl_pattern_from_query(query: str) -> str:
    words = re.findall(r"[a-z0-9]+", normalize_search_phrase(query).lower())
    if not words:
        return ""
    return f"*{'*'.join(words[:5])}*"


def common_crawl_search(
    query: str,
    count: int = 10,
    country: str = "IN",
    search_lang: str = "en",
    timeout: float = 4.0,
) -> Dict[str, object]:
    del country, search_lang
    pattern = common_crawl_pattern_from_query(query)
    if not pattern:
        return {"records": [], "collections": []}

    records: List[Dict[str, str]] = []
    collections = common_crawl_collections(limit=1, timeout=timeout)
    record_limit = max(1, min(int(count or 10), SEARCH_RESULT_LIMIT))

    for collection in collections:
        params = {
            "url": pattern,
            "output": "json",
            "fl": "url,timestamp,mime,status",
            "filter": ["status:200", "mime:text/html"],
            "collapse": "urlkey",
            "limit": str(record_limit),
        }
        request = Request(
            f"{collection['api']}?{urlencode(params, doseq=True)}",
            headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES)
        except HTTPError as exc:
            if exc.code == 404:
                continue
            raise

        for line in raw.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(item, dict):
                continue
            url = collapse_space(str(item.get("url") or ""))
            if not url:
                continue
            records.append(
                {
                    "url": url,
                    "timestamp": collapse_space(str(item.get("timestamp") or "")),
                    "mime": collapse_space(str(item.get("mime") or "")),
                    "status": collapse_space(str(item.get("status") or "")),
                    "collection": collection["id"],
                }
            )
            if len(records) >= record_limit:
                break
        if len(records) >= record_limit:
            break

    return {"records": records, "collections": collections, "pattern": pattern}


def extract_search_results(payload: Dict[str, object], query: str) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []

    web_payload = payload.get("web")
    if isinstance(web_payload, dict):
        web_results = web_payload.get("results")
        if isinstance(web_results, list):
            for item in web_results:
                if not isinstance(item, dict):
                    continue
                url = collapse_space(str(item.get("url") or ""))
                if not url:
                    continue
                title = collapse_space(str(item.get("title") or url))
                description = collapse_space(str(item.get("description") or ""))
                results.append(
                    {
                        "title": title,
                        "url": url,
                        "description": description,
                        "query": query,
                        "sourceType": "Search result",
                    }
                )

    video_payload = payload.get("videos")
    if isinstance(video_payload, dict):
        video_results = video_payload.get("results")
        if isinstance(video_results, list):
            for item in video_results:
                if not isinstance(item, dict):
                    continue
                url = collapse_space(str(item.get("url") or ""))
                if not url:
                    continue
                title = collapse_space(str(item.get("title") or url))
                description = collapse_space(str(item.get("description") or ""))
                results.append(
                    {
                        "title": title,
                        "url": url,
                        "description": description,
                        "query": query,
                        "sourceType": "Search video result",
                    }
                )

    return results


def extract_bing_results(payload: Dict[str, object], query: str) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    web_pages = payload.get("webPages")
    values = web_pages.get("value") if isinstance(web_pages, dict) else []
    if not isinstance(values, list):
        return results

    for item in values:
        if not isinstance(item, dict):
            continue
        url = collapse_space(str(item.get("url") or ""))
        if not url:
            continue
        results.append(
            {
                "title": collapse_space(str(item.get("name") or url)),
                "url": url,
                "description": collapse_space(str(item.get("snippet") or "")),
                "query": query,
                "sourceType": "Bing search result",
            }
        )
    return results


def extract_google_results(payload: Dict[str, object], query: str) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    items = payload.get("items")
    if not isinstance(items, list):
        return results

    for item in items:
        if not isinstance(item, dict):
            continue
        url = collapse_space(str(item.get("link") or ""))
        if not url:
            continue
        results.append(
            {
                "title": collapse_space(str(item.get("title") or url)),
                "url": url,
                "description": collapse_space(str(item.get("snippet") or "")),
                "query": query,
                "sourceType": "Google CSE result",
            }
        )
    return results


def extract_common_crawl_results(payload: Dict[str, object], query: str) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    records = payload.get("records")
    if not isinstance(records, list):
        return results

    for item in records:
        if not isinstance(item, dict):
            continue
        url = collapse_space(str(item.get("url") or ""))
        if not url:
            continue
        host = urlparse(url).hostname or url
        collection = collapse_space(str(item.get("collection") or "Common Crawl"))
        timestamp = collapse_space(str(item.get("timestamp") or ""))
        description = f"Public archive URL-index hit from {collection}"
        if timestamp:
            description = f"{description}; capture timestamp {timestamp}"
        results.append(
            {
                "title": f"Archived URL: {host}",
                "url": url,
                "description": description,
                "query": query,
                "sourceType": "Common Crawl URL index",
            }
        )
    return results


def unique_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return collapse_space(url)

    query_items = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered_key = key.lower()
        if lowered_key.startswith("utm_") or lowered_key in TRACKING_QUERY_PARAMS:
            continue
        query_items.append((key, value))

    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")

    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            urlencode(query_items, doseq=True),
            "",
        )
    )


def normalize_provider_names(providers: Optional[Iterable[str]]) -> List[str]:
    allowed = ["brave", "bing", "google", "commoncrawl"]
    names = [collapse_space(str(provider)).lower() for provider in providers or []]
    selected = [provider for provider in names if provider in allowed]
    if not selected:
        selected = allowed

    deduped: List[str] = []
    for provider in selected:
        if provider not in deduped:
            deduped.append(provider)
    return deduped


def merge_unique_candidates(*candidate_groups: Iterable[Dict[str, object]], limit: int = 24) -> List[Dict[str, object]]:
    merged: Dict[str, Dict[str, object]] = {}
    for group in candidate_groups:
        for candidate in group:
            key = unique_url(str(candidate.get("url") or ""))
            if not key:
                continue
            existing = merged.get(key)
            if not existing or int(candidate.get("score", 0)) > int(existing.get("score", 0)):
                merged[key] = candidate
    return sorted(merged.values(), key=lambda item: int(item.get("score", 0)), reverse=True)[:limit]


def merge_unique_sources(*source_groups: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    merged: Dict[str, Dict[str, object]] = {}
    for group in source_groups:
        for source in group:
            key = unique_url(str(source.get("url") or ""))
            if not key:
                continue
            existing = merged.get(key)
            if not existing or (not existing.get("ok") and source.get("ok")):
                merged[key] = source
    return list(merged.values())


def merge_unique_links(*link_groups: Iterable[Dict[str, object]], limit: int = MAX_EXPANSION_PAGES) -> List[Dict[str, object]]:
    merged: Dict[str, Dict[str, object]] = {}
    for group in link_groups:
        for link in group:
            key = unique_url(str(link.get("url") or ""))
            if not key:
                continue
            existing = merged.get(key)
            if not existing or int(link.get("score", 0)) > int(existing.get("score", 0)):
                merged[key] = link
    return sorted(merged.values(), key=lambda item: int(item.get("score", 0)), reverse=True)[:limit]


def build_coverage_report(
    provider_names: Iterable[str],
    provider_results: Iterable[Dict[str, object]],
    search_result_count: int,
    sources: Iterable[Dict[str, object]],
    candidates: Iterable[Dict[str, object]],
    excluded_candidates: Iterable[Dict[str, object]],
    expansion_urls: Iterable[Dict[str, object]],
    authorized_domains: set[str],
    authorized_excluded: int,
    media_reference_count: int,
    verified_media_count: int,
    expansion_depth: int,
    queries_issued: int = 0,
    unique_url_count: int = 0,
    search_latency_ms: int = 0,
    page_fetch_latency_ms: int = 0,
    total_discovery_ms: int = 0,
) -> Dict[str, object]:
    source_list = list(sources)
    candidate_list = list(candidates)
    excluded_list = list(excluded_candidates)
    expansion_list = list(expansion_urls)
    domain_set: set[str] = set()

    for item in [*source_list, *candidate_list, *excluded_list, *expansion_list]:
        host = normalize_domain(str(item.get("host") or urlparse(str(item.get("url") or "")).hostname or ""))
        if host:
            domain_set.add(host)

    ready_providers = [
        str(item.get("provider"))
        for item in provider_results
        if item.get("status") in {"ready", "partial"}
    ]
    blocked_sources = sum(1 for source in source_list if not source.get("ok") and not source.get("skipped"))
    high_risk = sum(
        1
        for candidate in candidate_list
        if candidate.get("riskLevel") == "High-risk lead" or int(candidate.get("score", 0)) >= 70
    )
    unknown_domains = sum(1 for domain in domain_set if not domain_matches(domain, authorized_domains))
    media_candidates = sum(1 for candidate in candidate_list if int(candidate.get("mediaReferenceCount", 0)) > 0)

    return {
        "providersRequested": list(provider_names),
        "providersReady": ready_providers,
        "queriesIssued": int(queries_issued),
        "searchResults": int(search_result_count),
        "uniqueUrls": int(unique_url_count or search_result_count),
        "pagesEvaluated": len(source_list),
        "domainsEvaluated": len(domain_set),
        "unknownDomains": unknown_domains,
        "thirdPartyLeads": len(candidate_list),
        "highRiskLeads": high_risk,
        "authorizedExclusions": int(authorized_excluded),
        "blockedUnreachable": blocked_sources,
        "mediaCandidates": media_candidates,
        "mediaReferences": int(media_reference_count),
        "verifiedMatches": int(verified_media_count),
        "expansionDepth": int(expansion_depth),
        "expansionQueued": len(expansion_list),
        "searchLatencyMs": int(search_latency_ms),
        "pageFetchLatencyMs": int(page_fetch_latency_ms),
        "totalDiscoveryMs": int(total_discovery_ms),
    }


def discovery_boundary() -> List[str]:
    return [
        "Public HTML and metadata only",
        "No pirated video download or stream capture",
        "No login bypass, paywall bypass, or hidden-site access",
        "Discovery leads must be verified by Content DNA before action",
        "Coverage is measured and reported; private, blocked, or unindexed sources are not claimed as scanned",
    ]


def evidence_ladder() -> List[Dict[str, object]]:
    return [
        {"level": level, "label": label}
        for level, label in EVIDENCE_LEVEL_LABELS.items()
    ]


def parse_page(fetch: FetchResult) -> PageParser:
    parser = PageParser()
    parser.feed(fetch.text)
    return parser


def scan_public_sources(
    title: str,
    aliases: Optional[Iterable[str]],
    seed_urls: Iterable[str],
    authorized_domains: Optional[Iterable[str]] = None,
    max_pages: int = 6,
    fetcher: Callable[[str], FetchResult] = fetch_url,
    validate_urls: bool = True,
) -> Dict[str, object]:
    discovery_started = time.perf_counter()
    protected_title = collapse_space(title)
    if not protected_title:
        raise ValueError("Protected title is required.")

    alias_list = [collapse_space(alias) for alias in aliases or [] if collapse_space(alias)]
    query_tokens = tokenize(protected_title, *alias_list)
    seeds = [normalize_seed_url(url) for url in seed_urls if normalize_seed_url(url)]
    seeds = seeds[: max(1, min(int(max_pages or 6), 10))]
    authorized_set = normalize_domains(authorized_domains)

    sources: List[Dict[str, object]] = []
    candidates: List[Dict[str, object]] = []
    excluded_candidates: List[Dict[str, object]] = []
    expansion_urls: List[Dict[str, object]] = []
    seen_urls: set[str] = set()
    seen_expansion_urls: set[str] = set()

    for seed in seeds:
        parsed_seed = urlparse(seed)
        host = parsed_seed.hostname or ""
        initial_class = "AUTHORIZED" if domain_matches(host, authorized_set) else "PENDING"
        source_record: Dict[str, object] = {
            "url": seed,
            "host": host,
            "ok": False,
            "status": None,
            "title": "",
            "error": "",
            "linksFound": 0,
            "mediaReferences": 0,
            "sourceClass": initial_class,
            "authorized": initial_class == "AUTHORIZED",
            "skipped": False,
            "discoveredLinks": [],
            "fetchMs": 0,
        }

        if initial_class == "AUTHORIZED":
            source_record["ok"] = True
            source_record["skipped"] = True
            source_record["error"] = "Authorized source excluded before verification queue."
            sources.append(source_record)
            continue

        if validate_urls:
            ok, reason = is_public_http_url(seed)
            if not ok:
                source_record["error"] = reason
                sources.append(source_record)
                continue

        try:
            fetch_started = time.perf_counter()
            fetched = fetcher(seed)
            fetch_ms = int((time.perf_counter() - fetch_started) * 1000)
            parser = parse_page(fetched)
            source_title = parser.title or parsed_seed.netloc
            source_context = " ".join([parser.description, parser.body_text[:1600]])
            media_references = collect_media_references(parser, fetched.final_url)
            source_expansion_urls: List[Dict[str, object]] = []
            source_record.update(
                {
                    "ok": True,
                    "status": fetched.status,
                    "url": fetched.final_url,
                    "host": urlparse(fetched.final_url).hostname or parsed_seed.hostname or "",
                    "title": source_title,
                    "linksFound": len(parser.anchors),
                    "mediaReferences": len(media_references),
                    "fetchMs": fetch_ms,
                }
            )

            page_score = score_candidate(query_tokens, source_title, fetched.final_url, source_context)
            source_record["metadataScore"] = int(page_score.get("metadataScore", 0))
            source_record["riskScore"] = int(page_score.get("score", 0))
            source_record["sourceClass"] = classify_source(
                str(source_record["host"]),
                f"{source_title} {fetched.final_url} {source_context}",
                int(page_score["score"]),
                authorized_set,
                media_references,
                int(page_score.get("metadataScore", 0)),
            )
            source_record["authorized"] = source_record["sourceClass"] == "AUTHORIZED"
            if int(page_score.get("metadataScore", 0)) >= 45 or int(page_score["score"]) >= 25:
                add_candidate(
                    candidates,
                    excluded_candidates,
                    build_candidate(
                        len(candidates) + len(excluded_candidates),
                        source_title,
                        fetched.final_url,
                        str(source_record["host"]),
                        "Seed page",
                        page_score,
                        source_context,
                        fetched.final_url,
                        media_references,
                        authorized_set,
                    ),
                )

            for anchor in parser.anchors:
                href = anchor.get("href", "")
                absolute_url = urljoin(fetched.final_url, href)
                parsed_link = urlparse(absolute_url)
                if parsed_link.scheme not in {"http", "https"} or not parsed_link.netloc:
                    continue
                direct_media = is_media_reference_url(absolute_url)
                normalized_without_fragment = parsed_link._replace(fragment="").geturl()
                candidate_url = fetched.final_url if direct_media else normalized_without_fragment
                if candidate_url in seen_urls:
                    continue

                link_text = anchor.get("text", "")
                link_score = score_candidate(query_tokens, link_text, normalized_without_fragment, source_context)
                link_host = parsed_link.hostname or ""
                if (
                    not direct_media
                    and (int(link_score["score"]) >= 20 or int(link_score.get("metadataScore", 0)) >= 45)
                    and not domain_matches(link_host, authorized_set)
                    and normalized_without_fragment not in seen_expansion_urls
                ):
                    seen_expansion_urls.add(normalized_without_fragment)
                    expansion_record = {
                        "title": collapse_space(link_text) or parsed_link.path.rsplit("/", 1)[-1] or link_host,
                        "url": normalized_without_fragment,
                        "host": link_host,
                        "score": int(link_score["score"]),
                        "sourcePage": fetched.final_url,
                        "sourceTitle": source_title,
                        "sourceType": "Public link expansion",
                    }
                    expansion_urls.append(expansion_record)
                    source_expansion_urls.append(expansion_record)
                if (
                    not direct_media
                    and int(link_score["score"]) < 30
                    and int(link_score.get("metadataScore", 0)) < 45
                ):
                    continue

                seen_urls.add(candidate_url)
                link_media_references = [describe_media_reference(absolute_url, "link")] if direct_media else []
                add_candidate(
                    candidates,
                    excluded_candidates,
                    build_candidate(
                        len(candidates) + len(excluded_candidates),
                        link_text or parsed_link.path.rsplit("/", 1)[-1] or parsed_link.netloc,
                        candidate_url,
                        link_host,
                        "Media reference" if direct_media else "Linked candidate",
                        link_score,
                        source_context,
                        fetched.final_url,
                        link_media_references,
                        authorized_set,
                    ),
                )
            source_record["discoveredLinks"] = sorted(
                source_expansion_urls,
                key=lambda item: int(item.get("score", 0)),
                reverse=True,
            )[:8]
        except Exception as exc:  # noqa: BLE001 - connector reports source failures in the UI.
            source_record["error"] = str(exc)[:220]
            source_record["sourceClass"] = "BLOCKED"
        finally:
            sources.append(source_record)

    candidates = sorted(candidates, key=lambda item: int(item["score"]), reverse=True)[:24]
    excluded_candidates = sorted(excluded_candidates, key=lambda item: int(item["score"]), reverse=True)[:12]
    expansion_urls = merge_unique_links(expansion_urls, limit=MAX_EXPANSION_PAGES)
    media_reference_count = sum(int(source.get("mediaReferences", 0)) for source in sources)
    authorized_excluded_count = len(excluded_candidates) + sum(1 for source in sources if source.get("authorized"))
    coverage = build_coverage_report(
        provider_names=["seed"],
        provider_results=[{"provider": "seed", "status": "seed_only", "resultCount": 0}],
        search_result_count=0,
        sources=sources,
        candidates=candidates,
        excluded_candidates=excluded_candidates,
        expansion_urls=expansion_urls,
        authorized_domains=authorized_set,
        authorized_excluded=authorized_excluded_count,
        media_reference_count=media_reference_count + sum(int(item.get("mediaReferenceCount", 0)) for item in candidates),
        verified_media_count=0,
        expansion_depth=0,
        page_fetch_latency_ms=sum(int(source.get("fetchMs", 0)) for source in sources),
    )
    return {
        "query": protected_title,
        "aliases": alias_list,
        "seedCount": len(seeds),
        "sourcesScanned": sources,
        "candidateCount": len(candidates),
        "candidates": candidates,
        "excludedCandidates": excluded_candidates,
        "authorizedExcluded": authorized_excluded_count,
        "mediaReferenceCount": media_reference_count + sum(int(item.get("mediaReferenceCount", 0)) for item in candidates),
        "verifiedMediaCount": 0,
        "provider": "seed",
        "providerStatus": "seed_only",
        "providerResults": [{"provider": "seed", "status": "seed_only", "resultCount": 0}],
        "searchQueries": [],
        "searchResultCount": 0,
        "searchErrors": [],
        "expansionUrls": expansion_urls,
        "coverage": coverage,
        "setupRequired": False,
        "setupMessage": "",
        "evidenceLadder": evidence_ladder(),
        "boundary": discovery_boundary(),
    }


def search_public_web(
    title: str,
    aliases: Optional[Iterable[str]] = None,
    authorized_domains: Optional[Iterable[str]] = None,
    source_domains: Optional[Iterable[str]] = None,
    risk_terms: Optional[Iterable[str]] = None,
    providers: Optional[Iterable[str]] = None,
    max_results: int = 12,
    deep_scan_pages: int = 6,
    expand_depth: int = 1,
    expand_pages: int = 16,
    per_domain_page_limit: int = 4,
    country: str = "IN",
    search_lang: str = "en",
    api_key: Optional[str] = None,
    searcher: Optional[Callable[[str, int, str, str], Dict[str, object]]] = None,
    fetcher: Callable[[str], FetchResult] = fetch_url,
    validate_urls: bool = True,
) -> Dict[str, object]:
    discovery_started = time.perf_counter()
    protected_title = collapse_space(title)
    if not protected_title:
        raise ValueError("Protected title is required.")

    alias_list = [collapse_space(alias) for alias in aliases or [] if collapse_space(alias)]
    authorized_set = normalize_domains(authorized_domains)
    source_focus = [normalize_domain(domain) for domain in source_domains or [] if normalize_domain(domain)]
    query_tokens = tokenize(protected_title, *alias_list)
    queries = build_search_queries(protected_title, alias_list, source_focus, risk_terms)
    requested_providers = ["test"] if searcher else normalize_provider_names(providers)

    provider_entries: List[Dict[str, str]] = []
    provider_results: List[Dict[str, object]] = []

    if searcher:
        provider_entries.append({"provider": "test", "key": "test"})
    else:
        brave_key = api_key if api_key is not None else os.environ.get("BRAVE_SEARCH_API_KEY") or os.environ.get("BRAVE_API_KEY") or ""
        bing_key = os.environ.get("BING_SEARCH_API_KEY") or os.environ.get("BING_API_KEY") or ""
        google_key = os.environ.get("GOOGLE_CSE_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
        google_cx = os.environ.get("GOOGLE_CSE_ID") or os.environ.get("GOOGLE_SEARCH_ENGINE_ID") or ""

        for provider in requested_providers:
            if provider == "brave" and brave_key:
                provider_entries.append({"provider": "brave", "key": brave_key})
            elif provider == "bing" and bing_key:
                provider_entries.append({"provider": "bing", "key": bing_key})
            elif provider == "google" and google_key and google_cx:
                provider_entries.append({"provider": "google", "key": google_key, "cx": google_cx})
            elif provider == "commoncrawl":
                provider_entries.append({"provider": "commoncrawl", "key": "public"})
            else:
                provider_results.append(
                    {
                        "provider": provider,
                        "status": "missing_key",
                        "resultCount": 0,
                        "queries": len(queries),
                    }
                )

    if not provider_entries:
        coverage = build_coverage_report(
            provider_names=requested_providers,
            provider_results=provider_results,
            search_result_count=0,
            sources=[],
            candidates=[],
            excluded_candidates=[],
            expansion_urls=[],
            authorized_domains=authorized_set,
            authorized_excluded=0,
            media_reference_count=0,
            verified_media_count=0,
            expansion_depth=0,
            queries_issued=0,
            unique_url_count=0,
            total_discovery_ms=int((time.perf_counter() - discovery_started) * 1000),
        )
        return {
            "query": protected_title,
            "aliases": alias_list,
            "provider": "multi-index",
            "providerStatus": "missing_key",
            "setupRequired": True,
            "setupMessage": "Set BRAVE_SEARCH_API_KEY, BING_SEARCH_API_KEY, or GOOGLE_CSE_API_KEY + GOOGLE_CSE_ID on the backend to enable multi-index public discovery. Seed URL scanning still works without a key.",
            "searchQueries": queries,
            "searchResultCount": 0,
            "searchErrors": [],
            "sourceFocusDomains": source_focus,
            "providerResults": provider_results,
            "seedCount": 0,
            "sourcesScanned": [],
            "candidateCount": 0,
            "candidates": [],
            "excludedCandidates": [],
            "authorizedExcluded": 0,
            "mediaReferenceCount": 0,
            "verifiedMediaCount": 0,
            "expansionUrls": [],
            "coverage": coverage,
            "evidenceLadder": evidence_ladder(),
            "boundary": discovery_boundary(),
        }

    search_results: List[Dict[str, str]] = []
    search_errors: List[str] = []
    per_query_count = max(1, min(int(max_results or 12), SEARCH_RESULT_LIMIT))
    provider_counts = {entry["provider"]: 0 for entry in provider_entries}
    provider_error_counts = {entry["provider"]: 0 for entry in provider_entries}
    provider_latency_ms = {entry["provider"]: 0 for entry in provider_entries}
    provider_query_counts: Dict[str, int] = {}

    for entry in provider_entries:
        provider = entry["provider"]
        provider_queries = queries[:COMMON_CRAWL_QUERY_LIMIT] if provider == "commoncrawl" else queries
        provider_query_counts[provider] = len(provider_queries)
        for query in provider_queries:
            search_started = time.perf_counter()
            try:
                if provider == "test":
                    payload = searcher(query, per_query_count, country, search_lang)  # type: ignore[misc]
                    extracted = extract_search_results(payload, query)
                elif provider == "brave":
                    payload = brave_search(
                        query=query,
                        api_key=entry["key"],
                        count=per_query_count,
                        country=country,
                        search_lang=search_lang,
                    )
                    extracted = extract_search_results(payload, query)
                    for item in extracted:
                        item["sourceType"] = item.get("sourceType", "Brave search result").replace("Search", "Brave search")
                elif provider == "bing":
                    payload = bing_search(
                        query=query,
                        api_key=entry["key"],
                        count=per_query_count,
                        country=country,
                        search_lang=search_lang,
                    )
                    extracted = extract_bing_results(payload, query)
                elif provider == "google":
                    payload = google_cse_search(
                        query=query,
                        api_key=entry["key"],
                        search_engine_id=entry.get("cx", ""),
                        count=per_query_count,
                        country=country,
                        search_lang=search_lang,
                    )
                    extracted = extract_google_results(payload, query)
                else:
                    payload = common_crawl_search(
                        query=query,
                        count=per_query_count,
                        country=country,
                        search_lang=search_lang,
                    )
                    extracted = extract_common_crawl_results(payload, query)

                provider_latency_ms[provider] += int((time.perf_counter() - search_started) * 1000)
                for result in extracted:
                    result["provider"] = provider
                provider_counts[provider] += len(extracted)
                search_results.extend(extracted)
            except Exception as exc:  # noqa: BLE001 - search failures are surfaced in the UI.
                provider_latency_ms[provider] += int((time.perf_counter() - search_started) * 1000)
                provider_error_counts[provider] += 1
                search_errors.append(f"{provider}: {query}: {describe_connector_error(exc)}")

    for entry in provider_entries:
        provider = entry["provider"]
        error_count = provider_error_counts.get(provider, 0)
        result_count = provider_counts.get(provider, 0)
        status = "ready"
        if error_count and result_count:
            status = "partial"
        elif error_count:
            status = "error"
        provider_results.append(
            {
                "provider": provider,
                "status": status,
                "resultCount": result_count,
                "queries": provider_query_counts.get(provider, len(queries)),
                "errors": error_count,
                "latencyMs": provider_latency_ms.get(provider, 0),
            }
        )

    deduped_results: List[Dict[str, str]] = []
    seen_urls: set[str] = set()
    for result in search_results:
        url = unique_url(result["url"])
        if url in seen_urls:
            continue
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        seen_urls.add(url)
        deduped_results.append({**result, "url": url})

    search_candidates: List[Dict[str, object]] = []
    excluded_search_candidates: List[Dict[str, object]] = []
    deep_scan_urls: List[str] = []

    for result in deduped_results[: max(1, min(int(max_results or 12), 36))]:
        parsed = urlparse(result["url"])
        host = parsed.hostname or ""
        context = str(result.get("description", ""))
        scored = score_candidate(query_tokens, result.get("title", ""), result["url"], context)
        if int(scored.get("metadataScore", 0)) >= 30 or int(scored["score"]) >= 15 or domain_matches(host, authorized_set):
            add_candidate(
                search_candidates,
                excluded_search_candidates,
                build_candidate(
                    len(search_candidates) + len(excluded_search_candidates),
                    result.get("title", ""),
                    result["url"],
                    host,
                    result.get("sourceType", "Search result"),
                    scored,
                    context,
                    result["url"],
                    [],
                    authorized_set,
                    evidence_level_override=0,
                    provider=str(result.get("provider") or ""),
                    query=str(result.get("query") or ""),
                    parent_url="",
                ),
            )
        if not domain_matches(host, authorized_set):
            deep_scan_urls.append(result["url"])

    deep_limit = max(0, min(int(deep_scan_pages or 0), 10))
    scanned = scan_public_sources(
        title=protected_title,
        aliases=alias_list,
        seed_urls=deep_scan_urls[:deep_limit],
        authorized_domains=authorized_domains,
        max_pages=deep_limit or 1,
        fetcher=fetcher,
        validate_urls=validate_urls,
    ) if deep_scan_urls and deep_limit else {
        "sourcesScanned": [],
        "candidates": [],
        "excludedCandidates": [],
        "authorizedExcluded": 0,
        "mediaReferenceCount": 0,
        "verifiedMediaCount": 0,
        "expansionUrls": [],
    }

    all_sources = list(scanned.get("sourcesScanned", []))
    scanned_candidates = list(scanned.get("candidates", []))
    scanned_excluded = list(scanned.get("excludedCandidates", []))
    expansion_urls = list(scanned.get("expansionUrls", []))
    seen_scan_urls = {unique_url(url) for url in deep_scan_urls[:deep_limit]}
    expansion_depth = max(0, min(int(expand_depth or 0), 2))
    remaining_expansion_pages = max(0, min(int(expand_pages or 0), MAX_EXPANSION_PAGES))
    per_domain_limit = max(1, min(int(per_domain_page_limit or 4), 10))
    domain_fetch_counts: Dict[str, int] = {}
    for url in seen_scan_urls:
        host = normalize_domain(urlparse(url).hostname or "")
        if host:
            domain_fetch_counts[host] = domain_fetch_counts.get(host, 0) + 1
    frontier = merge_unique_links(expansion_urls, limit=remaining_expansion_pages)

    for _level in range(expansion_depth):
        if not frontier or remaining_expansion_pages <= 0:
            break

        urls_to_scan: List[str] = []
        for link in frontier:
            link_url = unique_url(str(link.get("url") or ""))
            if not link_url or link_url in seen_scan_urls:
                continue
            link_host = normalize_domain(urlparse(link_url).hostname or "")
            if link_host and domain_fetch_counts.get(link_host, 0) >= per_domain_limit:
                continue
            urls_to_scan.append(link_url)
            seen_scan_urls.add(link_url)
            if link_host:
                domain_fetch_counts[link_host] = domain_fetch_counts.get(link_host, 0) + 1
            if len(urls_to_scan) >= remaining_expansion_pages:
                break

        if not urls_to_scan:
            break

        next_frontier: List[Dict[str, object]] = []
        for index in range(0, len(urls_to_scan), 10):
            chunk = urls_to_scan[index:index + 10]
            expanded = scan_public_sources(
                title=protected_title,
                aliases=alias_list,
                seed_urls=chunk,
                authorized_domains=authorized_domains,
                max_pages=len(chunk),
                fetcher=fetcher,
                validate_urls=validate_urls,
            )
            all_sources = merge_unique_sources(all_sources, expanded.get("sourcesScanned", []))
            scanned_candidates = merge_unique_candidates(scanned_candidates, expanded.get("candidates", []), limit=48)
            scanned_excluded = merge_unique_candidates(scanned_excluded, expanded.get("excludedCandidates", []), limit=24)
            expansion_urls = merge_unique_links(expansion_urls, expanded.get("expansionUrls", []), limit=MAX_EXPANSION_PAGES)
            next_frontier = merge_unique_links(next_frontier, expanded.get("expansionUrls", []), limit=MAX_EXPANSION_PAGES)
            remaining_expansion_pages -= len(chunk)
            if remaining_expansion_pages <= 0:
                break

        frontier = [
            link
            for link in merge_unique_links(next_frontier, limit=remaining_expansion_pages or MAX_EXPANSION_PAGES)
            if unique_url(str(link.get("url") or "")) not in seen_scan_urls
        ]

    merged_candidates = merge_unique_candidates(scanned_candidates, search_candidates, limit=24)
    merged_excluded = merge_unique_candidates(scanned_excluded, excluded_search_candidates, limit=12)
    authorized_sources_scanned = sum(1 for source in all_sources if source.get("authorized"))
    authorized_excluded = authorized_sources_scanned + len(merged_excluded)
    media_reference_count = sum(int(source.get("mediaReferences", 0)) for source in all_sources)
    media_reference_count += sum(int(candidate.get("mediaReferenceCount", 0)) for candidate in merged_candidates)
    page_fetch_latency_ms = sum(int(source.get("fetchMs", 0)) for source in all_sources)
    search_latency_ms = sum(int(item.get("latencyMs", 0)) for item in provider_results)
    provider_status = "ready"
    if search_errors or any(item.get("status") in {"missing_key", "error", "partial"} for item in provider_results):
        provider_status = "partial"
    if not deduped_results and search_errors:
        provider_status = "error"
    coverage = build_coverage_report(
        provider_names=requested_providers,
        provider_results=provider_results,
        search_result_count=len(deduped_results),
        sources=all_sources,
        candidates=merged_candidates,
        excluded_candidates=merged_excluded,
        expansion_urls=expansion_urls,
        authorized_domains=authorized_set,
        authorized_excluded=authorized_excluded,
        media_reference_count=media_reference_count,
        verified_media_count=0,
        expansion_depth=expansion_depth,
        queries_issued=sum(provider_query_counts.get(entry["provider"], len(queries)) for entry in provider_entries),
        unique_url_count=len(deduped_results),
        search_latency_ms=search_latency_ms,
        page_fetch_latency_ms=page_fetch_latency_ms,
        total_discovery_ms=int((time.perf_counter() - discovery_started) * 1000),
    )

    return {
        "query": protected_title,
        "aliases": alias_list,
        "provider": "test" if searcher else "multi-index",
        "providerStatus": provider_status,
        "setupRequired": False,
        "setupMessage": "",
        "searchQueries": queries,
        "searchResultCount": len(deduped_results),
        "searchErrors": search_errors,
        "sourceFocusDomains": source_focus,
        "providerResults": provider_results,
        "seedCount": len(deep_scan_urls[:deep_limit]),
        "sourcesScanned": all_sources,
        "candidateCount": len(merged_candidates),
        "candidates": merged_candidates,
        "excludedCandidates": merged_excluded,
        "authorizedExcluded": authorized_excluded,
        "mediaReferenceCount": media_reference_count,
        "verifiedMediaCount": 0,
        "expansionUrls": expansion_urls,
        "coverage": coverage,
        "evidenceLadder": evidence_ladder(),
        "boundary": discovery_boundary(),
    }


def build_candidate(
    index: int,
    title: str,
    url: str,
    host: str,
    source_type: str,
    scored: Dict[str, object],
    context: str,
    source_page: str,
    media_references: List[Dict[str, str]],
    authorized_domains: set[str],
    evidence_level_override: Optional[int] = None,
    provider: str = "",
    query: str = "",
    parent_url: str = "",
) -> Dict[str, object]:
    base_risk_score = int(scored.get("riskScore", scored["score"]))
    metadata_score = int(scored.get("metadataScore", scored.get("relevanceScore", 0)))
    distribution_score = int(scored.get("distributionScore", 0))
    domain_context_score = int(scored.get("domainContextScore", 0))
    authorized_by_domain = domain_matches(host, authorized_domains)
    known_low_risk_domain = low_risk_domain_matches(host)
    media_evidence_score = 0
    if media_references:
        reference_types = {item.get("type", "") for item in media_references}
        media_evidence_score = 25 if reference_types & {"MP4", "M4V", "MOV", "WEBM", "MKV", "AVI"} else 18
    if known_low_risk_domain:
        media_evidence_score = min(media_evidence_score, 8)
        domain_context_score = 0
    unknown_source_bonus = 0
    if not authorized_by_domain and not known_low_risk_domain and (media_evidence_score > 0 or distribution_score >= 8):
        unknown_source_bonus = 8
        domain_context_score = min(15, domain_context_score + unknown_source_bonus)

    score = max(0, min(100, base_risk_score + media_evidence_score + unknown_source_bonus))
    evidence_level = evidence_level_override if evidence_level_override is not None else 2 if media_references else 1
    if evidence_level < 2:
        score = min(score, 55)
    if media_evidence_score <= 0 and evidence_level < 4:
        score = min(score, 59)
    if known_low_risk_domain and evidence_level < 4:
        score = min(score, 24)
    snippet = collapse_space(context)[:220]
    source_class = classify_source(
        host,
        f"{title} {url} {snippet}",
        score,
        authorized_domains,
        media_references,
        metadata_score,
    )
    authorized = source_class == "AUTHORIZED"
    risk_level = candidate_risk_label(score, source_class, authorized, media_evidence_score, evidence_level)
    signals = dict(scored["signals"])
    signals["Media evidence"] = media_evidence_score
    signals["Domain/context"] = domain_context_score
    if known_low_risk_domain:
        signals["Low-risk source"] = 100
    if unknown_source_bonus:
        signals["Unknown source bonus"] = unknown_source_bonus
    reasons = list(scored["reasons"])
    if known_low_risk_domain:
        reasons.append("Known legitimate/catalog domain keeps this out of high-risk ranking")
    elif unknown_source_bonus:
        reasons.append("Unknown source plus distribution/media evidence increased investigation priority")

    evidence_boundary = (
        "Search-result metadata only. This is a relevance lead, not a content match."
        if evidence_level == 0
        else "Media reference found, but Content DNA verification is still required before any response case."
        if media_references
        else "Metadata-only discovery lead. A Content DNA match is required before any response case."
    )
    return {
        "id": f"DISC-{index + 1:03d}",
        "title": collapse_space(title) or host or "Untitled page",
        "url": url,
        "host": host,
        "sourceType": source_type,
        "score": score,
        "scoreType": "risk",
        "metadataScore": metadata_score,
        "relevanceScore": metadata_score,
        "riskScore": score,
        "baseRiskScore": base_risk_score,
        "distributionScore": distribution_score,
        "domainContextScore": domain_context_score,
        "mediaEvidenceScore": media_evidence_score,
        "contentMatchScore": None,
        "finalDecisionStage": "CONTENT_VERIFIED" if evidence_level >= 4 else "MEDIA_FOUND" if evidence_level >= 2 else "RELEVANT" if metadata_score >= 45 else "DISCOVERED",
        "decision": "Authorized source" if authorized else candidate_decision(score, media_evidence_score, evidence_level),
        "sourceClass": source_class,
        "riskLevel": risk_level,
        "authorized": authorized,
        "accessType": "Public page metadata",
        "evidenceLevel": evidence_level,
        "evidenceLevelLabel": EVIDENCE_LEVEL_LABELS[evidence_level],
        "verificationStatus": "Excluded authorized source" if authorized else "DNA verification pending",
        "mediaAccessStatus": "MEDIA_REFERENCE_ONLY" if media_references else "MEDIA_REFERENCE_NOT_FOUND",
        "eligibleForVerification": not authorized,
        "provider": provider,
        "query": query,
        "parentUrl": parent_url or source_page,
        "discoveredAt": datetime.now(timezone.utc).isoformat(),
        "signals": signals,
        "reasons": reasons,
        "snippet": snippet,
        "sourcePage": source_page,
        "mediaReferenceCount": len(media_references),
        "mediaReferences": media_references,
        "mediaReferenceTypes": sorted({item["type"] for item in media_references}),
        "evidenceBoundary": evidence_boundary,
    }
