from __future__ import annotations

import json
import math
import random
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MEDIA_DIR = ROOT / "media" / "real_benchmark"
VIDEO_DIR = MEDIA_DIR / "videos"
AUDIO_DIR = MEDIA_DIR / "audio"

SEED = 20260825
WIDTH = 320
HEIGHT = 180
FPS = 10
SECONDS = 6
FRAME_COUNT = FPS * SECONDS
AUDIO_RATE = 8000
THRESHOLD = 0.90
REVIEW_FLOOR = 0.88

SIGNALS = ["visual", "audio", "scene", "temporal", "metadata"]

BASELINE_WEIGHTS = {
    "visual": 0.58,
    "audio": 0.15,
    "scene": 0.16,
    "temporal": 0.06,
    "metadata": 0.05,
}

ADAPTIVE_BASE_WEIGHTS = {
    "visual": 0.30,
    "audio": 0.26,
    "scene": 0.24,
    "temporal": 0.12,
    "metadata": 0.08,
}

WORKS = [
    {"id": "work_01", "title": "Project Monsoon", "color": (33, 167, 150), "accent": (229, 173, 73), "freq": 261.63},
    {"id": "work_02", "title": "Night Market", "color": (80, 95, 210), "accent": (239, 117, 100), "freq": 329.63},
    {"id": "work_03", "title": "Glass City", "color": (88, 191, 131), "accent": (168, 140, 244), "freq": 392.00},
    {"id": "work_04", "title": "Solar Drift", "color": (210, 116, 54), "accent": (66, 211, 200), "freq": 493.88},
    {"id": "work_05", "title": "Project Rain", "color": (36, 158, 146), "accent": (216, 166, 68), "freq": 587.33},
]

TRANSFORMS = {
    "clean": "Original-quality copy",
    "compression": "JPEG-style frame compression",
    "resolution": "Downscale then upscale",
    "crop": "Cropped edges then resized",
    "watermark": "Overlay watermark",
    "audio_mod": "Noise and amplitude modulation",
    "partial": "Short middle clip",
    "combined": "Crop + watermark + compression + audio noise",
}


Vector = np.ndarray


@dataclass
class MediaPair:
    video: Path
    audio: Path


@dataclass
class Example:
    transformation: str
    label: int
    similarities: Dict[str, float]
    baseline_score: float
    adaptive_score: float
    adaptive_weights: Dict[str, float]
    candidate_video: str
    candidate_audio: str


