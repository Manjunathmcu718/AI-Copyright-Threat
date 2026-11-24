from unittest.mock import patch
from fastapi import HTTPException

from backend.main import OriginalLinkSearchRequest, search_from_original_link


def test_original_link_uses_page_title_and_excludes_original_domain():
    page = {"sourcesScanned": [{"ok": True, "title": "Example Movie | Official", "error": ""}]}
    search_result = {"candidates": [{"url": "https://other.example/movie"}], "providerStatus": "ready"}
    with patch("backend.main.is_public_http_url", return_value=(True, "")), patch(
        "backend.main.scan_public_sources", return_value=page
    ), patch("backend.main.search_public_web", return_value=search_result) as search:
        result = search_from_original_link(OriginalLinkSearchRequest(originalUrl="https://official.example/movie"))

    assert result["title"] == "Example Movie"
    assert result["verificationStatus"] == "UNVERIFIED_METADATA_LEADS"
    assert result["discovery"] == search_result
    assert search.call_args.kwargs["authorized_domains"] == ["official.example"]


def test_original_link_falls_back_to_user_title_if_page_blocked():
    page = {"sourcesScanned": [{"ok": False, "error": "Access denied"}]}
    with patch("backend.main.is_public_http_url", return_value=(True, "")), patch(
        "backend.main.scan_public_sources", return_value=page
    ), patch("backend.main.search_public_web", return_value={"candidates": []}) as search:
        result = search_from_original_link(
            OriginalLinkSearchRequest(originalUrl="https://official.example/movie", title="Example Movie")
        )

    assert result["originalPageAccessible"] is False
    assert result["titleSource"] == "provided"
    assert search.call_args.kwargs["title"] == "Example Movie"


def test_original_link_requires_title_when_metadata_unavailable():
    with patch("backend.main.is_public_http_url", return_value=(True, "")), patch(
        "backend.main.scan_public_sources", return_value={"sourcesScanned": [{"ok": False}]}
    ):
        try:
            search_from_original_link(OriginalLinkSearchRequest(originalUrl="https://official.example/movie"))
        except HTTPException as error:
            assert error.status_code == 400
        else:
            raise AssertionError("Expected a missing-title error")


if __name__ == "__main__":
    test_original_link_uses_page_title_and_excludes_original_domain()
    test_original_link_falls_back_to_user_title_if_page_blocked()
    test_original_link_requires_title_when_metadata_unavailable()
