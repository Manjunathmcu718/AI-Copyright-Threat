from backend.discovery import (
    FetchResult,
    build_search_queries,
    common_crawl_pattern_from_query,
    extract_common_crawl_results,
    scan_public_sources,
    search_public_web,
    unique_url,
)


def test_public_source_scan_extracts_ranked_candidates():
    html = """
    <html>
      <head>
        <title>Project Monsoon episodes and movie archive</title>
        <meta name="description" content="Watch Project Monsoon clips and episodes in HD">
      </head>
      <body>
        <a href="/project-monsoon-s01e01-watch">Project Monsoon S01E01 Watch HD</a>
        <a href="/unrelated-title">Another title</a>
      </body>
    </html>
    """

    def fake_fetcher(url: str) -> FetchResult:
        return FetchResult(url=url, final_url=url, status=200, content_type="text/html", text=html)

    result = scan_public_sources(
        title="Project Monsoon",
        aliases=["Monsoon"],
        seed_urls=["https://public.example/list"],
        fetcher=fake_fetcher,
        validate_urls=False,
    )

    assert result["candidateCount"] >= 1
    assert result["candidates"][0]["metadataScore"] >= 70
    assert result["candidates"][0]["riskScore"] < 70
    assert any("Content DNA" in item for item in result["boundary"])


def test_public_source_scan_excludes_authorized_domains():
    html = """
    <html>
      <head><title>Project Monsoon official streaming page</title></head>
      <body><a href="/watch/project-monsoon">Project Monsoon Watch</a></body>
    </html>
    """

    def fake_fetcher(url: str) -> FetchResult:
        return FetchResult(url=url, final_url=url, status=200, content_type="text/html", text=html)

    result = scan_public_sources(
        title="Project Monsoon",
        aliases=[],
        seed_urls=["https://official.example/project-monsoon"],
        authorized_domains=["official.example"],
        fetcher=fake_fetcher,
        validate_urls=False,
    )

    assert result["candidateCount"] == 0
    assert result["authorizedExcluded"] == 1
    assert result["sourcesScanned"][0]["sourceClass"] == "AUTHORIZED"
    assert result["sourcesScanned"][0]["skipped"] is True


def test_public_source_scan_detects_media_reference_without_downloading():
    html = """
    <html>
      <head><title>Project Monsoon watch page</title></head>
      <body>
        <video src="/media/project-monsoon-preview.m3u8"></video>
        <a href="/project-monsoon-watch">Project Monsoon watch HD</a>
      </body>
    </html>
    """

    def fake_fetcher(url: str) -> FetchResult:
        return FetchResult(url=url, final_url=url, status=200, content_type="text/html", text=html)

    result = scan_public_sources(
        title="Project Monsoon",
        aliases=[],
        seed_urls=["https://unknown.example/project-monsoon"],
        fetcher=fake_fetcher,
        validate_urls=False,
    )

    assert result["candidateCount"] >= 1
    assert result["mediaReferenceCount"] >= 1
    assert result["candidates"][0]["evidenceLevel"] == 2
    assert result["candidates"][0]["mediaEvidenceScore"] > 0
    assert result["candidates"][0]["contentMatchScore"] is None
    assert result["verifiedMediaCount"] == 0


def test_public_source_scan_keeps_news_review_low_risk():
    html = """
    <html>
      <head>
        <title>Salaar movie review and box office collection</title>
        <meta name="description" content="News analysis, cast, review, and trailer discussion for Salaar">
      </head>
      <body>Salaar review, cast, box office collection, news update.</body>
    </html>
    """

    def fake_fetcher(url: str) -> FetchResult:
        return FetchResult(url=url, final_url=url, status=200, content_type="text/html", text=html)

    result = scan_public_sources(
        title="Salaar",
        aliases=["Salaar Part 1 Ceasefire"],
        seed_urls=["https://news.example/salaar-review"],
        fetcher=fake_fetcher,
        validate_urls=False,
    )

    assert result["candidateCount"] >= 1
    assert result["candidates"][0]["metadataScore"] >= 70
    assert result["candidates"][0]["riskScore"] < 35
    assert result["candidates"][0]["riskLevel"] == "Low-risk relevant"
    assert result["candidates"][0]["finalDecisionStage"] == "RELEVANT"


