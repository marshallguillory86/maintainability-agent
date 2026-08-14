"""The estimate uses analyzer readings. Operator text may not say otherwise.

After 3.5/3.6 the production mix is ``scoring._primary_pressures``:
analyzer where the full concept set exists, built-in fallback otherwise.
A hostile audit found the same stale sentence in the Markdown report,
CLI ``--help``, ``build_report``'s docstring, the README, docs/README,
and architecture — the prompt had been patched; the report had not.

This file is the class lint. Re-introducing "analyzers do not move the
estimate" on any surface a user reads must fail the build, not wait for
the next audit. The gate lifts itself if ``_primary_pressures`` leaves
scoring, because those sentences would then be true again.
"""
from __future__ import annotations

import re
from pathlib import Path

from maintainability_audit._scan_view import analyzer_measurements_markdown

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "maintainability_audit"

# Present-tense claims that the current mix makes false. Historical
# changelog notes about 0.5/0.6 signals are not in LIVE_SURFACES.
_STALE = (
    (re.compile(r"do not (?:yet )?move the point estimate", re.I),
     "analyzers move the estimate where the concept set is complete"),
    (re.compile(r"do not (?:yet )?drive the point estimate", re.I),
     "a complete analyzer concept set is the primary evidence"),
    (re.compile(r"not yet scored", re.I),
     "complete measurements are scored; say so"),
    (re.compile(r"still derives from the built-in", re.I),
     "the estimate is analyzer-primary"),
    (re.compile(r"neither path feeds the point estimate", re.I),
     "a metric adapter that completes a concept set feeds the estimate"),
    (re.compile(r"reported but do not yet move", re.I),
     "measurements move the estimate when the concept set is complete"),
    (re.compile(r"calibration constant still derived against", re.I),
     "3.6 re-derived C against the analyzer-primary mix"),
    (re.compile(r"re-deriving the constant against this one is outstanding", re.I),
     "3.6 landed"),
    (re.compile(r"outstanding recalibration", re.I),
     "3.6 landed"),
    (re.compile(r"recalibration \(3\.5", re.I),
     "3.5–3.6 are not next work"),
)

LIVE_SURFACES = (
    ROOT / "README.md",
    ROOT / "docs" / "README.md",
    ROOT / "docs" / "architecture.md",
    ROOT / "docs" / "decisions.md",
    ROOT / "docs" / "cli.md",
    ROOT / "docs" / "release-plan.md",
    PACKAGE / "cli.py",
    PACKAGE / "report.py",
    PACKAGE / "_scan_view.py",
)


def _analyzer_primary_is_the_mix() -> bool:
    scoring = (PACKAGE / "scoring.py").read_text(encoding="utf-8")
    return "def _primary_pressures(" in scoring


def test_the_production_mix_is_analyzer_primary() -> None:
    """The lint is about this function. If it is gone, the class closed."""
    assert _analyzer_primary_is_the_mix(), (
        "scoring._primary_pressures is the analyzer-primary mix; "
        "this file's other tests assume it exists"
    )


def test_live_surfaces_do_not_claim_analyzers_leave_the_estimate_alone() -> None:
    """The class: one stale sentence, every place a user can still read it."""
    if not _analyzer_primary_is_the_mix():
        return

    offenders: list[str] = []
    for path in LIVE_SURFACES:
        text = path.read_text(encoding="utf-8")
        for pattern, reason in _STALE:
            match = pattern.search(text)
            if match:
                offenders.append(
                    f"{path.relative_to(ROOT)}: {reason!r} — matched {match.group(0)!r}"
                )

    unreleased = _changelog_unreleased()
    for pattern, reason in _STALE:
        match = pattern.search(unreleased)
        if match:
            offenders.append(
                f"CHANGELOG.md Unreleased: {reason!r} — matched {match.group(0)!r}"
            )

    assert not offenders, (
        "operator-facing text still says analyzers do not move the estimate "
        "while scoring._primary_pressures is the production mix:\n"
        + "\n".join(offenders)
    )


def test_scored_measurements_name_the_estimate_source() -> None:
    """The Markdown report is what a human reads. It must not invert the mix."""
    text = "\n".join(analyzer_measurements_markdown(_one_measurement(), ["declarations"]))
    lowered = text.lower()

    assert "not yet scored" not in lowered
    assert "still derives from the built-in" not in lowered
    assert "declarations" in lowered
    assert "estimate" in lowered
    assert any(word in lowered for word in ("uses", "used", "primary"))


def test_unscored_measurements_name_the_fallback_without_the_stale_sentence() -> None:
    """Lizard-only / findings-only output really is fallback. Say that, not 'not yet'."""
    text = "\n".join(analyzer_measurements_markdown(_one_measurement(), []))
    lowered = text.lower()

    assert "not yet scored" not in lowered
    assert "re-deriving the calibration" not in lowered
    assert "built-in" in lowered


def test_changelog_unreleased_records_the_estimate_swap() -> None:
    """A scoring-behavior change with an empty Unreleased section is the same lie."""
    text = _changelog_unreleased()
    assert text.strip(), "CHANGELOG Unreleased is empty after the estimate swap"
    lowered = text.lower()
    assert "2.2658" in text or "analyzer-primary" in lowered or "point estimate" in lowered


def _changelog_unreleased() -> str:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    _, rest = text.split("## Unreleased", maxsplit=1)
    next_heading = re.search(r"^## ", rest, re.M)
    return rest if next_heading is None else rest[: next_heading.start()]


def _one_measurement() -> dict:
    return {
        "cyclomatic_complexity": {
            "units": 40,
            "tools": ["lizard"],
            "tool_disagreement": None,
            "distribution": {},
        }
    }
