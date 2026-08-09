"""The calibration constants must be derivable, not asserted.

``_calibration.py`` carries five reference medians and a curve constant
that set the meaning of every grade this tool emits. Left as bare
numbers they would be unfalsifiable — values someone once computed on
their own machine, which is precisely the kind of claim the 0.5.0
scoring rewrite exists to stop making.

So the corpus measurements are checked in, and these tests re-derive the
constants from them offline: no clone, no network, no trust required. If
someone edits a constant by hand, or re-measures without updating the
stored values, this fails.

``tools/calibration/measure.py`` regenerates ``measurements.json`` from
the pinned commits in ``corpus.json``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maintainability_audit._calibration import CALIBRATION_C, DIMENSION_REFERENCES, DIMENSION_WEIGHTS
from maintainability_audit._derive import (
    DIMENSIONS,
    FIXED_REFERENCES,
    MIN_CORPUS_SIZE,
    derive_curve_constant,
    derive_references,
    normalized_pressures,
)
from maintainability_audit.scoring import score_report

CORPUS_DIR = Path(__file__).resolve().parents[1] / "tools" / "calibration"


def load(name: str) -> dict:
    return json.loads((CORPUS_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def measurements() -> list[dict]:
    return load("measurements.json")["measurements"]


# ---------------------------------------------------------------------------
# The constants are what the corpus says they are
# ---------------------------------------------------------------------------

def test_dimension_references_match_the_measured_corpus(measurements: list[dict]) -> None:
    assert derive_references(measurements) == DIMENSION_REFERENCES


def test_the_fixed_gates_reference_is_checked_rather_than_echoed(measurements: list[dict]) -> None:
    """A hand-edited ``gates`` must fail the suite like any other constant.

    ``gates`` is the one reference the corpus does not measure, so it
    cannot be re-derived from the measurements — which briefly made it the
    one constant nothing checked: ``derive_references`` read it back out
    of ``_calibration`` and the test above compared it to itself. The
    authority now lives in ``_derive``, and these are two independent
    statements of the same number.
    """
    assert FIXED_REFERENCES["gates"] == DIMENSION_REFERENCES["gates"]
    assert derive_references(measurements)["gates"] == FIXED_REFERENCES["gates"]

    tampered = dict(DIMENSION_REFERENCES) | {"gates": 0.5}

    assert derive_references(measurements) != tampered, "editing gates by hand must be caught"


def test_curve_constant_matches_the_measured_corpus(measurements: list[dict]) -> None:
    derived = derive_curve_constant(measurements, DIMENSION_REFERENCES, DIMENSION_WEIGHTS)

    assert derived == CALIBRATION_C


def test_the_corpus_median_repo_scores_exactly_a_b(measurements: list[dict]) -> None:
    """The headline calibration claim, checked rather than asserted:
    a well-run real codebase earns a 4.0."""
    scores = sorted(
        score_report({"summary": _summary(entry)})["overall"] for entry in measurements
    )
    middle = scores[len(scores) // 2] if len(scores) % 2 else (scores[len(scores) // 2 - 1] + scores[len(scores) // 2]) / 2

    assert 3.9 <= middle <= 4.1, f"corpus median scored {middle}, not ~4.0"


# ---------------------------------------------------------------------------
# The corpus itself has to stay trustworthy
# ---------------------------------------------------------------------------

def test_manifest_pins_every_repo_to_an_exact_commit() -> None:
    """A floating reference corpus is not a reference. Every entry needs a
    full SHA so a recalibration is reproducible rather than a snapshot of
    whatever HEAD happened to be."""
    repos = load("corpus.json")["repos"]

    assert len(repos) >= MIN_CORPUS_SIZE
    for repo in repos:
        assert len(repo["commit"]) == 40, f"{repo['name']} is not pinned to a full commit SHA"
        assert repo["url"].startswith("https://"), repo["name"]


def test_measurements_cover_the_manifest(measurements: list[dict]) -> None:
    manifest_names = {repo["name"] for repo in load("corpus.json")["repos"]}
    measured_names = {entry["repo"] for entry in measurements}

    assert measured_names == manifest_names


def test_every_measurement_carries_every_dimension(measurements: list[dict]) -> None:
    for entry in measurements:
        assert set(entry["dimensions"]) == set(DIMENSIONS), entry["repo"]
        assert entry["files"] > 0, entry["repo"]


def test_corpus_spans_a_range_of_repo_sizes(measurements: list[dict]) -> None:
    """A reference drawn only from small libraries would bake in the same
    size bias that made the previous model score Django an F."""
    sizes = sorted(entry["files"] for entry in measurements)

    assert sizes[0] < 200
    assert sizes[-1] > 2000


# ---------------------------------------------------------------------------
# Derivation refuses to produce a number it cannot justify
# ---------------------------------------------------------------------------

def test_derivation_rejects_a_corpus_too_small_to_have_a_median() -> None:
    tiny = [{"repo": "x", "files": 1, "dimensions": dict.fromkeys(DIMENSIONS, 0.1)}]

    with pytest.raises(ValueError, match="at least"):
        derive_references(tiny)


def test_normalized_pressure_is_one_for_a_repo_at_every_reference() -> None:
    at_reference = [{"repo": "ref", "files": 100, "dimensions": dict(DIMENSION_REFERENCES)}]

    values = normalized_pressures(at_reference, DIMENSION_REFERENCES, DIMENSION_WEIGHTS)

    assert values == [pytest.approx(1.0)]


def _summary(entry: dict) -> dict:
    """Rebuild a scoreable summary from stored raw pressures.

    Populations are carried through so the rates reconstruct exactly;
    warnings are folded into failures because only the combined pressure
    was recorded. The stored ``evidence`` block is merged last so the
    rubric aspects price here exactly as the derivation priced them —
    this test exercises the same rollup users receive, which is the
    point of the anchor.
    """
    files, decls = entry["files"], max(1, entry["declarations"])
    dims = entry["dimensions"]
    return {
        "files_scanned": files,
        "declarations_scanned": decls,
        "production_files_scanned": files,
        "production_declarations_scanned": decls,
        "file_failures": dims["file_size"] * files,
        "file_warnings": 0,
        "function_failures": dims["declarations"] * decls,
        "function_warnings": 0,
        "production_file_failures": dims["file_size"] * files,
        "production_file_warnings": 0,
        "production_function_failures": dims["declarations"] * decls,
        "production_function_warnings": 0,
        "duplicate_blocks": dims["duplication"] * files,
        "risk_findings": dims["risk"] * files,
        "hard_gate_failures": dims["gates"] / 0.05,
        "production_hard_gate_failures": dims["gates"] / 0.05,
        **entry.get("evidence", {}),
    }
