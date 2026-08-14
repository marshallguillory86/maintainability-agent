"""The measured pressures a summary carries, as rates.

Split out of ``scoring`` when that module crossed the file-length gate
this tool enforces on everyone else. The seam is a real one rather than
a convenience: this layer knows only about counts and populations, the
aspect layer turns pressures into 0-5 scores, and ``scoring`` bands and
grades them. Nothing here imports either of the two above it, so the
dependency runs one way.

**Every count arrives as a typed evidence state** (ADR 001 stage 4). The
previous version read the summary dictionary with ``get(name, 0)``,
which silently turned "this report does not say how many risk findings
there were" into "there were none" — a perfect score for saying
nothing. Six audit rounds fixed instances of that shape; a seventh
found four more fields carrying it. The defence was a companion
function listing which keys had to be present, which worked only for as
long as someone remembered to extend the list.

A pressure is now computed **only from ``Measured`` inputs**. Any other
state makes the pressure ``None``, which travels as "unmeasured" all
the way to the aspect and prices at zero in the evidence floor. There is
no default to forget to guard.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from ._calibration import DIMENSION_REFERENCES, WARN_WEIGHT
from ._metrics_types import Measurement, is_test_path
from .evidence import Measured, SummaryEvidence


def measured(state: object) -> float | None:
    """The number a state carries, or ``None`` if it does not carry one.

    The single place evidence states become arithmetic. ``Measured(0)``
    returns ``0.0``; ``Unknown`` and ``NotApplicable`` return ``None``
    and cannot be mistaken for it.
    """
    return float(state.value) if isinstance(state, Measured) else None


def _rate(count: float, population: float) -> float:
    return count / population if population > 0 else 0.0


def _weighted_rate(
    failures: float | None, warnings: float | None, population: float | None
) -> float | None:
    """Failure rate plus discounted warning rate, or None if anything is unknown."""
    if failures is None or warnings is None or population is None:
        return None
    return _rate(failures, population) + WARN_WEIGHT * _rate(warnings, population)


def _ratio(count: float | None, population: float | None) -> float | None:
    if count is None or population is None:
        return None
    return _rate(count, population)


def dimension_pressures(summary: SummaryEvidence) -> dict[str, float | None]:
    """The five independently-sourced pressures, as rates.

    Unlike the previous model's five categories — which were five linear
    re-weightings of the same handful of counts — each of these is drawn
    from a different measurement, so they can disagree with each other.

    ``None`` for a dimension whose inputs were not all measured.
    """
    files = measured(summary.files_scanned)
    decls = measured(summary.declarations_scanned)
    gates = measured(summary.hard_gate_failures)
    return {
        "file_size": _weighted_rate(
            measured(summary.file_failures), measured(summary.file_warnings), files
        ),
        "declarations": _weighted_rate(
            measured(summary.function_failures), measured(summary.function_warnings), decls
        ),
        "duplication": _ratio(measured(summary.duplicate_blocks), files),
        "risk": _ratio(measured(summary.risk_findings), files),
        # Gates are discrete policy breaches, not a population sample, so
        # they are scaled to sit on the same footing as a rate.
        "gates": None if gates is None else 0.05 * gates,
    }


def _production(primary: object) -> float | None:
    """A production-only count. Unknown stays unknown.

    This used to fall back to the combined count when the production
    figure was absent, on the theory that a summary might predate the
    production split. An audit killed it twice over: the report contract
    establishes that **no consumer rescores a historical report**, so the
    fallback served no real caller, and it silently resurrected an
    ``Unknown`` as a measured value — deleting
    ``production_declarations_scanned`` produced a measured pressure and
    raised the reported overall from 4.3 to 4.6. ADR 001 §3 forbids
    exactly this: compatibility for a consumer that does not exist.
    """
    return measured(primary)


def production_pressures(summary: SummaryEvidence) -> dict[str, float | None]:
    """The same pressures, counting production code only.

    ``analyzability`` and ``testability`` ask how understandable and how
    testable the *production* code is. Charging them for a long test body
    inverts the incentive — extracting duplicated test setup into a
    fixture would lower the score for improving the code.
    """
    files = _production(summary.production_files_scanned)
    decls = _production(summary.production_declarations_scanned)
    gates = _production(summary.production_hard_gate_failures)
    return {
        "file_size": _weighted_rate(
            _production(summary.production_file_failures),
            _production(summary.production_file_warnings),
            files,
        ),
        "declarations": _weighted_rate(
            _production(summary.production_function_failures),
            _production(summary.production_function_warnings),
            decls,
        ),
        "gates": None if gates is None else 0.05 * gates,
    }


def normalize_production(summary: SummaryEvidence) -> dict[str, float | None]:
    """Production-only pressures, in the same normalized units."""
    return normalize(production_pressures(summary))


def normalize(pressures: dict[str, float | None]) -> dict[str, float | None]:
    """Express each pressure as a multiple of what real code carries.

    1.0 means "typical of the mature OSS corpus". 2.0 means twice the
    trouble a well-run real codebase shows on that dimension. This is
    the unit the report should speak in, because "duplication 3.1x" is
    actionable in a way that "duplication 0.6346" is not.
    """
    return {
        name: None if value is None else _relative(value, DIMENSION_REFERENCES[name])
        for name, value in pressures.items()
    }


def _relative(value: float, reference: float) -> float:
    """Express a pressure as a multiple of its reference.

    A reference of zero means the corpus showed none of this at all, so
    there is nothing to be a multiple *of*. Report 0.0 rather than
    dividing — the dimension simply carries no signal for this scale.
    """
    if reference <= 0:
        return 0.0
    return value / reference


# The concepts the `declarations` dimension needs, and the rubric
# thresholds that decide a breach. All three, because `function_status`
# fails a declaration on **lines OR complexity OR cognitive complexity**
# — a bridge counting only complexity measures something narrower and
# cannot be compared against it. Three ratios were quoted from that
# mistake before a test comparing every criterion caught it.
DECLARATION_CRITERIA: tuple[tuple[str, str, str], ...] = (
    ("cyclomatic_complexity", "warn_complexity", "max_complexity"),
    ("declaration_lines", "warn_function_lines", "max_function_lines"),
    ("cognitive_complexity", "warn_cognitive_complexity", "max_cognitive_complexity"),
)

# Dimensions an analyzer can supply at all. `file_size` needs per-file
# line counts no permissively-licensed tool in the pool reports, and
# `risk` and `gates` are configured policy with no external equivalent.
ANALYZER_DIMENSIONS: tuple[str, ...] = ("declarations",)


def _breach_counts(
    per_unit: dict[str, dict[str, float]], thresholds: dict[str, Any]
) -> tuple[int, int]:
    """Units failing or warning on *any* criterion, counted once each.

    Matches `declarations.function_status`: a declaration is one failure
    however many limits it breaks. Counting per criterion would
    double-count the worst code, which is the direction that flatters
    nothing but is wrong all the same.
    """
    failures = warnings = 0
    for values in per_unit.values():
        failed = warned = False
        for concept, warn_key, fail_key in DECLARATION_CRITERIA:
            value = values.get(concept)
            if value is None or warn_key not in thresholds or fail_key not in thresholds:
                continue
            if value > float(thresholds[fail_key]):
                failed = True
            elif value > float(thresholds[warn_key]):
                warned = True
        failures += failed
        warnings += warned and not failed
    return failures, warnings


@dataclass(frozen=True)
class ExternalPressures:
    """A second source's reading of the scorer's dimensions, both populations.

    Both, in one object, because the scorer keeps two populations and
    substituting one reading into both slots is a real distortion rather
    than a rounding error: it charges production code for the state of
    the test suite. That was the previous behaviour, and it was invisible
    at the call site — a single dict went in and got used twice. Pairing
    them makes supplying only one impossible to do by accident.
    """

    all_code: dict[str, float | None]
    production: dict[str, float | None]

    def measured_anything(self) -> bool:
        return any(value is not None for value in self.all_code.values()) or any(
            value is not None for value in self.production.values()
        )


def _declaration_pressure(
    measurements: list[Measurement], thresholds: dict[str, Any], production_only: bool
) -> dict[str, float | None]:
    """Weighted breach rate over the analyzers' declarations."""
    per_unit: dict[str, dict[str, float]] = defaultdict(dict)
    for measurement in measurements:
        if production_only and is_test_path(measurement.path or measurement.unit):
            continue
        per_unit[measurement.unit][measurement.concept] = measurement.value

    relevant = {
        unit: values
        for unit, values in per_unit.items()
        if any(concept in values for concept, _w, _f in DECLARATION_CRITERIA)
    }
    if not relevant:
        return dict.fromkeys(ANALYZER_DIMENSIONS)

    failures, warnings = _breach_counts(relevant, thresholds)
    return {"declarations": _weighted_rate(failures, warnings, len(relevant))}


