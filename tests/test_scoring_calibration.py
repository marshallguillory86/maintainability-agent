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

from maintainability_audit._calibration import DIMENSION_REFERENCES, WARN_WEIGHT
from maintainability_audit.evidence import (
    REPORT_SCHEMA_VERSION,
    SCHEMA_VERSION_KEY,
    normalize_report_evidence,
)
from maintainability_audit.scoring import dimension_pressures, grade_for, normalize
from maintainability_audit.scoring import score_report as _score_report


def score_report(report: dict) -> dict:
    """Stamp the schema version, then score.

    Production reports carry ``schema_version`` because ``build_report``
    stamps it, and since ADR 001 stage 4 the scorer validates it at the
    normalization boundary rather than trusting a raw dictionary. The
    hand-built fixtures below predate that and would otherwise be
    rejected. This shim makes them *conform* to the production contract;
    it does not bypass it — the version gate itself is tested against
    real reports in ``test_evidence_normalization.py``.
    """
    return _score_report({SCHEMA_VERSION_KEY: REPORT_SCHEMA_VERSION, **report})


def _evidence_of(raw_summary: dict) -> object:
    """The typed SummaryEvidence a raw fixture summary normalizes to.

    Since ADR 001 stage 4 the pressure layer takes evidence states, not
    a dictionary, so a test calling it directly goes through the same
    boundary the scorer does.
    """
    payload = {SCHEMA_VERSION_KEY: REPORT_SCHEMA_VERSION, "summary": raw_summary}
    return normalize_report_evidence(payload).summary


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
        # A fixture wanting a grade claims a full read; Unknown withholds one.
        "unread_source_files": 0,
        "read_source_files": files,
        "undetected_declaration_files": 0,
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

    assert small["maintainability_estimate"] == large["maintainability_estimate"]


def test_a_big_clean_repo_outscores_a_small_dirty_one() -> None:
    big_clean = score(5000, 10000, file_failures=50)
    small_dirty = score(40, 80, file_failures=20)

    assert big_clean["maintainability_estimate"] > small_dirty["maintainability_estimate"]


# ---------------------------------------------------------------------------
# No saturation: the scale must keep resolving all the way down
# ---------------------------------------------------------------------------

def test_two_bad_repos_remain_distinguishable() -> None:
    """The old curve pinned everything past ~3% of files to the floor,
    so 'bad' and 'catastrophic' were the same number."""
    bad = score(1000, 2000, file_failures=100, function_failures=200)
    worse = score(1000, 2000, file_failures=400, function_failures=800)

    assert bad["maintainability_estimate"] > worse["maintainability_estimate"]
    assert worse["maintainability_estimate"] > 0.0


def test_score_never_leaves_the_scale() -> None:
    catastrophic = score(
        100, 100, file_failures=100, function_failures=100, duplicate_blocks=9999, risk_findings=9999,
        hard_gate_failures=50,
    )

    assert 0.0 <= catastrophic["maintainability_estimate"] <= 5.0


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

    assert 3.5 <= result["maintainability_estimate"] <= 4.5, result["maintainability_estimate"]


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

    assert result["maintainability_estimate"] == 5.0
    assert result["verified_grade"] == "A+"
    assert result["verified_grade_blockers"] == []


def test_unknown_evidence_blocks_the_top_grades() -> None:
    """A structurally-perfect repo with unmeasured aspects cannot take
    A+ on the evidence that happened to be available.

    The grade bands the evidence *floor*, so missing history costs more
    than a one-step demotion: the point estimate still reads high, and
    the gap between them is exactly what the repo has not shown.
    """
    result = score(500, 1000)

    # Stage 8: an incomplete report issues no grade at all, which is a
    # stronger statement than "not an A". The compatibility letter this
    # used to read is gone.
    assert result["verified_grade"] is None
    assert result["maintainability_estimate"] > result["maintainability_range"][0]
    # Stage 8: an unissued grade has no blockers. What is missing is
    # named in evidence_status.reasons instead, so an evidence gap can no
    # longer read as a quality demotion.
    assert result["verified_grade_blockers"] == []
    assert result["evidence_status"]["status"] == "incomplete"
    assert result["evidence_status"]["reasons"], "the gap must still be named"


