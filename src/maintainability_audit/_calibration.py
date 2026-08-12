"""Calibration constants, fitted to real code rather than chosen.

Split from ``scoring.py`` (2026-08-07). The scoring *logic* is small and
stable; these *numbers* are empirical findings with provenance, and they
carry the argument for why the score means anything. Keeping them apart
makes it obvious that re-fitting the corpus is a deliberate act with its
own review, not a tweak buried in a formula.

Every value here was measured, not guessed. See ``docs/standard.md`` for
the corpus and the method.
"""
from __future__ import annotations

CATEGORIES = ["modularity", "reusability", "analyzability", "modifiability", "testability"]

# Median raw pressure per dimension across the 40-repo reference corpus
# defined in ``tools/calibration/corpus.json``, measured under the
# package default thresholds.
#
# These live on wildly different scales — measured, not guessed:
# duplication's median is ~65x file_size's and ~62x declarations'.
# Summing raw pressures therefore scores duplication and almost nothing
# else, which is the same class of bug as the count-based model it
# replaced. Each dimension is divided by its own reference so that
# "typical of real code" equals 1.0 everywhere, and the dimensions
# become commensurable.
#
# DO NOT hand-edit. Regenerate with:
#
#     python3 tools/calibration/measure.py
#
# and re-run whenever the default thresholds change — these are the
# anchor for every score the tool emits, so changing thresholds without
# recalibrating silently moves the meaning of every grade.
# ``tests/test_calibration_corpus.py`` re-derives them offline from the
# checked-in measurements and fails if they drift.
# risk moved 0.0726 -> 0.0733 on 2026-08-12, re-measured across the same
# 40 repositories. The cause is this release adding three default risk
# patterns (absence-as-zero, vacuous-assertion, silent-truncation), all
# Python-only, which fire on the 13 Python repositories in the corpus and
# nudge the median. Every other reference and the curve constant are
# unchanged, which is the check that the move is the patterns rather than
# drift in the pipeline.
DIMENSION_REFERENCES: dict[str, float] = {
    "file_size": 0.0576,
    "declarations": 0.0599,
    "duplication": 3.7350,
    "risk": 0.0733,
    # Fixed, not corpus-derived — see ``_derive.FIXED_REFERENCES``, which
    # is the authority for this value and carries the reasoning. Stated
    # again here rather than imported, so the two are independent claims
    # that ``tests/test_calibration_corpus.py`` can compare.
    "gates": 0.05,
}

# Risk patterns are user-configured and their density varies by two
# orders of magnitude across the corpus, so they get a reduced vote
# rather than an equal one.
DIMENSION_WEIGHTS: dict[str, float] = {
    "file_size": 1.0,
    "declarations": 1.0,
    "duplication": 1.0,
    "risk": 0.5,
    "gates": 0.5,
}

# score = 5c/(n+c), where n is the weighted mean of normalized pressures.
#
# c is fitted so the *measured* median of the reference corpus scores
# exactly 4.0 — a well-run real codebase earns a B and everything above
# it has to be paid for. Note the corpus median repo does not sit at
# n = 1.0 even though every reference above is itself a median: no single
# repo is simultaneously median on all five dimensions, so the median of
# the means is not the mean of the medians. Fitting to the observed value
# is what keeps the documented claim literally true.
#
# The curve is hyperbolic rather than linear so it never saturates: there
# is always resolution left between two bad repos, which is exactly what
# the old count-based model lost.
#
# Derived by ``_derive.derive_curve_constant``; regenerate with
# ``tools/calibration/measure.py``.
# Re-fitted twice as the overall became the rubric rollup: first with
# structural aspects only, then again when the corpus measurements
# began carrying the evidence block (test presence, dead code,
# near-duplication, idioms, documentation) — an audit correctly noted
# that an anchor derived through fewer aspects than a live report gets
# does not describe the shipped score. c sits inside every per-aspect
# curve, so it is recovered by bisection against the corpus median
# rather than in closed form. History aspects stay out of the anchor:
# the corpus is pinned via shallow fetches, so they renormalize away in
# the derivation exactly as they do for any shallow clone. Same anchor
# throughout: the median mature repo rolls up to exactly 4.0.
# Third fit: unknown aspects now price at the corpus anchor (4.0)
# instead of renormalizing away — an audit showed renormalization let a
# shallow clone outscore the same code with its history visible.
# Fourth fit: the derivation now rounds categories to one decimal
# before the overall, exactly as score_report ships them — an audit
# found six corpus repos differing between the rounded and unrounded
# paths while the docs claimed "same pipeline". The rounded pipeline
# is a step function, so c is the midpoint of the plateau where the
# corpus median hits 4.0 exactly.
# Fifth fit: the derivation now calls the shipped rollup itself rather
# than restating it, so the untested testability cap lands on corpus
# members too, and knowledge_concentration carries weight instead of
# being scored and ignored. Both change what the median repo rolls up
# to, so c is re-fitted. The reference medians re-measured byte-identical
# for the third audit running.
CALIBRATION_C = 2.6279

# A failure is a threshold breach; a warning is an approach to one.
WARN_WEIGHT = 0.3

# Ceilings a repo may not exceed and still claim the grade. A+ requires
# nothing wrong anywhere; A tolerates a trace. Both are deliberately
# strict — see the module docstring.
GRADE_GATES: dict[str, dict[str, float]] = {
    "A+": {"file_fail_rate": 0.0, "decl_fail_rate": 0.0, "file_warn_rate": 0.02,
           "decl_warn_rate": 0.02, "duplication": 0.0, "risk": 0.0, "gates": 0.0},
    "A": {"file_fail_rate": 0.005, "decl_fail_rate": 0.005, "file_warn_rate": 0.05,
          "decl_warn_rate": 0.05, "duplication": 0.02, "risk": 0.02, "gates": 0.0},
}

