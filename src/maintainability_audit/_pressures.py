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

from ._calibration import DIMENSION_REFERENCES, WARN_WEIGHT
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


def _production(primary: object, fallback: object) -> float | None:
    """A production-only count, falling back to the combined one.

    The fallback exists because a summary may predate the production
    split. It falls back to the *combined measurement*, never to zero.
    """
    value = measured(primary)
    return measured(fallback) if value is None else value


def production_pressures(summary: SummaryEvidence) -> dict[str, float | None]:
    """The same pressures, counting production code only.

    ``analyzability`` and ``testability`` ask how understandable and how
    testable the *production* code is. Charging them for a long test body
    inverts the incentive — extracting duplicated test setup into a
    fixture would lower the score for improving the code.
    """
    files = _production(summary.production_files_scanned, summary.files_scanned)
    decls = _production(summary.production_declarations_scanned, summary.declarations_scanned)
    gates = _production(summary.production_hard_gate_failures, summary.hard_gate_failures)
    return {
        "file_size": _weighted_rate(
            _production(summary.production_file_failures, summary.file_failures),
            _production(summary.production_file_warnings, summary.file_warnings),
            files,
        ),
        "declarations": _weighted_rate(
            _production(summary.production_function_failures, summary.function_failures),
            _production(summary.production_function_warnings, summary.function_warnings),
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
