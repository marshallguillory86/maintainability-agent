"""The properties that make a score mean something.

The 0.4.0 model was replaced after being measured against real code: it
counted findings in absolute terms, so every large codebase saturated the
floor. Django, pytest, black, tornado, click, httpx, attrs, lodash,
svelte, axios and fastapi all scored 0.0 / F while a 53-file toy repo
scored 4.6 / A.

These tests pin the properties that failure violated, so it cannot come
back quietly:

- size independence — the same *proportion* of trouble scores the same
  in a 50-file repo and a 5,000-file one
- no saturation — two bad repos remain distinguishable
- calibration — a repo at the corpus median lands on a B
- gated top grades — A+ requires every dimension clean, not a good average
"""
from __future__ import annotations

from maintainability_audit._calibration import DIMENSION_REFERENCES
from maintainability_audit.scoring import dimension_pressures, grade_for, normalize, score_report


def summary(files: int, decls: int, **overrides: int) -> dict[str, int]:
    base = {
        "files_scanned": files,
        "declarations_scanned": decls,
        "production_files_scanned": files,
        "production_declarations_scanned": decls,
        "file_warnings": 0,
        "file_failures": 0,
        "function_warnings": 0,
        "function_failures": 0,
        "production_file_warnings": 0,
        "production_file_failures": 0,
        "production_function_warnings": 0,
        "production_function_failures": 0,
        "duplicate_blocks": 0,
        "risk_findings": 0,
        "hard_gate_failures": 0,
        "production_hard_gate_failures": 0,
    }
    base.update(overrides)
    return base


def score(files: int, decls: int, **overrides: int) -> dict:
    return score_report({"summary": summary(files, decls, **overrides)})


# ---------------------------------------------------------------------------
# Size independence: the defect that made every real repo an F
# ---------------------------------------------------------------------------

def test_identical_proportions_score_identically_at_any_repo_size() -> None:
    """5% of files failing is 5% whether the repo has 50 files or 5000.

    The old model charged an absolute count, so a big repo was punished
    for being big and a small one flattered for being small."""
    small = score(100, 200, file_failures=5, function_failures=10)
    large = score(5000, 10000, file_failures=250, function_failures=500)

    assert small["overall"] == large["overall"]


def test_a_big_clean_repo_outscores_a_small_dirty_one() -> None:
    big_clean = score(5000, 10000, file_failures=50)
    small_dirty = score(40, 80, file_failures=20)

    assert big_clean["overall"] > small_dirty["overall"]


# ---------------------------------------------------------------------------
# No saturation: the scale must keep resolving all the way down
# ---------------------------------------------------------------------------

def test_two_bad_repos_remain_distinguishable() -> None:
    """The old curve pinned everything past ~3% of files to the floor,
    so 'bad' and 'catastrophic' were the same number."""
    bad = score(1000, 2000, file_failures=100, function_failures=200)
    worse = score(1000, 2000, file_failures=400, function_failures=800)

    assert bad["overall"] > worse["overall"]
    assert worse["overall"] > 0.0


def test_score_never_leaves_the_scale() -> None:
    catastrophic = score(
        100, 100, file_failures=100, function_failures=100, duplicate_blocks=9999, risk_findings=9999,
        hard_gate_failures=50,
    )

    assert 0.0 <= catastrophic["overall"] <= 5.0


# ---------------------------------------------------------------------------
# Calibration against the corpus
# ---------------------------------------------------------------------------

def test_a_repo_at_the_corpus_median_scores_in_the_b_range() -> None:
    """Feed back exactly the reference pressures the corpus produced. A
    typical well-run open-source codebase must not read as failing."""
    files = 1000
    at_median = {
        "files_scanned": files,
        "declarations_scanned": files,
        "file_failures": round(DIMENSION_REFERENCES["file_size"] * files),
        "function_failures": round(DIMENSION_REFERENCES["declarations"] * files),
        "duplicate_blocks": round(DIMENSION_REFERENCES["duplication"] * files),
        "risk_findings": round(DIMENSION_REFERENCES["risk"] * files),
        "hard_gate_failures": round(DIMENSION_REFERENCES["gates"] / 0.05),
    }
    result = score_report({"summary": summary(files, files, **at_median)})

    assert 3.5 <= result["overall"] <= 4.5, result["overall"]


