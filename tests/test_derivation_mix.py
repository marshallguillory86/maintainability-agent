"""The fit replays the shipped mix, or the constant describes nothing.

`score_evidence` uses the analyzers' declaration pressure when they
measured the full concept set, and the built-in reading otherwise
(ADR 006 §1). `_derive._corpus_overall` fitted against the built-in
reading for every repository, so `CALIBRATION_C` was derived from a
pipeline the product no longer runs.

That is the failure mode this whole derivation exists to prevent, and it
has happened three times already — each time the fit differed from the
live path by one step (category rounding, the untested cap, per-aspect
rounding), and each time the corpus median survived while the
per-repository claim did not. A fourth divergence, this one in *which
source supplied the number*, would be the largest yet: on a repository
where the analyzers see two thirds of what the built-ins do, the two
readings are not close.

So the mix is applied by one function that both paths call, and a
`measurements.json` with no analyzer column is refused rather than
fitted — that file was produced by the old pipeline and re-deriving from
it would silently reproduce the old constant.
"""
from __future__ import annotations

import pytest

from maintainability_audit._derive import (
    derive_references,
    primary_declarations,
    require_analyzer_column,
)


def _row(built_in: float, analyzer: float | None) -> dict:
    """One corpus row, both readings, in the stored shape."""
    return {
        "repo": "r",
        "files": 100,
        "declarations": 400,
        "dimensions": {"file_size": 0.0, "declarations": built_in,
                       "duplication": 0.0, "risk": 0.0, "gates": 0.0},
        "production_dimensions": {"declarations": built_in},
        "analyzer_production_dimensions": (
            None if analyzer is None else {"declarations": analyzer}
        ),
        "evidence": {},
    }


def test_the_analyzer_reading_is_used_when_it_exists() -> None:
    """Same rule as `scoring._primary_pressures`, replayed on stored rows."""
    assert primary_declarations(_row(0.40, 0.12)) == 0.12


def test_the_built_in_reading_stands_when_the_pool_did_not_contribute() -> None:
    """`null` is unmeasured, not zero.

    A repository the pool could not read is recorded with a null analyzer
    column rather than dropped. Reading that null as a pressure of zero
    would fit the curve against a corpus of imaginary clean code.
    """
    assert primary_declarations(_row(0.40, None)) == 0.40


def test_a_partial_concept_set_falls_back_the_same_way() -> None:
    """`analyzer_production_dimensions` present but `declarations` None.

    That is what the full-concept-set rule produces: the pool ran, and
    measured too narrow a set to compose the dimension.
    """
    row = _row(0.40, 0.12)
    row["analyzer_production_dimensions"] = {"declarations": None}

    assert primary_declarations(row) == 0.40


def test_a_row_with_no_analyzer_column_at_all_is_refused() -> None:
    """The old pipeline's file, caught rather than fitted.

    Silently falling back for every row would re-derive the built-in
    constant and label it the analyzer-primary one.
    """
    row = _row(0.40, None)
    del row["analyzer_production_dimensions"]

    with pytest.raises(ValueError, match="analyzer_production_dimensions"):
        primary_declarations(row)


def test_derivation_refuses_a_measurements_file_from_the_old_pipeline() -> None:
    """One check at the top, naming the remedy.

    A per-row error deep in the fit would report an arithmetic problem
    for what is really a stale input file.
    """
    old = [{"repo": "a", "dimensions": {"declarations": 0.1}},
           {"repo": "b", "dimensions": {"declarations": 0.2}}]

    with pytest.raises(ValueError, match="--with-analyzers"):
        require_analyzer_column(old)


def test_a_file_with_the_column_passes_the_check() -> None:
    assert require_analyzer_column([_row(0.4, 0.1), _row(0.3, None)]) is None


def test_the_reference_median_is_taken_over_the_same_mix_the_fit_uses() -> None:
    """Numerator and denominator must be the same measurement.

    The reference is what the fit divides by. Taking its median over the
    built-in reading while the numerator is the analyzer reading is a
    ratio between two different instruments — the mistake that produced
    four published ratios (4.0x, 0.3x, 0.19x, 0.77x) before this
    comparison was trustworthy.
    """
    # Eight rows: `derive_references` refuses a smaller corpus, so one
    # unusual repository cannot move a median. Two fall back.
    rows = [_row(value / 10, None if value in {2, 5} else 0.9) for value in range(1, 9)]
    mixed = sorted(0.9 if value not in {2, 5} else value / 10 for value in range(1, 9))

    from statistics import median
    assert derive_references(rows)["declarations"] == pytest.approx(round(median(mixed), 4))
