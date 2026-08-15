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
    """The class: one stale sentence, every place a user can still read it.

    P8: the estimate's source has to be attributable, and a document
    still saying the analyzers leave the number alone attributes it to
    the wrong tier.
    """
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
    """The Markdown report is what a human reads. It must not invert the mix.

    P8: a reported value needs an attributable source, so where the
    analyzers supplied the number the report says so rather than leaving
    the reader to assume the built-in tier produced it.
    """
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


def test_the_default_report_names_the_built_in_tier_as_the_estimate_source(
    tmp_path: Path,
) -> None:
    """P8 on the path almost every reader takes: no `--analyzers`.

    A reported value with no attributable source is the published
    falsifier, and the default Markdown report is exactly that today.
    `summary_table` prints the estimate, the range and the grade; the
    coverage section that would name the built-in tier is omitted
    entirely because `analyzer_coverage` is None when the pool did not
    run, and the estimate-source caveat in `_scan_view` only renders
    beside analyzer measurements.

    So the one report a zero-install user actually reads states a number
    and never says what produced it. Where analyzers *do* run the source
    is named — which makes the default path the gap, not the design.
    """
    import subprocess

    from maintainability_audit.config import load_config
    from maintainability_audit.renderers import render_markdown
    from maintainability_audit.report import build_report

    root = tmp_path / "default"
    root.mkdir()
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    for index in range(40):
        (root / f"m{index}.py").write_text(
            "\n".join(f"def f{index}_{j}(v):\n    return v + {j}\n" for j in range(4)),
            encoding="utf-8",
        )
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "start"],
        check=True,
    )

    report = build_report(root, load_config(None))
    assert report["analyzer_coverage"] is None, "this fixture must be the no-analyzers path"
    assert report["score"]["maintainability_estimate"] is not None, (
        "the fixture must produce a number, or there is no source to attribute"
    )

    markdown = render_markdown(report)
    lowered = markdown.lower()

    assert any(
        phrase in lowered
        for phrase in ("built-in detector", "built-in tier", "built-in detectors")
    ), (
        "the default report states an estimate and never says what produced it; "
        "P8's falsifier is a reported value with no attributable source"
    )
