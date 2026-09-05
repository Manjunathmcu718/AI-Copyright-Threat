from backend.url_media import normalize_candidate_urls, validate_direct_media_url, url_verification_boundary


def test_normalize_candidate_urls_dedupes_and_limits():
    urls = [f"https://public.example/video-{index}.mp4" for index in range(8)]
    result = normalize_candidate_urls([urls[0], urls[0], *urls[1:]])

    assert result[0] == urls[0]
    assert len(result) == 6


def test_validate_direct_media_url_rejects_non_video_page_before_fetch():
    ok, reason = validate_direct_media_url("https://public.example/watch/project-monsoon")

    assert ok is False
    assert "direct public video file URLs" in reason


def test_url_verification_boundary_blocks_hidden_or_stream_capture_claims():
    boundary = " ".join(url_verification_boundary())

    assert "No HLS/DASH stream capture" in boundary
    assert "No login" in boundary
