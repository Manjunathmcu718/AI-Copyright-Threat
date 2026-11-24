from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import cv2
import numpy as np


FrameVector = np.ndarray


def normalize(values: Iterable[float]) -> FrameVector:
    vector = np.asarray(list(values), dtype=np.float32)
    norm = float(np.linalg.norm(vector)) or 1.0
    return vector / norm


def cosine_similarity(first: Sequence[float], second: Sequence[float]) -> float:
    length = min(len(first), len(second))
    if length <= 0:
        return 0.0
    dot = sum(float(a) * float(b) for a, b in zip(first[:length], second[:length]))
    return float(max(0.0, min(1.0, dot)))


def resample_array(values: Sequence[float], goal_length: int) -> List[float]:
    if not values:
        return [0.0 for _ in range(goal_length)]
    if goal_length <= 1:
        return [float(values[0])]

    result: List[float] = []
    for index in range(goal_length):
        position = (index / (goal_length - 1)) * (len(values) - 1)
        left = int(math.floor(position))
        right = min(len(values) - 1, left + 1)
        mix = position - left
        left_value = float(values[left])
        right_value = float(values[right])
        result.append(left_value * (1.0 - mix) + right_value * mix)
    return result


def build_temporal_profile(vectors: Sequence[Sequence[float]]) -> List[float]:
    if len(vectors) < 2:
        return [0.0]

    profile: List[float] = []
    for index in range(1, len(vectors)):
        profile.append(1.0 - cosine_similarity(vectors[index - 1], vectors[index]))
    return profile


def build_dna_id(vectors: Sequence[Sequence[float]], duration: float) -> str:
    digest = hashlib.sha1()
    digest.update(str(round(duration, 3)).encode("utf-8"))
    for vector in vectors:
        values = np.asarray(vector, dtype=np.float32)
        digest.update(np.round(values[:48], 4).tobytes())
    hexdigest = digest.hexdigest().upper()
    return f"CS-DNA {hexdigest[:4]} {hexdigest[4:8]} {hexdigest[8:12]}"


def sample_video_for_dna(video_path: str | Path) -> Dict[str, object]:
    video_path = Path(video_path)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    fps = float(capture.get(cv2.CAP_PROP_FPS)) or 30.0
    frames: List[np.ndarray] = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frames.append(frame)
    capture.release()

    if not frames:
        raise ValueError(f"No frames found in video: {video_path}")

    # A short candidate can be one continuous segment from a longer original.
    # Eight sparse samples are not enough to find that temporal offset, so keep
    # a bounded two-samples-per-second fingerprint (12–24 frames per video).
    duration = max(1.0, float(len(frames)) / fps)
    sample_count = min(24, max(12, int(round(duration * 2))))
    sample_count = min(sample_count, len(frames))
    sampled = []
    for frame_index in np.linspace(0, len(frames) - 1, num=sample_count, dtype=int):
        frame = frames[int(frame_index)]
        resized = cv2.resize(frame, (20, 12), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY).astype(np.float32)
        values = gray.ravel() / 255.0
        mean = float(np.mean(values))
        centered = values - mean
        norm = float(np.linalg.norm(centered)) or 1.0
        sampled.append((centered / norm).tolist())

    temporal_profile = build_temporal_profile(sampled)
    return {
        "duration": duration,
        "visual_vectors": [np.asarray(vector, dtype=np.float32) for vector in sampled],
        "temporal_profile": temporal_profile,
        "sampled_frames": len(sampled),
        "dna_id": build_dna_id(sampled, duration),
        "file_name": video_path.name,
        "file_size": video_path.stat().st_size if video_path.exists() else 0,
    }


def strongest_ordered_segment(matches: Sequence[Dict[str, float]]) -> Dict[str, float]:
    """Find a contiguous, in-order run of strong frame correspondences.

    A trimmed or speed-modified candidate is not expected to cover the entire
    protected timeline. This identifies the strongest continuous segment without
    allowing unrelated isolated frames to become a copy claim.
    """
    threshold = 0.82
    best: List[Dict[str, float]] = []
    current: List[Dict[str, float]] = []
    previous_index = -1

    for match in matches:
        score = float(match["score"])
        source_index = int(match["index"])
        if score >= threshold and (not current or source_index > previous_index):
            current.append(match)
            previous_index = source_index
        else:
            if len(current) > len(best):
                best = current
            current = [match] if score >= threshold else []
            previous_index = source_index if current else -1

    if len(current) > len(best):
        best = current

    if not best:
        return {
            "length": 0.0,
            "mean": 0.0,
            "candidate_fraction": 0.0,
            "source_start": -1.0,
            "source_end": -1.0,
        }

    return {
        "length": float(len(best)),
        "mean": float(sum(float(match["score"]) for match in best) / len(best)),
        "candidate_fraction": float(len(best) / max(1, len(matches))),
        "source_start": float(best[0]["index"]),
        "source_end": float(best[-1]["index"]),
    }