def test_a_single_hard_gate_failure_blocks_the_top_grades() -> None:
    result = score(500, 1000, hard_gate_failures=1)

    assert result["verified_grade"] is None


# ---------------------------------------------------------------------------
# Dimensions are genuinely independent inputs
# ---------------------------------------------------------------------------

def test_dimensions_can_disagree_with_each_other() -> None:
    """The previous five categories were five re-weightings of one
    signal, so they always moved together. These are drawn from
    different measurements and must not."""
    pressures = dimension_pressures(_evidence_of(summary(100, 100, duplicate_blocks=500)))
    normalized = normalize(pressures)

    assert normalized["duplication"] > 1.0
    assert normalized["file_size"] == 0.0


# ---------------------------------------------------------------------------
# Unknown-evidence pricing: what concealment can and cannot buy
# ---------------------------------------------------------------------------

def _evidence_summary(**overrides: object) -> dict:
    full = summary(500, 1000)
    full.update({
        "test_file_count": 100, "production_declarations_scanned": 650,
        "dead_code_count": 0, "near_duplicate_count": 0, "idiom_concern_count": 0,
        "has_readme": True, "has_changelog": True, "has_docs_dir": True,
    })
    full.update(overrides)
    return full


def _history(**overrides) -> dict:
    base = {
        "window": "12 months ago", "files_changed": 50, "hotspots": [],
        "change_coupling": [], "qualifying_hotspots": 0, "code_coupling_pairs": 0,
        "multi_commit_files": 10, "single_author_files": 1,
    }
    base.update(overrides)
    return base


def test_concealment_ordering_and_its_stated_limit() -> None:
    """Unknowns price at the anchor, so the shallow point estimate sits
    BETWEEN worst-band and clean history — hiding evidence never buys
    the clean score, but a repo whose true history is worse than the
    anchor still gains by hiding it. That residual gain is a documented
    property of any single-value imputation, not a closed exploit; the
    overall_range below is what makes it visible."""
    worst = _history(qualifying_hotspots=20, code_coupling_pairs=20, single_author_files=10)

    clean_score = score_report({"summary": _evidence_summary(), "history": _history()})
    shallow_score = score_report({"summary": _evidence_summary()})
    worst_score = score_report({"summary": _evidence_summary(), "history": worst})

    assert worst_score["maintainability_estimate"] < shallow_score["maintainability_estimate"] <= clean_score["maintainability_estimate"]
    # The residual concealment gain exists and is bounded by
    # (clean - worst); pin it so it cannot silently grow.
    shallow_gain = shallow_score['maintainability_estimate'] - worst_score['maintainability_estimate']
    clean_gain = clean_score['maintainability_estimate'] - worst_score['maintainability_estimate']
    assert shallow_gain <= clean_gain


def test_overall_range_collapses_only_under_full_evidence() -> None:
    """The interval is the honest companion to imputation: measured
    everything -> zero width; anything hidden -> visible width."""
    full = score_report({"summary": _evidence_summary(), "history": _history()})
    shallow = score_report({"summary": _evidence_summary()})

    assert full["maintainability_range"][0] == full["maintainability_range"][1] == full["maintainability_estimate"]
    low, high = shallow["maintainability_range"]
    assert low < shallow["maintainability_estimate"] < high, "hidden evidence must widen the interval"
    assert high - low >= 0.5, "three hidden aspects cannot cost less than half a grade of width"


def test_corpus_median_rolls_up_to_exactly_four_through_the_rounded_path() -> None:
    """The anchor claim, at full strength: the derivation now rounds
    categories exactly as score_report ships them, and c sits mid-plateau
    where the corpus median is 4.0 -- not 3.9-something "close enough"."""
    import json
    from pathlib import Path
    from statistics import median as _median

    from maintainability_audit._calibration import CALIBRATION_C, DIMENSION_REFERENCES
    from maintainability_audit._derive import _corpus_overall

    measurements = json.loads(
        (Path(__file__).resolve().parents[1] / "tools/calibration/measurements.json").read_text()
    )["measurements"]
    # The *shipped* references, not freshly derived ones. `score_report`
    # reads the shipped table, so deriving a fresh one here hands the two
    # paths different inputs and the comparison stops meaning anything —
    # it reported angular and anime disagreeing when the only difference
    # was which reference table each side used. Both must start from
    # identical inputs, which is this test's whole premise.
    references = DIMENSION_REFERENCES

    values = [_corpus_overall(entry, references, CALIBRATION_C) for entry in measurements]

    assert _median(values) == 4.0