def test_dimensions_are_reported_as_multiples_of_real_world_normal() -> None:
    files = 1000
    doubled = round(DIMENSION_REFERENCES["duplication"] * files * 2)
    result = score(files, files, duplicate_blocks=doubled)

    assert result["dimensions"]["duplication"] == 2.0
    assert result["worst_dimension"] == "duplication"


# ---------------------------------------------------------------------------
# A+ has to be earned on every dimension, not on an average
# ---------------------------------------------------------------------------

def test_a_plus_is_withheld_when_any_single_dimension_is_dirty() -> None:
    """A mean lets four clean dimensions hide one bad one. The gate is
    what makes the top grade expensive."""
    clean = {"file_fail_rate": 0.0, "decl_fail_rate": 0.0, "file_warn_rate": 0.0,
             "decl_warn_rate": 0.0, "duplication": 0.0, "risk": 0.0, "gates": 0.0}

    grade, blockers = grade_for(4.9, clean)
    assert (grade, blockers) == ("A+", [])

    # A trace of dirt costs A+ but still clears A's looser ceiling.
    grade, blockers = grade_for(4.9, {**clean, "decl_fail_rate": 0.004})
    assert grade == "A"
    assert any("decl_fail_rate" in blocker for blocker in blockers)

    # More than a trace cascades past A as well, rather than stepping
    # down exactly one grade and landing somewhere it did not earn.
    grade, blockers = grade_for(4.9, {**clean, "decl_fail_rate": 0.01})
    assert grade == "B"


def test_a_perfect_repo_can_still_reach_a_plus() -> None:
    """The gate must be strict, not unreachable — otherwise it stops
    being a target and starts being noise.

    "Perfect" now includes *evidence*: tests, docs, and a readable
    history with nothing wrong in it. A structurally-spotless repo with
    unknowns is capped at B — an audit showed a shallow clone could
    otherwise outscore the same repository with its history visible."""
    full = summary(500, 1000)
    full.update({
        "test_file_count": 100,
        "production_declarations_scanned": 650,
        "dead_code_count": 0,
        "near_duplicate_count": 0,
        "idiom_concern_count": 0,
        "has_readme": True,
        "has_changelog": True,
        "has_docs_dir": True,
    })
    history = {
        "window": "12 months ago",
        "files_changed": 50,
        "hotspots": [],
        "change_coupling": [],
        "qualifying_hotspots": 0,
        "code_coupling_pairs": 0,
        "multi_commit_files": 10,
        "single_author_files": 1,
    }

    result = score_report({"summary": full, "history": history})

    assert result["overall"] == 5.0
    assert result["grade"] == "A+"
    assert result["grade_blockers"] == []


def test_unknown_evidence_blocks_the_top_grades() -> None:
    """A structurally-perfect repo with unmeasured aspects cannot take
    A+ on the evidence that happened to be available."""
    result = score(500, 1000)

    assert result["grade"] == "B"
    assert any("full evidence" in blocker for blocker in result["grade_blockers"])


def test_a_single_hard_gate_failure_blocks_the_top_grades() -> None:
    result = score(500, 1000, hard_gate_failures=1)

    assert result["grade"] not in {"A+", "A"}


# ---------------------------------------------------------------------------
# Dimensions are genuinely independent inputs
# ---------------------------------------------------------------------------

def test_dimensions_can_disagree_with_each_other() -> None:
    """The previous five categories were five re-weightings of one
    signal, so they always moved together. These are drawn from
    different measurements and must not."""
    pressures = dimension_pressures(summary(100, 100, duplicate_blocks=500))
    normalized = normalize(pressures)

    assert normalized["duplication"] > 1.0
    assert normalized["file_size"] == 0.0