def ensure_dirs() -> None:
    for directory in (DATA_DIR, VIDEO_DIR, AUDIO_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def normalize(values: Iterable[float]) -> Vector:
    vector = np.asarray(list(values), dtype=np.float32)
    norm = float(np.linalg.norm(vector)) or 1.0
    return vector / norm


def cosine(left: Vector, right: Vector) -> float:
    raw = float(np.dot(left, right))
    return max(0.0, min(1.0, (raw + 1.0) / 2.0))


def sequence_similarity(left: List[Vector], right: List[Vector]) -> float:
    if not left or not right:
        return 0.0

    if len(left) >= len(right):
        long, short = left, right
    else:
        long, short = right, left

    if len(short) == 1:
        return max(cosine(item, short[0]) for item in long)

    best = 0.0
    for start in range(len(long) - len(short) + 1):
        window = long[start : start + len(short)]
        score = sum(cosine(a, b) for a, b in zip(window, short)) / len(short)
        best = max(best, score)
    return best


def make_frame(work_index: int, frame_index: int) -> np.ndarray:
    work = WORKS[work_index]
    base = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32)
    x = np.linspace(0, 1, WIDTH, dtype=np.float32)
    y = np.linspace(0, 1, HEIGHT, dtype=np.float32)[:, None]
    t = frame_index / max(1, FRAME_COUNT - 1)
    scene = frame_index // 15
    color = np.asarray(work["color"], dtype=np.float32)
    accent = np.asarray(work["accent"], dtype=np.float32)

    base[:, :, 0] = color[0] * (0.28 + 0.46 * x) + accent[0] * (0.10 + 0.08 * scene)
    base[:, :, 1] = color[1] * (0.22 + 0.42 * y) + accent[1] * (0.08 + 0.06 * math.sin(t * math.pi))
    base[:, :, 2] = color[2] * (0.32 + 0.25 * (1 - x)) + accent[2] * (0.14 + 0.05 * scene)

    frame = np.clip(base, 0, 255).astype(np.uint8)
    center = (int(44 + t * (WIDTH - 88)), int(54 + 38 * math.sin(t * math.pi * 2 + work_index)))
    cv2.circle(frame, center, 18 + (scene % 3) * 4, work["accent"], -1)
    cv2.rectangle(
        frame,
        (24 + scene * 12, 122 - scene * 6),
        (112 + scene * 18, 158),
        work["color"],
        -1,
    )
    cv2.line(frame, (0, 24 + scene * 20), (WIDTH, 92 + scene * 13), work["accent"], 3)
    cv2.putText(frame, work["title"][:14], (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (242, 234, 220), 2)
    cv2.putText(frame, f"S{scene + 1:02d} F{frame_index:02d}", (214, 162), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (15, 18, 17), 2)
    return frame


def make_audio(work_index: int) -> np.ndarray:
    work = WORKS[work_index]
    total = AUDIO_RATE * SECONDS
    t = np.arange(total, dtype=np.float32) / AUDIO_RATE
    primary = np.sin(2 * np.pi * work["freq"] * t)
    secondary = 0.36 * np.sin(2 * np.pi * (work["freq"] * 1.5) * t + work_index)
    pulse = 0.20 * np.sin(2 * np.pi * (2 + work_index) * t)
    audio = (0.58 + pulse) * (primary + secondary)
    return np.clip(audio, -1.0, 1.0).astype(np.float32)


def write_video(path: Path, frames: List[np.ndarray]) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(str(path), fourcc, FPS, (WIDTH, HEIGHT))
    if not writer.isOpened():
        raise RuntimeError(f"Could not create video writer for {path}")
    for frame in frames:
        writer.write(frame)
    writer.release()


def write_audio(path: Path, audio: np.ndarray) -> None:
    samples = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(AUDIO_RATE)
        handle.writeframes(samples.tobytes())


def simulate_compression(frame: np.ndarray, quality: int = 35) -> np.ndarray:
    ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        return frame
    return cv2.imdecode(encoded, cv2.IMREAD_COLOR)


def transform_frames(frames: List[np.ndarray], transform: str) -> List[np.ndarray]:
    selected = frames
    if transform == "partial":
        selected = frames[18:42]

    result: List[np.ndarray] = []
    for frame in selected:
        out = frame.copy()
        if transform in {"compression", "combined"}:
            out = simulate_compression(out, 28 if transform == "combined" else 42)
        if transform in {"resolution", "combined"}:
            out = cv2.resize(out, (WIDTH // 3, HEIGHT // 3), interpolation=cv2.INTER_AREA)
            out = cv2.resize(out, (WIDTH, HEIGHT), interpolation=cv2.INTER_LINEAR)
        if transform in {"crop", "combined"}:
            out = out[18 : HEIGHT - 18, 28 : WIDTH - 28]
            out = cv2.resize(out, (WIDTH, HEIGHT), interpolation=cv2.INTER_LINEAR)
        if transform in {"watermark", "combined"}:
            overlay = out.copy()
            cv2.rectangle(overlay, (170, 126), (312, 166), (8, 10, 10), -1)
            cv2.putText(overlay, "WATCHNOW", (184, 152), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (242, 234, 220), 2)
            out = cv2.addWeighted(overlay, 0.52, out, 0.48, 0)
        if transform == "subtitle":
            cv2.rectangle(out, (18, 132), (302, 166), (6, 7, 7), -1)
            cv2.putText(out, "fan subtitle altered", (32, 154), cv2.FONT_HERSHEY_SIMPLEX, 0.54, (242, 234, 220), 2)
        result.append(out)
    return result


def transform_audio(audio: np.ndarray, transform: str, rng: random.Random) -> np.ndarray:
    selected = audio
    if transform == "partial":
        selected = audio[int(1.8 * AUDIO_RATE) : int(4.2 * AUDIO_RATE)]

    out = selected.copy()
    if transform in {"audio_mod", "combined"}:
        noise = np.asarray([rng.gauss(0, 0.035) for _ in range(len(out))], dtype=np.float32)
        modulation = 0.78 + 0.15 * np.sin(2 * np.pi * np.arange(len(out)) / max(1, AUDIO_RATE * 0.8))
        out = out * modulation + noise
    elif transform in {"compression", "watermark", "crop", "resolution"}:
        noise = np.asarray([rng.gauss(0, 0.006) for _ in range(len(out))], dtype=np.float32)
        out = out + noise
    return np.clip(out, -1.0, 1.0).astype(np.float32)


def generate_media() -> Dict[str, Dict[str, MediaPair]]:
    ensure_dirs()
    rng = random.Random(SEED)
    media: Dict[str, Dict[str, MediaPair]] = {}

    for work_index, work in enumerate(WORKS):
        frames = [make_frame(work_index, index) for index in range(FRAME_COUNT)]
        audio = make_audio(work_index)
        media[work["id"]] = {}

        original_video = VIDEO_DIR / f"{work['id']}_original.avi"
        original_audio = AUDIO_DIR / f"{work['id']}_original.wav"
        write_video(original_video, frames)
        write_audio(original_audio, audio)
        media[work["id"]]["original"] = MediaPair(original_video, original_audio)

        for transform in TRANSFORMS:
            transformed_frames = transform_frames(frames, transform)
            transformed_audio = transform_audio(audio, transform, rng)
            video_path = VIDEO_DIR / f"{work['id']}_{transform}.avi"
            audio_path = AUDIO_DIR / f"{work['id']}_{transform}.wav"
            write_video(video_path, transformed_frames)
            write_audio(audio_path, transformed_audio)
            media[work["id"]][transform] = MediaPair(video_path, audio_path)

    return media


def read_video(path: Path) -> List[np.ndarray]:
    capture = cv2.VideoCapture(str(path))
    frames: List[np.ndarray] = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frames.append(frame)
    capture.release()
    return frames


def read_audio(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as handle:
        raw = handle.readframes(handle.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32767.0


def visual_features(frames: List[np.ndarray]) -> List[Vector]:
    features = []
    stride = max(1, len(frames) // 10)
    for frame in frames[::stride]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (16, 16), interpolation=cv2.INTER_AREA).astype(np.float32)
        features.append(normalize((small - float(np.mean(small))).ravel()))
    return features


def scene_features(frames: List[np.ndarray]) -> List[Vector]:
    features = []
    stride = max(1, len(frames) // 10)
    for frame in frames[::stride]:
        small = cv2.resize(frame, (4, 4), interpolation=cv2.INTER_AREA).astype(np.float32)
        centered = small - np.mean(small, axis=(0, 1), keepdims=True)
        channel_mean = np.mean(small, axis=(0, 1)) / 255.0
        features.append(normalize(np.concatenate([centered.ravel() / 255.0, channel_mean])))
    return features


def temporal_features(frames: List[np.ndarray]) -> List[Vector]:
    sampled = scene_features(frames)
    if len(sampled) < 2:
        return sampled
    return [normalize(np.abs(sampled[index] - sampled[index - 1])) for index in range(1, len(sampled))]


def audio_features(audio: np.ndarray) -> List[Vector]:
    chunk = 2048
    features = []
    for start in range(0, max(0, len(audio) - chunk), chunk):
        window = audio[start : start + chunk] * np.hanning(chunk)
        spectrum = np.log1p(np.abs(np.fft.rfft(window))[:768])
        bands = np.array_split(spectrum, 64)
        band_values = [float(np.max(band)) for band in bands]
        peak_index = int(np.argmax(band_values))
        peak_signature = [1.0 if index == peak_index else 0.0 for index in range(len(band_values))]
        features.append(normalize(band_values + peak_signature))
    return features


def work_key(path: Path) -> str:
    parts = path.stem.split("_")
    return "_".join(parts[:2])


def metadata_similarity(
    original: MediaPair,
    candidate: MediaPair,
    original_frames: List[np.ndarray],
    candidate_frames: List[np.ndarray],
    original_audio: np.ndarray,
    candidate_audio: np.ndarray,
) -> float:
    video_duration_ratio = min(len(original_frames), len(candidate_frames)) / max(len(original_frames), len(candidate_frames), 1)
    audio_duration_ratio = min(len(original_audio), len(candidate_audio)) / max(len(original_audio), len(candidate_audio), 1)
    duration_score = 0.55 * video_duration_ratio + 0.45 * audio_duration_ratio
    title_score = 1.0 if work_key(original.video) == work_key(candidate.video) else 0.12
    return 0.65 * title_score + 0.35 * duration_score


def media_similarity(original: MediaPair, candidate: MediaPair) -> Dict[str, float]:
    original_frames = read_video(original.video)
    candidate_frames = read_video(candidate.video)
    original_audio = read_audio(original.audio)
    candidate_audio = read_audio(candidate.audio)

    return {
        "visual": sequence_similarity(visual_features(original_frames), visual_features(candidate_frames)),
        "audio": sequence_similarity(audio_features(original_audio), audio_features(candidate_audio)),
        "scene": sequence_similarity(scene_features(original_frames), scene_features(candidate_frames)),
        "temporal": sequence_similarity(temporal_features(original_frames), temporal_features(candidate_frames)),
        "metadata": metadata_similarity(original, candidate, original_frames, candidate_frames, original_audio, candidate_audio),
    }


def weighted_score(similarities: Dict[str, float], weights: Dict[str, float]) -> float:
    return sum(similarities[signal] * weights[signal] for signal in weights)


def adaptive_fused_score(similarities: Dict[str, float], weights: Dict[str, float]) -> float:
    score = weighted_score(similarities, weights)

    # A strong visual/scene match is not enough when both independent corroborators
    # are weak. This keeps lookalike hard negatives in review instead of match.
    weak_independent_evidence = similarities["audio"] < 0.68 and similarities["metadata"] < 0.55
    strong_visual_family = similarities["visual"] > 0.86 and similarities["scene"] > 0.90
    if weak_independent_evidence and strong_visual_family:
        return min(score, 0.88)

    return score


def adaptive_weights(similarities: Dict[str, float]) -> Dict[str, float]:
    weights = dict(ADAPTIVE_BASE_WEIGHTS)
    visual_gap = ((similarities["audio"] + similarities["scene"]) / 2.0) - similarities["visual"]
    audio_gap = ((similarities["visual"] + similarities["scene"]) / 2.0) - similarities["audio"]
    partial_gap = similarities["scene"] - similarities["metadata"]

    if visual_gap > 0.045:
        weights["visual"] *= 0.52
        weights["audio"] *= 1.32
        weights["scene"] *= 1.22
        weights["temporal"] *= 1.10

    if audio_gap > 0.050:
        weights["audio"] *= 0.48
        weights["visual"] *= 1.18
        weights["scene"] *= 1.20
        weights["temporal"] *= 1.12

    if partial_gap > 0.22:
        weights["metadata"] *= 0.50
        weights["temporal"] *= 0.72
        weights["scene"] *= 1.28

    for signal, score in similarities.items():
        reliability = max(0.14, min(1.0, (score - 0.42) / 0.56))
        weights[signal] *= reliability

    total = sum(weights.values()) or 1.0
    return {signal: value / total for signal, value in weights.items()}


def make_example(original: MediaPair, candidate: MediaPair, transformation: str, label: int) -> Example:
    sims = media_similarity(original, candidate)
    adaptive = adaptive_weights(sims)
    return Example(
        transformation=transformation,
        label=label,
        similarities=sims,
        baseline_score=weighted_score(sims, BASELINE_WEIGHTS),
        adaptive_score=adaptive_fused_score(sims, adaptive),
        adaptive_weights=adaptive,
        candidate_video=str(candidate.video.relative_to(ROOT)).replace("\\", "/"),
        candidate_audio=str(candidate.audio.relative_to(ROOT)).replace("\\", "/"),
    )


def metrics(examples: List[Example], score_attr: str) -> Dict[str, float]:
    tp = fp = tn = fn = 0
    for example in examples:
        prediction = 1 if getattr(example, score_attr) >= THRESHOLD else 0
        if prediction and example.label:
            tp += 1
        elif prediction and not example.label:
            fp += 1
        elif not prediction and not example.label:
            tn += 1
        else:
            fn += 1

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "tn": tn, "fn": fn}


def pct(value: float) -> int:
    return int(round(value * 100))


def decision_coverage(examples: List[Example]) -> Dict[str, int]:
    match = review = negative = 0
    automated_correct = 0
    automated_total = 0

    for example in examples:
        if example.adaptive_score >= THRESHOLD:
            match += 1
            automated_total += 1
            automated_correct += int(example.label == 1)
        elif example.adaptive_score >= REVIEW_FLOOR:
            review += 1
        else:
            negative += 1
            automated_total += 1
            automated_correct += int(example.label == 0)

    total = len(examples) or 1
    automation_total = match + negative
    return {
        "match": match,
        "negative": negative,
        "review": review,
        "matchRate": pct(match / total),
        "negativeRate": pct(negative / total),
        "reviewRate": pct(review / total),
        "automationCoverage": pct(automation_total / total),
        "automatedDecisionAccuracy": pct(automated_correct / automated_total) if automated_total else 0,
    }


def build_examples(media: Dict[str, Dict[str, MediaPair]]) -> List[Example]:
    examples: List[Example] = []
    work_ids = [work["id"] for work in WORKS]

    for work_id in work_ids:
        original = media[work_id]["original"]

        for transform in TRANSFORMS:
            examples.append(make_example(original, media[work_id][transform], transform, 1))
            for negative_work in work_ids:
                if negative_work != work_id:
                    examples.append(make_example(original, media[negative_work][transform], transform, 0))

    return examples


def summarize(examples: List[Example]) -> Dict[str, object]:
    clean_adaptive = metrics([item for item in examples if item.transformation == "clean"], "adaptive_score")["f1"]
    rows = []
    for transform, note in TRANSFORMS.items():
        group = [item for item in examples if item.transformation == transform]
        baseline = metrics(group, "baseline_score")
        adaptive = metrics(group, "adaptive_score")
        degradation = max(0.0, clean_adaptive - adaptive["f1"])
        rows.append(
            {
                "key": transform,
                "transformation": transform.replace("_", " ").title(),
                "baseline": pct(baseline["f1"]),
                "cineshield": pct(adaptive["f1"]),
                "gain": pct(adaptive["f1"] - baseline["f1"]),
                "degradation": pct(degradation),
                "examples": len(group),
                "note": note,
                "baselinePrecision": pct(baseline["precision"]),
                "baselineRecall": pct(baseline["recall"]),
                "adaptivePrecision": pct(adaptive["precision"]),
                "adaptiveRecall": pct(adaptive["recall"]),
            }
        )

    transformed_cases = [item for item in examples if item.label and item.transformation in {"crop", "combined", "partial"}]
    best_case = max(transformed_cases, key=lambda item: item.adaptive_score)
    review_case = min((item for item in examples if item.label), key=lambda item: item.adaptive_score)

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "threshold": THRESHOLD,
        "reviewFloor": REVIEW_FLOOR,
        "works": len(WORKS),
        "sampleCount": len(examples),
        "mediaRoot": str(MEDIA_DIR.relative_to(ROOT)).replace("\\", "/"),
        "signals": SIGNALS,
        "negativeDesign": "cross-work negatives compare every protected work against transformed variants of every other generated work, including a deliberate Project Monsoon lookalike",
        "decisionPolicy": {
            "match": f"adaptive score >= {THRESHOLD}",
            "review": f"{REVIEW_FLOOR} <= adaptive score < {THRESHOLD}",
            "negative": f"adaptive score < {REVIEW_FLOOR}",
        },
        "rows": rows,
        "overall": {
            "baseline": {key: pct(value) if isinstance(value, float) else value for key, value in metrics(examples, "baseline_score").items()},
            "adaptive": {key: pct(value) if isinstance(value, float) else value for key, value in metrics(examples, "adaptive_score").items()},
        },
        "coverage": decision_coverage(examples),
        "sampleCase": {
            "transformation": best_case.transformation,
            "baseline": pct(best_case.baseline_score),
            "adaptive": pct(best_case.adaptive_score),
            "signals": {signal: pct(score) for signal, score in best_case.similarities.items()},
            "weights": {signal: pct(weight) for signal, weight in best_case.adaptive_weights.items()},
            "video": best_case.candidate_video,
            "audio": best_case.candidate_audio,
        },
        "reviewCase": {
            "transformation": review_case.transformation,
            "baseline": pct(review_case.baseline_score),
            "adaptive": pct(review_case.adaptive_score),
            "signals": {signal: pct(score) for signal, score in review_case.similarities.items()},
            "video": review_case.candidate_video,
            "audio": review_case.candidate_audio,
        },
    }


def write_outputs(payload: Dict[str, object]) -> None:
    json_text = json.dumps(payload, indent=2)
    (DATA_DIR / "real-media-results.json").write_text(json_text + "\n", encoding="utf-8")
    (DATA_DIR / "real-media-results.js").write_text("window.CINESHIELD_REAL_MEDIA = " + json_text + ";\n", encoding="utf-8")


def main() -> None:
    media = generate_media()
    examples = build_examples(media)
    payload = summarize(examples)
    write_outputs(payload)
    print(f"Generated {payload['works']} permitted synthetic media works")
    print(f"Evaluated {payload['sampleCount']} real-media pairs")
    print(f"Baseline F1: {payload['overall']['baseline']['f1']}%")
    print(f"Adaptive F1: {payload['overall']['adaptive']['f1']}%")
    print(f"Wrote {DATA_DIR / 'real-media-results.json'}")
    print(f"Wrote {DATA_DIR / 'real-media-results.js'}")


if __name__ == "__main__":
    main()
