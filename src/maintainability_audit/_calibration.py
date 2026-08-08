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

# Median raw pressure per dimension across the 14-repo reference corpus
# defined in ``tools/calibration/corpus.json``, measured under the
# package default thresholds.
#
# These live on wildly different scales — measured, not guessed:
# duplication's median is ~19x file_size's and ~63x declarations'.
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
DIMENSION_REFERENCES: dict[str, float] = {
    "file_size": 0.0779,
    "declarations": 0.0243,
    "duplication": 1.4659,
    "risk": 0.0546,
    "gates": 0.1500,
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
CALIBRATION_C = 5.2754

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

