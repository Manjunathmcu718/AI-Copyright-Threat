from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SEED = 7429
THRESHOLD = 0.78
REVIEW_FLOOR = 0.72
CALIBRATION_WORKS = 4
TEST_WORKS = 6
POSITIVE_VARIANTS_PER_TRANSFORMATION = 5
NEGATIVE_VARIANTS_PER_TRANSFORMATION = 5

SIGNALS = {
    "visual": 96,
    "audio": 64,
    "scene": 48,
    "temporal": 28,
    "text": 32,
    "metadata": 16,
}

BASELINE_WEIGHTS = {
    "visual": 0.44,
    "audio": 0.22,
    "scene": 0.16,
    "temporal": 0.08,
    "text": 0.05,
    "metadata": 0.05,
}

ADAPTIVE_BASE_WEIGHTS = {
    "visual": 0.30,
    "audio": 0.24,
    "scene": 0.22,
    "temporal": 0.10,
    "text": 0.08,
    "metadata": 0.06,
}

TRANSFORMATIONS = {
    "clean": {
        "display": "Clean copy",
        "noise": {"visual": 0.02, "audio": 0.02, "scene": 0.02, "temporal": 0.02, "text": 0.02, "metadata": 0.02},
        "note": "Original-quality near duplicate",
    },
    "compression": {
        "display": "Compression",
        "noise": {"visual": 0.12, "audio": 0.05, "scene": 0.08, "temporal": 0.03, "text": 0.07, "metadata": 0.05},
        "note": "Scene and audio evidence stay stable",
    },
    "resolution": {
        "display": "Resolution change",
        "noise": {"visual": 0.15, "audio": 0.04, "scene": 0.08, "temporal": 0.03, "text": 0.05, "metadata": 0.05},
        "note": "Visual embeddings normalize downscale",
    },
    "crop": {
        "display": "Cropping",
        "noise": {"visual": 0.34, "audio": 0.05, "scene": 0.13, "temporal": 0.05, "text": 0.19, "metadata": 0.07},
        "note": "Visual discounted, audio and scene evidence raised",
    },
    "watermark": {
        "display": "Watermark",
        "noise": {"visual": 0.29, "audio": 0.05, "scene": 0.09, "temporal": 0.04, "text": 0.12, "metadata": 0.07},
        "note": "Overlay weakens visual-only matching",
    },
    "audio_mod": {
        "display": "Audio modification",
        "noise": {"visual": 0.08, "audio": 0.34, "scene": 0.08, "temporal": 0.06, "text": 0.06, "metadata": 0.05},
        "note": "Visual, scene, and temporal evidence compensate",
    },
    "subtitle": {
        "display": "Subtitle edit",
        "noise": {"visual": 0.07, "audio": 0.05, "scene": 0.05, "temporal": 0.04, "text": 0.32, "metadata": 0.08},
        "note": "Text signal is bounded when subtitles diverge",
    },
    "partial": {
        "display": "Partial clip",
        "noise": {"visual": 0.26, "audio": 0.20, "scene": 0.20, "temporal": 0.30, "text": 0.22, "metadata": 0.18},
        "note": "Confidence stays review-gated under short coverage",
    },
    "combined": {
        "display": "Combined transformations",
        "noise": {"visual": 0.38, "audio": 0.18, "scene": 0.22, "temporal": 0.15, "text": 0.28, "metadata": 0.13},
        "note": "Adaptive fusion reduces multi-transform degradation",
    },
}


Vector = List[float]
DNA = Dict[str, Vector]


@dataclass
class Example:
    work_id: str
    split: str
    transformation: str
    label: int
    similarities: Dict[str, float]
    baseline_score: float
    adaptive_score: float
    adaptive_weights: Dict[str, float]


def normalize(vector: Iterable[float]) -> Vector:
    values = list(vector)
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


def random_vector(rng: random.Random, size: int) -> Vector:
    return normalize(rng.gauss(0, 1) for _ in range(size))


def jitter(vector: Vector, noise: float, rng: random.Random) -> Vector:
    return normalize(value + rng.gauss(0, noise) for value in vector)


def blend_with_anchor(vector: Vector, strength: float, noise: float, rng: random.Random) -> Vector:
    unrelated = random_vector(rng, len(vector))
    return normalize(
        strength * original + (1.0 - strength) * other + rng.gauss(0, noise)
        for original, other in zip(vector, unrelated)
    )


