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

    frames: List[np.ndarray] = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frames.append(frame)
    capture.release()

    if not frames:
        raise ValueError(f"No frames found in video: {video_path}")

    sample_count = min(8, max(4, len(frames)))
    sampled = []
    stride = max(1, len(frames) // sample_count)
    for frame in frames[::stride][:sample_count]:
        resized = cv2.resize(frame, (20, 12), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY).astype(np.float32)
        values = gray.ravel() / 255.0
        mean = float(np.mean(values))
        centered = values - mean
        norm = float(np.linalg.norm(centered)) or 1.0
        sampled.append((centered / norm).tolist())

    temporal_profile = build_temporal_profile(sampled)
    duration = max(1.0, float(len(frames)) / max(1.0, 30.0))
    return {
        "duration": duration,
        "visual_vectors": [np.asarray(vector, dtype=np.float32) for vector in sampled],
        "temporal_profile": temporal_profile,
        "sampled_frames": len(sampled),
        "dna_id": build_dna_id(sampled, duration),
        "file_name": video_path.name,
        "file_size": video_path.stat().st_size if video_path.exists() else 0,
    }


def align_frames(protected: Dict[str, object], candidate: Dict[str, object]) -> Dict[str, float]:
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
    return {"mean": float(mean), "order": float(order), "coverage": float(coverage), "scene": scene}


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
    low_coverage_only = alignment["coverage"] < 0.45 and alignment["mean"] < 0.93
    bounded_confidence = min(confidence, 0.84) if low_coverage_only else confidence

    if bounded_confidence >= 0.86:
        decision = "Match"
    elif bounded_confidence >= 0.72:
        decision = "Review"
    else:
        decision = "No match"

    signals = {
        "Visual": int(round(alignment["mean"] * 100)),
        "Scene": int(round(alignment["scene"] * 100)),
        "Temporal": int(round(temporal_score * 100)),
        "Duration": int(round(duration_score * 100)),
        "Coverage": int(round(alignment["coverage"] * 100)),
    }

    reasons = [
        f"Visual frame signature {signals['Visual']}%",
        f"Scene order and coverage {signals['Scene']}%",
        f"Temporal motion profile {signals['Temporal']}%",
        "Duration profile supports the comparison" if duration_score >= 0.76 else "Duration mismatch keeps the decision gated",
        "Candidate crossed the high-confidence threshold" if decision == "Match" else "Evidence is meaningful but needs human review" if decision == "Review" else "Evidence is below same-content threshold",
    ]

    return {
        "fileName": candidate.get("file_name"),
        "duration": float(candidate.get("duration", 0.0)),
        "dnaId": candidate.get("dna_id"),
        "sampledFrames": candidate.get("sampled_frames"),
        "confidence": round(float(bounded_confidence) * 100, 1),
        "decision": decision,
        "signals": signals,
        "weights": {key: int(round(value * 100)) for key, value in weights.items()},
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
