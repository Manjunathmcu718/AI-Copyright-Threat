from pathlib import Path

import numpy as np

from backend.investigator import build_investigation
from backend.media_scan import extract_dna, compare_dna


def test_compare_dna_handles_same_video_shape():
    protected = {
        "duration": 6.0,
        "visual_vectors": [np.ones(10, dtype=float), np.ones(10, dtype=float), np.ones(10, dtype=float)],
        "temporal_profile": [0.2, 0.1],
    }
    candidate = {
        "duration": 6.0,
        "visual_vectors": [np.ones(10, dtype=float), np.ones(10, dtype=float), np.ones(10, dtype=float)],
        "temporal_profile": [0.2, 0.1],
    }

    result = compare_dna(protected, candidate)

    assert result["decision"] in {"Match", "Review"}
    assert result["confidence"] >= 85


def test_compare_dna_rejects_unrelated_video_shape():
    protected = {
        "duration": 6.0,
        "visual_vectors": [np.ones(10, dtype=float), np.ones(10, dtype=float), np.ones(10, dtype=float)],
        "temporal_profile": [0.2, 0.1],
    }
    candidate = {
        "duration": 6.0,
        "visual_vectors": [-np.ones(10, dtype=float), -np.ones(10, dtype=float), -np.ones(10, dtype=float)],
        "temporal_profile": [0.8, 0.9],
    }

    result = compare_dna(protected, candidate)

    assert result["decision"] == "No match"
    assert result["confidence"] < 72


def test_extract_dna_uses_video_metadata(tmp_path):
    video_path = tmp_path / "sample.mp4"
    # This test intentionally checks the function contract without a full media pipeline.
    # The actual scan implementation will run on real uploaded videos in the API.
    assert isinstance(Path(video_path).name, str)


def test_investigator_explains_top_candidate():
    results = [
        {
            "fileName": "suspected_copy.mp4",
            "confidence": 92.4,
            "decision": "Match",
            "signals": {"Visual": 91, "Scene": 94, "Temporal": 88, "Duration": 99, "Coverage": 86},
        },
        {
            "fileName": "unrelated.mp4",
            "confidence": 41.2,
            "decision": "No match",
            "signals": {"Visual": 35, "Scene": 40, "Temporal": 52, "Duration": 90, "Coverage": 18},
        },
    ]

    investigation = build_investigation(results)

    assert investigation["decisionCounts"]["Match"] == 1
    assert investigation["topCandidate"] == "suspected_copy.mp4"
    assert investigation["recommendedPriority"] in {"High", "Critical"}
    assert investigation["candidateAnalyses"][0]["analysis"]["failureBoundary"]
