"""The measured pressures a summary carries, as rates.

Split out of ``scoring`` when that module crossed the file-length gate
this tool enforces on everyone else. The seam is a real one rather than
a convenience: this layer knows only about counts and populations, the
aspect layer turns pressures into 0-5 scores, and ``scoring`` bands and
grades them. Nothing here imports either of the two above it, so the
dependency runs one way.
"""
from __future__ import annotations

from typing import Any

from ._calibration import DIMENSION_REFERENCES, WARN_WEIGHT


def _rate(count: float, population: float) -> float:
    return count / population if population > 0 else 0.0


def dimension_pressures(summary: dict[str, Any]) -> dict[str, float]:
    """The five independently-sourced pressures, as rates.

    Unlike the previous model's five categories — which were five linear
    re-weightings of the same handful of counts — each of these is drawn
    from a different measurement, so they can disagree with each other.
    """
    files = summary.get("files_scanned", 0)
    decls = summary.get("declarations_scanned", 0)
    return {
        "file_size": _rate(summary.get("file_failures", 0), files)
        + WARN_WEIGHT * _rate(summary.get("file_warnings", 0), files),
        "declarations": _rate(summary.get("function_failures", 0), decls)
        + WARN_WEIGHT * _rate(summary.get("function_warnings", 0), decls),
        "duplication": _rate(summary.get("duplicate_blocks", 0), files),
        "risk": _rate(summary.get("risk_findings", 0), files),
        # Gates are discrete policy breaches, not a population sample, so
        # they are scaled to sit on the same footing as a rate.
        "gates": 0.05 * summary.get("hard_gate_failures", 0),
    }


def normalize_production(summary: dict[str, Any]) -> dict[str, float]:
    """Production-only pressures, in the same normalized units."""
    raw = production_pressures(summary)
    return {name: _relative(value, DIMENSION_REFERENCES[name]) for name, value in raw.items()}


def production_pressures(summary: dict[str, Any]) -> dict[str, float]:
    """The same pressures, counting production code only.

    ``analyzability`` and ``testability`` ask how understandable and how
    testable the *production* code is. Charging them for a long test body
    inverts the incentive — extracting duplicated test setup into a
    fixture would lower the score for improving the code. Falls back to
    the combined counts when a summary predates the split.
    """
    files = summary.get("production_files_scanned", summary.get("files_scanned", 0))
    decls = summary.get("production_declarations_scanned", summary.get("declarations_scanned", 0))
    return {
        "file_size": _rate(summary.get("production_file_failures", summary.get("file_failures", 0)), files)
        + WARN_WEIGHT * _rate(summary.get("production_file_warnings", summary.get("file_warnings", 0)), files),
        "declarations": _rate(
            summary.get("production_function_failures", summary.get("function_failures", 0)), decls
        )
        + WARN_WEIGHT
        * _rate(summary.get("production_function_warnings", summary.get("function_warnings", 0)), decls),
        "gates": 0.05 * summary.get("production_hard_gate_failures", summary.get("hard_gate_failures", 0)),
    }


# The summary counts each dimension's pressure is computed from. A
# dimension whose inputs are absent was not measured, which is a
# different statement from "measured and found clean" — see
# :func:`unmeasured_dimensions`.
DIMENSION_INPUTS: dict[str, tuple[str, ...]] = {
    "file_size": ("files_scanned", "file_failures", "file_warnings"),
    "declarations": ("declarations_scanned", "function_failures", "function_warnings"),
    "duplication": ("files_scanned", "duplicate_blocks"),
    "risk": ("files_scanned", "risk_findings"),
    "gates": ("hard_gate_failures",),
}

# declaration_size curves the production-only pressure, so it has its
# own inputs — each falling back to the combined count, as
# :func:`production_pressures` does.
PRODUCTION_DECLARATION_INPUTS: tuple[tuple[str, str], ...] = (
    ("production_declarations_scanned", "declarations_scanned"),
    ("production_function_failures", "function_failures"),
    ("production_function_warnings", "function_warnings"),
)


def unmeasured_dimensions(summary: dict[str, Any]) -> set[str]:
    """Dimensions whose input counts the summary does not carry.

    Every pressure above reads its counts with ``.get(name, 0)``, which
    silently turns "this report does not say how many risk findings
    there were" into "there were none" — a perfect score for saying
    nothing. An audit found the same shape in the testability cap and
    demonstrated that deleting a field *raised* the evidence floor;
    sweeping every summary key showed three more fields with the
    identical property (``file_failures``, ``files_scanned``,
    ``risk_findings``). Absent inputs now make the dimension unmeasured,
    so its aspect scores None: priced at the anchor for the point
    estimate and at zero for the floor the grade is banded from.
    """
    return {
        dimension
        for dimension, inputs in DIMENSION_INPUTS.items()
        if any(name not in summary for name in inputs)
    }


def production_declarations_measured(summary: dict[str, Any]) -> bool:
    """Whether the production-only declaration pressure has its inputs."""
    return all(
        primary in summary or fallback in summary
        for primary, fallback in PRODUCTION_DECLARATION_INPUTS
    )


def normalize(pressures: dict[str, float]) -> dict[str, float]:
    """Express each pressure as a multiple of what real code carries.

    1.0 means "typical of the mature OSS corpus". 2.0 means twice the
    trouble a well-run real codebase shows on that dimension. This is
    the unit the report should speak in, because "duplication 3.1x" is
    actionable in a way that "duplication 0.6346" is not.
    """
    return {name: _relative(value, DIMENSION_REFERENCES[name]) for name, value in pressures.items()}


def _relative(value: float, reference: float) -> float:
    """Express a pressure as a multiple of its reference.

    A reference of zero means the corpus showed none of this at all, so
    there is nothing to be a multiple *of*. Report 0.0 rather than
    dividing — the dimension simply carries no signal for this scale.
    """
    if reference <= 0:
        return 0.0
    return value / reference