def align_frames(protected: Dict[str, object], candidate: Dict[str, object]) -> Dict[str, object]:
    protected_frames = protected["visual_vectors"]
    candidate_frames = candidate["visual_vectors"]

    matches = []
    for candidate_vector in candidate_frames:
        best_score = 0.0
        best_index = 0
        for protected_index, protected_vector in enumerate(protected_frames):
            score = cosine_similarity(protected_vector, candidate_vector)
            if score > best_score:
                best_score = score
                best_index = protected_index
        matches.append({"score": best_score, "index": best_index})

    mean = sum(item["score"] for item in matches) / max(len(matches), 1)
    ordered_pairs = 0
    for index in range(1, len(matches)):
        if matches[index]["index"] >= matches[index - 1]["index"]:
            ordered_pairs += 1

    order = 1.0 if len(matches) <= 1 else ordered_pairs / (len(matches) - 1)
    coverage = len({item["index"] for item in matches}) / max(len(protected_frames), 1)
    scene = float(np.clip(mean * 0.72 + order * 0.2 + coverage * 0.08, 0.0, 1.0))
    return {
        "mean": float(mean),
        "order": float(order),
        "coverage": float(coverage),
        "scene": scene,
        "ordered_segment": strongest_ordered_segment(matches),
    }


def temporal_similarity(protected: Dict[str, object], candidate: Dict[str, object]) -> float:
    protected_profile = protected.get("temporal_profile", [])
    candidate_profile = candidate.get("temporal_profile", [])
    length = max(len(protected_profile), len(candidate_profile), 1)
    first = resample_array(protected_profile, length)
    second = resample_array(candidate_profile, length)
    average_delta = sum(abs(float(a) - float(b)) for a, b in zip(first, second)) / length
    return float(np.clip(1.0 - average_delta * 2.2, 0.0, 1.0))