def test_derivation_matches_live_score_report_repo_by_repo() -> None:
    """The anchor is derived through the *shipped* scorer, per repo.

    The previous version of this claim was checked only at the median,
    and an audit found corpus member ``tabby`` deriving 3.9 while
    ``score_report`` gave it 3.8 — the derivation skipped the untested
    testability cap. A median that survives a per-repo discrepancy is
    luck, so the comparison is now made repo by repo, from the public
    entry point, with the derivation given no special path.
    """
    import json
    from pathlib import Path

    from maintainability_audit._calibration import CALIBRATION_C, DIMENSION_REFERENCES
    from maintainability_audit._derive import _corpus_overall

    measurements = json.loads(
        (Path(__file__).resolve().parents[1] / "tools/calibration/measurements.json").read_text()
    )["measurements"]
    # The *shipped* references, not freshly derived ones. `score_report`
    # reads the shipped table, so deriving a fresh one here hands the two
    # paths different inputs and the comparison stops meaning anything —
    # it reported angular and anime disagreeing when the only difference
    # was which reference table each side used. Both must start from
    # identical inputs, which is this test's whole premise.
    references = DIMENSION_REFERENCES

    mismatches = []
    for entry in measurements:
        summary, matched = _matched_pair(entry)
        derived = _corpus_overall(matched, references, CALIBRATION_C)
        live = score_report({"summary": summary})["maintainability_estimate"]
        if derived != live:
            mismatches.append(f"{entry['repo']}: derived {derived} vs live {live}")

    assert not mismatches, "derivation and score_report disagree:\n" + "\n".join(mismatches)


def _matched_pair(entry: dict) -> tuple[dict, dict]:
    """A summary and an entry that describe exactly the same repository.

    The old version back-solved fractional counts from the stored rates
    so the live pressures would equal them. Cross-field and whole-number
    validation now reject that summary — correctly: it described a
    repository with 25.1 failing files and more production warnings than
    total warnings.

    So the direction is reversed. Build a *valid* integer summary first,
    measure its pressures with the shipped function, and hand those same
    pressures to the derivation. Both paths then start from identical
    inputs, which is what makes a disagreement meaningful rather than a
    rounding artifact.
    """
    files, decls = entry["files"], max(1, entry["declarations"])
    dims, recorded = entry["dimensions"], dict(entry.get("evidence", {}))
    prod_file_warn = recorded.get("production_file_warnings", 0)
    prod_func_warn = recorded.get("production_function_warnings", 0)
    summary = dict(recorded)
    summary.update({
        "files_scanned": files,
        "declarations_scanned": decls,
        "file_warnings": prod_file_warn,
        "function_warnings": prod_func_warn,
        "file_failures": max(
            recorded.get("production_file_failures", 0),
            round(dims["file_size"] * files - WARN_WEIGHT * prod_file_warn),
        ),
        "function_failures": max(
            recorded.get("production_function_failures", 0),
            round(dims["declarations"] * decls - WARN_WEIGHT * prod_func_warn),
        ),
        "duplicate_blocks": round(dims["duplication"] * files),
        "risk_findings": round(dims["risk"] * files),
        "hard_gate_failures": max(
            recorded.get("production_hard_gate_failures", 0), round(dims["gates"] / 0.05)
        ),
    })
    summary.setdefault("production_files_scanned", files)
    summary.setdefault("production_declarations_scanned", decls)
    measured_dims = dimension_pressures(_evidence_of(summary))
    matched_entry = {
        "repo": entry["repo"],
        "files": files,
        "declarations": decls,
        "dimensions": measured_dims,
        # Explicitly null, not absent. The live side of this comparison is
        # `score_report` with no `ExternalPressures`, so the matched entry
        # is a built-in-only reading — which is a measured fact about this
        # pair, while a missing key means the row predates
        # `--with-analyzers` and the derivation refuses it.
        "analyzer_production_dimensions": None,
        "evidence": {key: summary[key] for key in recorded},
    }
    return summary, matched_entry

# ---------------------------------------------------------------------------
