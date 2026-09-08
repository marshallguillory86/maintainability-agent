"""The analyzer half of a report, and the join that completes it.

Split from `report.py` at the 500-line gate this tool enforces on
everyone else. The seam is real rather than arithmetic: everything here
is about the external analyzer tier — what it measured, what it could
not, and how its criterion set is completed from the built-in scanner so
a language no tool reads cognitively can still be analyzer-driven.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ._analysis import analyze
from ._criteria_scope import built_in_readings
from ._documents import (
    coverage_document,
    findings_document,
    measurement_document,
    unidentified_source_paths,
)
from ._environment import environment_work_order
from ._metrics_types import FunctionMetric
from ._pressures import (
    ExternalPressures,
    analyzer_pressures,
    analyzer_production_pressures,
    declined_dimensions,
)


def analyzer_sections(
    root: Path,
    config: dict[str, Any],
    run_analyzers: bool,
    function_metrics: list[FunctionMetric],
) -> dict[str, Any]:
    """The three analyzer sections, or their empty forms.

    Extracted because `build_report` reached complexity 15 against this
    project's own limit. Four conditionals all asking the same question
    belong behind one, and the empty forms are stated here rather than
    repeated at each call site.
    """
    if not run_analyzers:
        return {"coverage": None, "findings": [], "measurements": {},
                "pressures": None, "environment": []}
    analysis = analyze(root, config)
    coverage = coverage_document(analysis)
    # P8: where the analyzer tier could not drive a dimension, say so on
    # the coverage document rather than leaving the built-in fallback to
    # be inferred from an absent number. Attached here because only this
    # layer holds both the measurements and the rubric's thresholds.
    # The scanner's own reading of each declaration, so the analyzer tier
    # can complete a criterion set no single tool covers (per concept,
    # not per dimension). Keyed the way the join is proven: (path, line).
    prefix = root.as_posix().rstrip("/") + "/"
    built_in = built_in_readings(function_metrics, prefix)
    coverage["dimensions_declined"] = list(
        declined_dimensions(analysis.measurements, False, built_in, prefix))
    return {
        "coverage": coverage,
        # ADR 006 §2c: what did not run and what it would take, for the
        # user to act on. Emitted here because only the analysis knows
        # which tools were *selected*; the agent never runs the commands.
        "environment": environment_work_order(analysis.coverage),
        "findings": findings_document(analysis, root),
        # Path spellings normalization refused (zero or several matches)
        # — visible, so a refusal is never mistaken for an identification.
        "unidentified_source_paths": unidentified_source_paths(analysis, root),
        "measurements": measurement_document(analysis, root),
        # The analyzers' reading of the scorer's dimensions, primary for
        # each it covers (ADR 006 §1); where None the built-in stands, so
        # an unmeasured dimension is unmeasured, not clean. Both
        # populations, since the production aspects read this.
        "pressures": ExternalPressures(
            all_code=analyzer_pressures(
                analysis.measurements, config["thresholds"], built_in, prefix),
            production=analyzer_production_pressures(
                analysis.measurements, config["thresholds"], built_in, prefix),
            # The raw readings ride along so the scorer can price
            # per-concept tool disagreement into the range (3.4).
            measurements=tuple(analysis.measurements),
        ),
    }