def test_public_source_scan_keeps_justwatch_low_risk():
    html = """
    <html>
      <head>
        <title>Salaar streaming online - JustWatch</title>
        <meta name="description" content="Find where to watch Salaar online on legal streaming services">
      </head>
      <body>Watch providers, rent, buy, and streaming availability.</body>
    </html>
    """

    def fake_fetcher(url: str) -> FetchResult:
        return FetchResult(url=url, final_url=url, status=200, content_type="text/html", text=html)

    result = scan_public_sources(
        title="Salaar",
        aliases=["Salaar Part 1 Ceasefire"],
        seed_urls=["https://www.justwatch.com/in/movie/salaar"],
        fetcher=fake_fetcher,
        validate_urls=False,
    )

    assert result["candidateCount"] >= 1
    assert result["candidates"][0]["sourceClass"] == "LEGITIMATE"
    assert result["candidates"][0]["riskScore"] < 35
    assert result["candidates"][0]["riskLevel"] == "Low-risk relevant"


def test_public_source_scan_marks_unknown_media_page_high_risk():
    html = """
    <html>
      <head>
        <title>Salaar full movie 1080p download</title>
        <meta name="description" content="Salaar full movie watch online download WEB-DL 1080p">
      </head>
      <body>
        <video src="https://cdn.unknown.example/salaar-copy.mp4"></video>
        <a href="/salaar-720p-download">Salaar 720p download</a>
      </body>
    </html>
    """

    def fake_fetcher(url: str) -> FetchResult:
        return FetchResult(url=url, final_url=url, status=200, content_type="text/html", text=html)

    result = scan_public_sources(
        title="Salaar",
        aliases=["Salaar Part 1 Ceasefire"],
        seed_urls=["https://unknown.example/salaar-1080p-download"],
        fetcher=fake_fetcher,
        validate_urls=False,
    )

    assert result["candidateCount"] >= 1
    candidate = result["candidates"][0]
    assert candidate["sourceClass"] == "SUSPECTED"
    assert candidate["riskLevel"] == "High-risk lead"
    assert candidate["riskScore"] >= 65
    assert candidate["mediaEvidenceScore"] > 0
    assert candidate["contentMatchScore"] is None
    assert candidate["finalDecisionStage"] == "MEDIA_FOUND"


def test_public_source_scan_reports_source_failures():
    def fake_fetcher(url: str) -> FetchResult:
        raise TimeoutError("timed out")

    result = scan_public_sources(
        title="Project Monsoon",
        aliases=[],
        seed_urls=["https://public.example/list"],
        fetcher=fake_fetcher,
        validate_urls=False,
    )

    assert result["candidateCount"] == 0
    assert result["sourcesScanned"][0]["ok"] is False
    assert "timed out" in result["sourcesScanned"][0]["error"]


def test_public_search_reports_missing_key_without_network_call():
    result = search_public_web(
        title="Project Monsoon",
        aliases=["Monsoon"],
        authorized_domains=[],
        source_domains=[],
        providers=["brave"],
        api_key="",
    )

    assert result["provider"] == "multi-index"
    assert result["providerStatus"] == "missing_key"
    assert result["setupRequired"] is True
    assert "BRAVE_SEARCH_API_KEY" in result["setupMessage"]
    assert "BING_SEARCH_API_KEY" in result["setupMessage"]
    assert "GOOGLE_CSE_API_KEY" in result["setupMessage"]
    assert result["searchQueries"]
    assert result["providerResults"]
    assert result["candidateCount"] == 0


def test_search_queries_normalize_uploaded_filename_titles():
    queries = build_search_queries("TRAIL_COPY", ["TRAIL COPY"])

    assert '"TRAIL COPY"' in queries
    assert '"TRAIL COPY" "watch online"' in queries
    assert '"TRAIL COPY" "WEB-DL"' in queries
    assert len(queries) == len(set(queries))


def test_unique_url_strips_tracking_params_and_fragments():
    normalized = unique_url("HTTPS://Example.COM/path/?utm_source=x&a=1&fbclid=y#player")

    assert normalized == "https://example.com/path?a=1"


def test_common_crawl_pattern_and_result_extraction():
    assert common_crawl_pattern_from_query('"Salaar" full movie') == "*salaar*full*movie*"

    result = extract_common_crawl_results(
        {
            "records": [
                {
                    "url": "https://unknown.example/watch/salaar-full-movie",
                    "timestamp": "20260901010101",
                    "collection": "CC-MAIN-2026-33",
                }
            ]
        },
        '"Salaar" full movie',
    )

    assert result[0]["url"] == "https://unknown.example/watch/salaar-full-movie"
    assert result[0]["sourceType"] == "Common Crawl URL index"


