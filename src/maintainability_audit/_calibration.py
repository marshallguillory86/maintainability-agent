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

# Median raw pressure per dimension across mature human-written OSS
# (requests, flask, click, attrs, httpx, express, tornado, lodash, axios,
# black, pytest) under the default thresholds.
#
# These live on wildly different scales — measured, not guessed:
# duplication's median is 15x file_size's and 93x declarations'. Summing
# raw pressures therefore scores duplication and almost nothing else,
# which is the same class of bug as the count-based model it replaced.
# Each dimension is divided by its own reference so that "typical of
# real code" equals 1.0 everywhere, and the dimensions become
# commensurable.
#
# Regenerate these with the corpus harness whenever the default
# thresholds change; they are the anchor for the entire scale.
DIMENSION_REFERENCES: dict[str, float] = {
    "file_size": 0.1233,
    "declarations": 0.0207,
    "duplication": 1.9245,
    "risk": 0.0525,
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
# c is fitted so the *measured* median of the OSS corpus (n = 1.2929)
# scores exactly 4.0 — a well-run real codebase earns a B and everything
# above it has to be paid for. Note the corpus median repo sits at 1.29
# rather than 1.0: no single repo is simultaneously median on all five
# dimensions, so the median of the means is not the mean of the medians.
# Fitting to the observed value keeps the documented claim true.
#
# The curve is hyperbolic rather than linear so it never saturates: there
# is always resolution left between two bad repos, which is exactly what
# the old count-based model lost.
CALIBRATION_C = 5.1717

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