def cosine(left: Vector, right: Vector) -> float:
    raw = sum(a * b for a, b in zip(left, right))
    return max(0.0, min(1.0, (raw + 1.0) / 2.0))


def make_work(rng: random.Random) -> DNA:
    return {signal: random_vector(rng, size) for signal, size in SIGNALS.items()}


def make_positive(work: DNA, transformation: str, rng: random.Random) -> DNA:
    noise = TRANSFORMATIONS[transformation]["noise"]
    return {signal: jitter(vector, noise[signal], rng) for signal, vector in work.items()}


def make_negative(work: DNA, transformation: str, rng: random.Random) -> DNA:
    negative = {signal: random_vector(rng, size) for signal, size in SIGNALS.items()}

    # Hard negatives mimic title/metadata or a few surface-level similarities.
    hard_negative_profiles = {
        "clean": {"metadata": 0.62},
        "compression": {"metadata": 0.68, "text": 0.52, "visual": 0.28},
        "resolution": {"metadata": 0.64, "visual": 0.42},
        "crop": {"visual": 0.50, "metadata": 0.48},
        "watermark": {"visual": 0.50, "text": 0.48},
        "audio_mod": {"audio": 0.50, "metadata": 0.48},
        "subtitle": {"text": 0.62, "metadata": 0.62},
        "partial": {"scene": 0.46, "audio": 0.42},
        "combined": {"visual": 0.50, "audio": 0.42, "text": 0.42},
    }

    for signal, strength in hard_negative_profiles[transformation].items():
        negative[signal] = blend_with_anchor(work[signal], strength, 0.09, rng)

    return negative


def similarities(work: DNA, candidate: DNA) -> Dict[str, float]:
    return {signal: cosine(work[signal], candidate[signal]) for signal in SIGNALS}


def weighted_score(sims: Dict[str, float], weights: Dict[str, float]) -> float:
    return sum(sims[signal] * weights[signal] for signal in weights)


def adaptive_weights(sims: Dict[str, float]) -> Dict[str, float]:
    weights = dict(ADAPTIVE_BASE_WEIGHTS)

    visual_gap = ((sims["audio"] + sims["scene"]) / 2.0) - sims["visual"]
    audio_gap = ((sims["visual"] + sims["scene"]) / 2.0) - sims["audio"]
    text_gap = ((sims["visual"] + sims["audio"] + sims["scene"]) / 3.0) - sims["text"]
    partial_gap = sims["scene"] - sims["temporal"]

    if visual_gap > 0.055:
        weights["visual"] *= 0.48
        weights["audio"] *= 1.34
        weights["scene"] *= 1.28
        weights["temporal"] *= 1.10

    if audio_gap > 0.055:
        weights["audio"] *= 0.46
        weights["visual"] *= 1.18
        weights["scene"] *= 1.24
        weights["temporal"] *= 1.10

    if text_gap > 0.075:
        weights["text"] *= 0.42
        weights["metadata"] *= 0.82

    if partial_gap > 0.09:
        weights["temporal"] *= 0.58
        weights["metadata"] *= 0.72
        weights["scene"] *= 1.35
        weights["audio"] *= 1.12

    # Reliability gating prevents a random high signal from dominating negatives.
    for signal, score in sims.items():
        reliability = max(0.12, min(1.0, (score - 0.46) / 0.52))
        weights[signal] *= reliability

    total = sum(weights.values()) or 1.0
    return {signal: value / total for signal, value in weights.items()}