def compare_dna(protected: Dict[str, object], candidate: Dict[str, object]) -> Dict[str, object]:
    alignment = align_frames(protected, candidate)
    duration_score = min(float(protected.get("duration", 1.0)), float(candidate.get("duration", 1.0))) / max(float(protected.get("duration", 1.0)), float(candidate.get("duration", 1.0)), 1.0)
    temporal_score = temporal_similarity(protected, candidate)

    weights = {"visual": 0.48, "scene": 0.28, "temporal": 0.14, "metadata": 0.10}
    if duration_score < 0.76 and alignment["scene"] > 0.72:
        weights["scene"] += 0.08
        weights["visual"] -= 0.04
        weights["metadata"] -= 0.04
    if alignment["mean"] < 0.76 and temporal_score > 0.72:
        weights["scene"] += 0.06
        weights["temporal"] += 0.04
        weights["visual"] -= 0.10

    confidence = (
        alignment["mean"] * weights["visual"]
        + alignment["scene"] * weights["scene"]
        + temporal_score * weights["temporal"]
        + duration_score * weights["metadata"]
    )
    segment = alignment["ordered_segment"]
    segment_length = int(segment["length"])
    segment_mean = float(segment["mean"])
    segment_candidate_fraction = float(segment["candidate_fraction"])
    protected_frame_count = max(1, len(protected["visual_vectors"]))
    segment_source_fraction = segment_length / protected_frame_count
    partial_segment_evidence = (
        duration_score < 0.80
        and segment_length >= 3
        and segment_mean >= 0.82
        and max(segment_candidate_fraction, segment_source_fraction) >= 0.25
    )
    low_coverage_only = alignment["coverage"] < 0.45 and alignment["mean"] < 0.93
    bounded_confidence = min(confidence, 0.84) if low_coverage_only else confidence

    strong_copy_evidence = (
        alignment["mean"] >= 0.80
        and alignment["scene"] >= 0.76
        and alignment["coverage"] >= 0.45
        and (temporal_score >= 0.45 or duration_score >= 0.65)
    )
    review_evidence = (
        alignment["mean"] >= 0.62
        and alignment["scene"] >= 0.55
        and alignment["coverage"] >= 0.30
    )

    # A weighted score is not sufficient on its own. A Match must also pass
    # independent visual, scene, and coverage gates so unrelated clips cannot
    # become a Match just because of a coincidental low-level similarity.
    if bounded_confidence >= 0.86 and strong_copy_evidence:
        decision = "Match"
    elif bounded_confidence >= 0.72 and review_evidence:
        decision = "Review"
    elif partial_segment_evidence:
        # A verified excerpt is useful evidence, but it is not treated as a
        # full-copy match until a reviewer confirms the short source coverage.
        decision = "Review"
    else:
        decision = "No match"

    partial_confidence = (
        segment_mean * 0.65
        + segment_candidate_fraction * 0.20
        + segment_source_fraction * 0.15
    )
    if decision == "Review" and partial_segment_evidence:
        bounded_confidence = max(bounded_confidence, partial_confidence)

    signals = {
        "Visual": int(round(alignment["mean"] * 100)),
        "Scene": int(round(alignment["scene"] * 100)),
        "Temporal": int(round(temporal_score * 100)),
        "Duration": int(round(duration_score * 100)),
        "Coverage": int(round(alignment["coverage"] * 100)),
    }

    checks = [
        ("Visual frame signature", signals["Visual"], 80),
        ("Scene order", signals["Scene"], 76),
        ("Temporal motion profile", signals["Temporal"], 45),
        ("Timeline duration", signals["Duration"], 35),
        ("Shared source coverage", signals["Coverage"], 45),
    ]
    matching_evidence = [
        f"{label} {score}% meets the {threshold}% copy-evidence threshold"
        for label, score, threshold in checks
        if score >= threshold
    ]
    if partial_segment_evidence:
        matching_evidence.append(
            "Contiguous partial segment found: "
            f"{segment_length} sampled candidate frames align in order at {round(segment_mean * 100)}% visual similarity "
            f"({round(segment_candidate_fraction * 100)}% of the candidate timeline; "
            f"{round(segment_source_fraction * 100)}% of the protected timeline)."
        )
    mismatch_evidence = [
        f"{label} {score}% is below the {threshold}% copy-evidence threshold"
        for label, score, threshold in checks
        if score < threshold
    ]
    decision_reason = (
        "Independent visual, scene, and coverage checks support a content match"
        if decision == "Match"
        else "Some evidence is present, but the result requires human review"
        if partial_segment_evidence
        else "Some evidence is present, but the result requires human review"
        if decision == "Review"
        else "No independent copy-evidence threshold was met; verified copy confidence is 0%"
        if not matching_evidence
        else "Independent copy-evidence checks did not support the same-content claim"
    )
    reasons = [*matching_evidence, *mismatch_evidence, decision_reason]
    verified_copy_confidence = bounded_confidence if decision != "No match" else 0.0

    return {
        "fileName": candidate.get("file_name"),
        "duration": float(candidate.get("duration", 0.0)),
        "dnaId": candidate.get("dna_id"),
        "sampledFrames": candidate.get("sampled_frames"),
        "confidence": round(float(verified_copy_confidence) * 100, 1),
        "rawSimilarity": round(float(bounded_confidence) * 100, 1),
        "decision": decision,
        "signals": signals,
        "weights": {key: int(round(value * 100)) for key, value in weights.items()},
        "partialSegment": {
            "detected": partial_segment_evidence,
            "matchedFrames": segment_length,
            "candidateCoverage": round(segment_candidate_fraction * 100, 1),
            "sourceCoverage": round(segment_source_fraction * 100, 1),
            "visualSimilarity": round(segment_mean * 100, 1),
        },
        "matchingEvidence": matching_evidence,
        "mismatchEvidence": mismatch_evidence,
        "reasons": reasons,
    }


def extract_dna(video_path: str | Path) -> Dict[str, object]:
    dna = sample_video_for_dna(video_path)
    return dna


def scan_folder(protected_video: str | Path, candidate_dir: str | Path) -> List[Dict[str, object]]:
    protected_dna = extract_dna(protected_video)
    matching_dir = Path(candidate_dir)
    if not matching_dir.exists():
        raise ValueError(f"Candidate directory does not exist: {matching_dir}")

    results = []
    for candidate in sorted(matching_dir.iterdir()):
        if candidate.is_dir() or candidate.suffix.lower() not in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
            continue
        candidate_dna = extract_dna(candidate)
        result = compare_dna(protected_dna, candidate_dna)
        result["fileName"] = candidate.name
        result["fileSize"] = candidate.stat().st_size
        results.append(result)

    return sorted(results, key=lambda item: float(item["confidence"]), reverse=True)
