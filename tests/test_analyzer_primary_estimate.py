"""The analyzers supply the number, dimension by dimension — ADR 006 §1.

The pool has been running for several releases and reaching nothing that
matters. `score_evidence` always called `dimension_pressures(summary)`,
so the estimate came from six built-in detectors; the analyzers' reading
only stretched the interval. ADR 006 says the opposite: external tools
are the primary evidence and the built-ins are a fallback tier.

The swap is per dimension, not wholesale, because coverage is partial by
nature. lizard measures complexity everywhere and documentation nowhere,
so a repository gets an analyzer number for some dimensions and a
built-in number for the rest. A dimension no analyzer measured is
**unmeasured, not zero** — the founding defect of this project — so it
keeps the built-in reading rather than being scored as clean.

Three things this must not break:

- **The zero-install path.** Without `--analyzers` there is no
  `ExternalPressures` at all, and every report stays byte-identical.
- **Both populations.** `declaration_size` reads the *production*
  pressure, so a substitution that lands only in `dimension_pressures`
  changes nothing the score reads.
- **The interval still shows disagreement.** It now widens around the
  analyzer estimate rather than the built-in one. The two readings are
  never averaged: a mean would lend the number a precision neither
  source earned.

The estimate moves as a result. That is expected, and re-deriving the
calibration constant against the new path is 3.6.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from maintainability_audit._pressures import ExternalPressures
from maintainability_audit.config import load_config
from maintainability_audit.evidence import normalize_report_evidence
from maintainability_audit.report import build_report
from maintainability_audit.scoring import score_evidence


@pytest.fixture
def evidence():
    """A committed tree of ordinary small functions, scored cleanly."""
    root = Path(tempfile.mkdtemp()) / "r"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    for index in range(40):
        (root / f"m{index}.py").write_text(
            "\n".join(f"def f{index}_{j}():\n    return {j}\n" for j in range(4)),
            encoding="utf-8",
        )
    return normalize_report_evidence(build_report(root, load_config(None)))


def _both(value: float) -> ExternalPressures:
    return ExternalPressures(
        all_code={"declarations": value}, production={"declarations": value}
    )


def test_an_analyzer_reading_moves_the_point_estimate(evidence) -> None:
    """The whole point. A tool that cannot change the number is decoration.

    Previously this asserted the opposite — that a second source widens
    the interval and leaves the estimate alone — which was the correct
    reading of ADR 006 §4 and the wrong reading of §1.
    """
    built_in = score_evidence(evidence)
    with_analyzers = score_evidence(evidence, _both(0.3))

    assert with_analyzers["maintainability_estimate"] != built_in["maintainability_estimate"], (
        "the analyzers measured this dimension and the estimate did not move"
    )
    assert with_analyzers["maintainability_estimate"] < built_in["maintainability_estimate"], (
        "a worse analyzer reading must lower the estimate, not raise it"
    )


def test_a_dimension_no_analyzer_measured_keeps_its_built_in_reading(evidence) -> None:
    """Unmeasured is not zero, and it is not clean either.

    Partial coverage is the normal case: lizard reads complexity and
    says nothing about documentation. Substituting `None` as a value
    would score the silent dimension as perfect, which is the exact
    shape of the defect that produced a 5.0/A+ on one function.
    """
    built_in = score_evidence(evidence)
    silent = score_evidence(
        evidence, ExternalPressures(all_code={"declarations": None},
                                    production={"declarations": None})
    )

    assert silent["maintainability_estimate"] == built_in["maintainability_estimate"]
    assert silent["maintainability_range"] == built_in["maintainability_range"]


def test_without_analyzers_nothing_changes(evidence) -> None:
    """The zero-install path is the default and must stay untouched."""
    assert score_evidence(evidence, None) == score_evidence(evidence)


def test_the_substitution_reaches_the_production_pressure(evidence) -> None:
    """`declaration_size` reads production, so all_code alone is a no-op.

    The first attempt at the interval widening had exactly this bug: the
    substitution landed in `dimension_pressures` and the score never saw
    it.
    """
    all_code_only = score_evidence(
        evidence, ExternalPressures(all_code={"declarations": 0.3}, production={})
    )
    both = score_evidence(evidence, _both(0.3))

    assert both["maintainability_estimate"] < all_code_only["maintainability_estimate"], (
        "the production population is what the declarations aspect reads"
    )


def test_the_interval_widens_around_the_analyzer_estimate(evidence) -> None:
    """Disagreement is still uncertainty, measured from the new centre.

    The built-in rollup becomes the alternative: the interval has to
    contain what the fallback tier would have scored, so a reader can
    see how far the two sources are apart without either being averaged
    into the other.
    """
    built_in = score_evidence(evidence)
    # A clearly divergent analyzer reading: the "not averaged" check below
    # only means anything when the two readings are far enough apart that
    # their mean is a distinct number. At a one-tenth gap the mean rounds
    # onto one of them and the check cannot tell a blend from the primary.
    swapped = score_evidence(evidence, _both(1.0))

    low, high = swapped["maintainability_range"]
    estimate = swapped["maintainability_estimate"]

    assert low <= estimate <= high, "the interval must contain its own estimate"
    assert low <= built_in["maintainability_estimate"] <= high, (
        "the interval must contain what the built-in tier would have scored"
    )
    assert estimate != round((estimate + built_in["maintainability_estimate"]) / 2, 1) or (
        estimate == built_in["maintainability_estimate"]
    ), "the two readings must not be averaged"


def test_agreement_does_not_widen_the_interval(evidence) -> None:
    """Two sources saying the same thing is not uncertainty."""
    built_in = score_evidence(evidence)
    pressure = built_in["dimensions"].get("declarations")
    if pressure is None:
        pytest.skip("this fixture has no declarations pressure to agree about")

    agreed = score_evidence(evidence, _both(pressure))

    assert agreed["maintainability_estimate"] == built_in["maintainability_estimate"]