def test_public_search_builds_queue_from_results_and_deep_scans_pages():
    search_payload = {
        "web": {
            "results": [
                {
                    "title": "Project Monsoon watch archive",
                    "url": "https://public.example/project-monsoon-watch",
                    "description": "Project Monsoon full video stream mirror listing",
                },
                {
                    "title": "Project Monsoon official page",
                    "url": "https://official.example/project-monsoon",
                    "description": "Official authorized streaming destination",
                },
            ]
        }
    }
    page_html = """
    <html>
      <head><title>Project Monsoon public watch page</title></head>
      <body>
        <video src="/media/project-monsoon-transformed.m3u8"></video>
        <a href="/project-monsoon-episode-watch">Project Monsoon episode watch HD</a>
      </body>
    </html>
    """

    def fake_searcher(query: str, count: int, country: str, search_lang: str) -> dict:
        assert count > 0
        assert country == "IN"
        assert search_lang == "en"
        return search_payload

    def fake_fetcher(url: str) -> FetchResult:
        return FetchResult(url=url, final_url=url, status=200, content_type="text/html", text=page_html)

    result = search_public_web(
        title="Project Monsoon",
        aliases=["Monsoon"],
        authorized_domains=["official.example"],
        max_results=4,
        deep_scan_pages=2,
        api_key="test-key",
        searcher=fake_searcher,
        fetcher=fake_fetcher,
        validate_urls=False,
    )

    assert result["providerStatus"] == "ready"
    assert result["searchResultCount"] == 2
    assert result["candidateCount"] >= 1
    assert result["mediaReferenceCount"] >= 1
    assert result["authorizedExcluded"] >= 1
    assert result["candidates"][0]["eligibleForVerification"] is True
    assert result["coverage"]["searchResults"] == 2


def test_public_search_does_not_let_query_text_inflate_article_risk():
    search_payload = {
        "web": {
            "results": [
                {
                    "title": "Salaar movie review and box office analysis",
                    "url": "https://news.example/salaar-review",
                    "description": "Review, cast, trailer, box office collection, and news analysis.",
                }
            ]
        }
    }

    def fake_searcher(query: str, count: int, country: str, search_lang: str) -> dict:
        assert "Salaar" in query
        return search_payload

    result = search_public_web(
        title="Salaar",
        aliases=[],
        authorized_domains=[],
        max_results=1,
        deep_scan_pages=0,
        api_key="test-key",
        searcher=fake_searcher,
        validate_urls=False,
    )

    assert result["candidateCount"] >= 1
    assert result["candidates"][0]["metadataScore"] >= 70
    assert result["candidates"][0]["riskScore"] < 35
    assert result["candidates"][0]["evidenceLevel"] == 0


def test_public_search_expands_from_relevant_public_links():
    search_payload = {
        "web": {
            "results": [
                {
                    "title": "Project Monsoon public archive",
                    "url": "https://first.example/project-monsoon",
                    "description": "Project Monsoon watch online mirror index",
                }
            ]
        }
    }

    pages = {
        "https://first.example/project-monsoon": """
        <html>
          <head><title>Project Monsoon mirror index</title></head>
          <body>
            <a href="https://second.example/project-monsoon-1080p-watch">Project Monsoon 1080p watch</a>
          </body>
        </html>
        """,
        "https://second.example/project-monsoon-1080p-watch": """
        <html>
          <head><title>Project Monsoon 1080p watch page</title></head>
          <body>
            <video src="/media/project-monsoon-public-reference.m3u8"></video>
          </body>
        </html>
        """,
    }

    def fake_searcher(query: str, count: int, country: str, search_lang: str) -> dict:
        return search_payload

    def fake_fetcher(url: str) -> FetchResult:
        return FetchResult(url=url, final_url=url, status=200, content_type="text/html", text=pages[url])

    result = search_public_web(
        title="Project Monsoon",
        aliases=[],
        authorized_domains=[],
        max_results=2,
        deep_scan_pages=1,
        expand_depth=1,
        expand_pages=4,
        api_key="test-key",
        searcher=fake_searcher,
        fetcher=fake_fetcher,
        validate_urls=False,
    )

    assert result["provider"] == "test"
    assert result["coverage"]["pagesEvaluated"] == 2
    assert result["coverage"]["domainsEvaluated"] == 2
    assert result["coverage"]["expansionQueued"] >= 1
    assert any(source["host"] == "second.example" for source in result["sourcesScanned"])