def make_example(work_id: str, split: str, work: DNA, transformation: str, label: int, rng: random.Random) -> Example:
    candidate = make_positive(work, transformation, rng) if label else make_negative(work, transformation, rng)
    sims = similarities(work, candidate)
    adaptive = adaptive_weights(sims)
    return Example(
        work_id=work_id,
        split=split,
        transformation=transformation,
        label=label,
        similarities=sims,
        baseline_score=weighted_score(sims, BASELINE_WEIGHTS),
        adaptive_score=weighted_score(sims, adaptive),
        adaptive_weights=adaptive,
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


def build_split(split: str, count: int, rng: random.Random) -> List[Example]:
    examples: List[Example] = []

    for work_index in range(count):
        work_id = f"{split.upper()}-{work_index + 1:02d}"
        work = make_work(rng)
        for transformation in TRANSFORMATIONS:
            for _ in range(POSITIVE_VARIANTS_PER_TRANSFORMATION):
                examples.append(make_example(work_id, split, work, transformation, 1, rng))
            for _ in range(NEGATIVE_VARIANTS_PER_TRANSFORMATION):
                examples.append(make_example(work_id, split, work, transformation, 0, rng))

    return examples


def build_dataset() -> Dict[str, List[Example]]:
    rng = random.Random(SEED)
    return {
        "calibration": build_split("calibration", CALIBRATION_WORKS, rng),
        "test": build_split("test", TEST_WORKS, rng),
    }


def summarize(splits: Dict[str, List[Example]]) -> Dict[str, object]:
    test_examples = splits["test"]
    calibration_examples = splits["calibration"]
    clean_examples = [item for item in test_examples if item.transformation == "clean"]
    clean_baseline = metrics(clean_examples, "baseline_score")["f1"]
    clean_adaptive = metrics(clean_examples, "adaptive_score")["f1"]

    rows = []
    for key, config in TRANSFORMATIONS.items():
        group = [item for item in test_examples if item.transformation == key]
        baseline = metrics(group, "baseline_score")
        adaptive = metrics(group, "adaptive_score")
        reference = clean_adaptive if key != "clean" else clean_baseline
        degradation = max(0, reference - adaptive["f1"])
        rows.append(
            {
                "key": key,
                "transformation": config["display"],
                "baseline": pct(baseline["f1"]),
                "cineshield": pct(adaptive["f1"]),
                "gain": pct(adaptive["f1"] - baseline["f1"]),
                "degradation": pct(degradation),
                "note": config["note"],
                "baselinePrecision": pct(baseline["precision"]),
                "baselineRecall": pct(baseline["recall"]),
                "adaptivePrecision": pct(adaptive["precision"]),
                "adaptiveRecall": pct(adaptive["recall"]),
            }
        )

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "threshold": THRESHOLD,
        "reviewFloor": REVIEW_FLOOR,
        "sampleCount": len(test_examples),
        "totalGeneratedExamples": len(calibration_examples) + len(test_examples),
        "split": {
            "type": "content-level",
            "calibrationWorks": CALIBRATION_WORKS,
            "testWorks": TEST_WORKS,
            "calibrationExamples": len(calibration_examples),
            "testExamples": len(test_examples),
            "positiveVariantsPerTransformationPerWork": POSITIVE_VARIANTS_PER_TRANSFORMATION,
            "negativeVariantsPerTransformationPerWork": NEGATIVE_VARIANTS_PER_TRANSFORMATION,
            "evaluatedOn": "held-out test works only",
        },
        "systems": {
            "baseline": "fixed visual-heavy evidence weights",
            "adaptive": "transformation-aware evidence reliability and normalized fusion weights",
        },
        "negativeDesign": "hard negatives share selected surface-level signals such as metadata, text, visual, audio, or scene similarity",
        "decisionPolicy": {
            "match": f"adaptive score >= {THRESHOLD}",
            "review": f"{REVIEW_FLOOR} <= adaptive score < {THRESHOLD}",
            "negative": f"adaptive score < {REVIEW_FLOOR}",
        },
        "rows": rows,
        "overall": {
            "baseline": {key: pct(value) if isinstance(value, float) else value for key, value in metrics(test_examples, "baseline_score").items()},
            "adaptive": {key: pct(value) if isinstance(value, float) else value for key, value in metrics(test_examples, "adaptive_score").items()},
        },
        "coverage": decision_coverage(test_examples),
    }


def write_outputs(payload: Dict[str, object]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    json_path = DATA_DIR / "benchmark-results.json"
    js_path = DATA_DIR / "benchmark-results.js"

    json_text = json.dumps(payload, indent=2)
    json_path.write_text(json_text + "\n", encoding="utf-8")
    js_path.write_text("window.CINESHIELD_BENCHMARK = " + json_text + ";\n", encoding="utf-8")


def main() -> None:
    splits = build_dataset()
    payload = summarize(splits)
    write_outputs(payload)
    adaptive = payload["overall"]["adaptive"]
    baseline = payload["overall"]["baseline"]
    print(f"Generated {payload['sampleCount']} benchmark examples")
    print(f"Baseline F1: {baseline['f1']}%")
    print(f"Adaptive F1: {adaptive['f1']}%")
    print(f"Wrote {DATA_DIR / 'benchmark-results.json'}")
    print(f"Wrote {DATA_DIR / 'benchmark-results.js'}")


if __name__ == "__main__":
    main()