def analyzer_pressures(
    measurements: list[Measurement], thresholds: dict[str, Any]
) -> dict[str, float | None]:
    """The scorer's own dimensions, computed from analyzer measurements.

    A **drop-in for** :func:`dimension_pressures`: same formula, same
    breach criteria, the same population — every declaration, test code
    included, because that is what `declarations_scanned` counts. The
    rubric's thresholds applied to the analyzers' numbers. That is ADR
    008's seam — a tool contributes measurements, the rubric decides what
    they mean.

    Getting this wrong is not a small error, and it was made three times.
    An earlier version returned a mean band pressure where the built-in
    path returns a weighted breach rate; the next counted only complexity
    where the built-in counts lines, complexity and cognitive complexity.
    Each produced a confident ratio that described my own bridge rather
    than the code being audited.

    ``None`` where nothing was measured — never zero.
    """
    return _declaration_pressure(measurements, thresholds, production_only=False)


def analyzer_production_pressures(
    measurements: list[Measurement], thresholds: dict[str, Any]
) -> dict[str, float | None]:
    """The same reading, over production code only.

    The drop-in for :func:`production_pressures`, which is what
    `analyzability` and `declaration_size` actually consume. Both
    populations are needed because the scorer keeps both: substituting an
    all-declarations reading into the production slot was a stated
    compromise from when this bridge could not tell the two apart, and it
    made the alternative rollup pessimistic on any repository whose tests
    are rougher than its production code.

    The gap is not small. On flask, 1,494 of 2,206 declarations the
    analyzers see are test code; the pressure moves 0.0049 → 0.0138.
    """
    return _declaration_pressure(measurements, thresholds, production_only=True)
