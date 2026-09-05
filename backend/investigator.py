from __future__ import annotations

from statistics import mean
from typing import Dict, Iterable, List, Mapping


ScanResult = Mapping[str, object]


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _signals(result: ScanResult) -> Dict[str, float]:
    raw = result.get("signals")
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): _as_float(value) for key, value in raw.items()}


def _decision(result: ScanResult) -> str:
    decision = str(result.get("decision") or "Review")
    return decision if decision in {"Match", "Review", "No match"} else "Review"


def _strongest_signals(result: ScanResult, count: int = 2) -> List[str]:
    signals = _signals(result)
    return [name for name, _ in sorted(signals.items(), key=lambda item: item[1], reverse=True)[:count]]


def _weakest_signals(result: ScanResult, count: int = 2) -> List[str]:
    signals = _signals(result)
    return [name for name, _ in sorted(signals.items(), key=lambda item: item[1])[:count]]


def explain_candidate(result: ScanResult) -> Dict[str, object]:
    decision = _decision(result)
    confidence = _as_float(result.get("confidence"))
    strongest = _strongest_signals(result)
    weakest = _weakest_signals(result)
    name = str(result.get("fileName") or "candidate")

    if decision == "Match":
        summary = (
            f"{name} crossed the high-confidence threshold at {confidence:.1f}%. "
            f"The strongest evidence comes from {', '.join(strongest) or 'the available signals'}."
        )
        boundary = "Prepare a case package, but require authorized human review before any external action."
        priority = "Critical" if confidence >= 94 else "High"
    elif decision == "Review":
        summary = (
            f"{name} has meaningful similarity at {confidence:.1f}%, but the evidence is not strong enough "
            "for automatic match handling."
        )
        boundary = f"Keep in review because {', '.join(weakest) or 'one or more signals'} is weak or incomplete."
        priority = "Review"
    else:
        summary = (
            f"{name} is below the same-content threshold at {confidence:.1f}%. "
            "The system should preserve the record without escalating it as a suspected copy."
        )
        boundary = "Reject for now, unless new source evidence or a stronger candidate appears."
        priority = "Low"

    return {
        "summary": summary,
        "recommendedPriority": priority,
        "failureBoundary": boundary,
        "strongestSignals": strongest,
        "weakestSignals": weakest,
    }


def _decision_counts(results: Iterable[ScanResult]) -> Dict[str, int]:
    counts = {"Match": 0, "Review": 0, "No match": 0}
    for result in results:
        counts[_decision(result)] += 1
    return counts


def build_investigation(results: List[ScanResult]) -> Dict[str, object]:
    if not results:
        return {
            "summary": "No candidate media was scanned.",
            "recommendedPriority": "Idle",
            "failureBoundary": "Upload candidate media before creating an evidence case.",
            "decisionCounts": {"Match": 0, "Review": 0, "No match": 0},
            "auditTrail": [],
            "candidateAnalyses": [],
        }

    ranked = sorted(results, key=lambda item: _as_float(item.get("confidence")), reverse=True)
    top = ranked[0]
    analyses = [dict(result, analysis=explain_candidate(result)) for result in ranked]
    counts = _decision_counts(ranked)
    confidences = [_as_float(result.get("confidence")) for result in ranked]
    top_analysis = explain_candidate(top)
    strongest = top_analysis["strongestSignals"]

    if counts["Match"]:
        summary = (
            f"CineShield scanned {len(ranked)} candidate file(s) and found {counts['Match']} high-confidence "
            f"suspected match(es). The top case is {top.get('fileName')} at {_as_float(top.get('confidence')):.1f}%."
        )
    elif counts["Review"]:
        summary = (
            f"CineShield scanned {len(ranked)} candidate file(s). No automatic match was created; "
            f"{counts['Review']} candidate(s) were routed to human review."
        )
    else:
        summary = (
            f"CineShield scanned {len(ranked)} candidate file(s) and rejected all candidates below the "
            "same-content threshold."
        )

    return {
        "summary": summary,
        "recommendedPriority": top_analysis["recommendedPriority"],
        "failureBoundary": top_analysis["failureBoundary"],
        "topCandidate": top.get("fileName"),
        "topConfidence": round(_as_float(top.get("confidence")), 1),
        "averageConfidence": round(mean(confidences), 1),
        "decisionCounts": counts,
        "strongestSignals": strongest,
        "auditTrail": [
            "Registered protected video",
            "Extracted Content DNA from protected media",
            "Processed uploaded candidate corpus",
            "Computed visual, scene, temporal, duration, and coverage signals",
            "Applied adaptive evidence fusion and review thresholds",
            "Prepared investigator summary for human authorization",
        ],
        "sourceBoundary": (
            "This investigation uses uploaded local candidate media only. Internet-wide discovery should be "
            "added through lawful connectors such as rights-holder URL queues, search APIs, and partner feeds."
        ),
        "candidateAnalyses": analyses,
    }
