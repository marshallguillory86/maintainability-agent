from __future__ import annotations

from typing import Any


CATEGORIES = ["modularity", "reusability", "analyzability", "modifiability", "testability"]


def clamp_score(value: float) -> float:
    return round(max(0.0, min(5.0, value)), 1)


def grade_from_score(score: float) -> str:
    if score >= 4.8:
        return "A+"
    if score >= 4.5:
        return "A"
    if score >= 4.0:
        return "B"
    if score >= 3.0:
        return "C"
    if score >= 2.0:
        return "D"
    return "F"


def score_report(report: dict[str, Any]) -> dict[str, Any]:
    summary = report["summary"]
    gates = summary["hard_gate_failures"]
    file_pressure = summary["file_failures"] * 1.0 + summary["file_warnings"] * 0.35
    function_pressure = summary["function_failures"] * 1.0 + summary["function_warnings"] * 0.4
    duplicate_pressure = min(summary["duplicate_blocks"], 20) * 0.08
    risk_pressure = min(summary["risk_findings"], 20) * 0.12

    categories = {
        "modularity": clamp_score(5.0 - file_pressure - function_pressure * 0.5 - duplicate_pressure),
        "reusability": clamp_score(5.0 - duplicate_pressure * 1.5 - file_pressure * 0.3),
        "analyzability": clamp_score(5.0 - file_pressure * 0.6 - function_pressure * 0.6 - risk_pressure),
        "modifiability": clamp_score(5.0 - gates * 0.8 - file_pressure * 0.4 - duplicate_pressure - risk_pressure),
        "testability": clamp_score(5.0 - gates * 0.6 - function_pressure * 0.5 - risk_pressure),
    }
    overall = clamp_score(sum(categories.values()) / len(categories))
    return {
        "standard": "ISO/IEC 25010 maintainability-inspired 0-5 scale",
        "overall": overall,
        "grade": grade_from_score(overall),
        "categories": categories,
    }
