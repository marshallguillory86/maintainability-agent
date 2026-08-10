"""ADR 001 stage 5: evidence sufficiency, separate from quality.

Contract tests, not the recursive state-space suite — that is stage 6
and is deliberately not attempted here. What these pin is the published
behaviour of two new fields and, just as importantly, that **nothing
else moved**: the compatibility score, the CLI's exit code and every
non-JSON artifact must be identical to what they were before
verification metadata existed.

Every case starts from a report `build_report` produced, per ADR 001 §6
and the closure rules: a hand-built summary carries whichever fields the
author remembered, and cannot show that a real report satisfies a
property.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_evidence_normalization import _commit, _report, _tested_repo

from maintainability_audit._verification import DEFAULT_PROFILE, verification
from maintainability_audit.config import load_config
from maintainability_audit.evidence import (
    EvidenceValidationError,
    Measured,
    NotApplicable,
    UnsupportedReportSchema,
    normalize_report_evidence,
)
from maintainability_audit.prompts import render_agent_instructions, render_ai_prompt
from maintainability_audit.renderers import render_markdown, render_pr_comment
from maintainability_audit.report import build_report
from maintainability_audit.sarif import report_to_sarif
from maintainability_audit.scoring import score_report

COMPATIBILITY_FIELDS = (
    "overall", "overall_range", "grade", "grade_blockers",
    "categories", "aspects", "dimensions", "rubric", "reference", "worst_dimension", "standard",
)


def _complete(tmp_path: Path) -> dict:
    _tested_repo(tmp_path)
    _commit(tmp_path, "start")
    return _report(tmp_path)


def _shallow(tmp_path: Path) -> dict:
    _tested_repo(tmp_path)  # never committed: build_report emits history None
    return _report(tmp_path)


def test_complete_evidence_verifies_and_agrees_with_the_compatibility_grade(tmp_path: Path) -> None:
    score = _complete(tmp_path)["score"]

    assert score["evidence_status"]["status"] == "complete"
    assert score["evidence_status"]["profile"] == DEFAULT_PROFILE
    assert score["evidence_status"]["reasons"] == []
    assert score["verified_grade"] == score["grade"]


def test_a_report_without_history_is_incomplete_and_names_what_is_missing(tmp_path: Path) -> None:
    """The shallow-clone case, which is the common one in CI.

    The compatibility grade still exists and still comes from the
    evidence floor; the verified grade is withheld rather than being
    reported as a bad letter, which is the distinction ADR 001 §1 draws.
    """
    score = _shallow(tmp_path)["score"]

    assert score["evidence_status"]["status"] == "incomplete"
    assert score["verified_grade"] is None
    named = {reason["measurement"] for reason in score["evidence_status"]["reasons"]}
    assert named == {
        "history.code_coupling_pairs", "history.files_changed", "history.multi_commit_files",
        "history.qualifying_hotspots", "history.single_author_files",
    }
    assert all(reason["reason"] and reason["provenance"] for reason in score["evidence_status"]["reasons"])
    assert score["grade"], "the compatibility grade must still be issued"


def test_one_unknown_summary_measurement_withholds_the_verified_grade(tmp_path: Path) -> None:
    report = _complete(tmp_path)
    del report["summary"]["test_file_count"]

    score = score_report(report)

    assert score["evidence_status"]["status"] == "incomplete"
    assert score["verified_grade"] is None
    assert [reason["measurement"] for reason in score["evidence_status"]["reasons"]] == [
        "summary.test_file_count"
    ]


def test_measured_zero_is_complete_evidence(tmp_path: Path) -> None:
    """The distinction the whole evidence model exists for.

    A clean repository genuinely measures zero risk findings. Treating
    that as missing would withhold verification from exactly the
    repositories that earned it.
    """
    report = _complete(tmp_path)
    assert report["summary"]["risk_findings"] == 0, "fixture must actually measure zero"
    evidence = normalize_report_evidence(report)
    assert isinstance(evidence.summary.risk_findings, Measured)

    assert report["score"]["evidence_status"]["status"] == "complete"
    assert report["score"]["verified_grade"] is not None


def test_not_applicable_is_complete_evidence(tmp_path: Path) -> None:
    """"Looked, and there is nothing to measure" does not block a grade.

    A one-commit repository has no file with three commits, so ownership
    concentration has no population. That is resolved evidence, not a
    gap, and the fixture below relies on it being present.
    """
    report = _complete(tmp_path)
    evidence = normalize_report_evidence(report)
    assert isinstance(evidence.history.single_author_files, NotApplicable), (
        "fixture must actually exercise NotApplicable"
    )

    result = verification(evidence, "A")

    assert result["evidence_status"]["status"] == "complete"
    assert result["verified_grade"] == "A"


def test_reason_order_is_deterministic(tmp_path: Path) -> None:
    report = _shallow(tmp_path)

    orders = [
        [reason["measurement"] for reason in score_report(report)["evidence_status"]["reasons"]]
        for _ in range(3)
    ]

    assert orders[0] == orders[1] == orders[2] == sorted(orders[0])


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda r: r["summary"].update({"risk_findings": -1}), EvidenceValidationError),
        (lambda r: r["summary"].update({"files_scanned": 1.5}), EvidenceValidationError),
        (lambda r: r.update({"schema_version": 99}), UnsupportedReportSchema),
    ],
)
def test_invalid_evidence_still_raises_rather_than_scoring(tmp_path: Path, mutate, expected) -> None:
    """Invalid is not a third status.

    ADR 001 §3 requires invalid combinations to fail validation. A
    serialized ``status: invalid`` document would let a malformed report
    flow onward carrying numbers nobody should trust.
    """
    report = _complete(tmp_path)
    mutate(report)

    with pytest.raises(expected):
        score_report(report)


def test_the_compatibility_score_is_untouched_by_verification(tmp_path: Path) -> None:
    """Stage 5 adds fields; it moves nothing.

    Compares the shipped score against the same rollup with the
    verification fields stripped, for both complete and incomplete
    evidence — the incomplete case matters most, since that is where a
    careless implementation would let a withheld grade leak into the
    compatibility one.
    """
    for report in (_complete(tmp_path / "full"), _shallow(tmp_path / "shallow")):
        score = report["score"]
        assert set(COMPATIBILITY_FIELDS) <= set(score)
        recomputed = score_report(report)
        for field in COMPATIBILITY_FIELDS:
            assert score[field] == recomputed[field], field
        assert score["grade_blockers"] == recomputed["grade_blockers"]


def test_rendered_artifacts_do_not_mention_the_new_fields(tmp_path: Path) -> None:
    """Consumer migration is stage 7; the artifacts must not move yet."""
    for report in (_complete(tmp_path / "full"), _shallow(tmp_path / "shallow")):
        rendered = "\n".join((
            render_markdown(report),
            render_pr_comment(report),
            render_ai_prompt(report),
            render_agent_instructions(report),
            json.dumps(report_to_sarif(report)),
        ))
        assert "verified_grade" not in rendered
        assert "evidence_status" not in rendered
        assert "default-v1" not in rendered


@pytest.mark.parametrize("committed", [True, False], ids=["complete", "incomplete"])
def test_fail_on_gate_exit_code_is_unchanged_by_evidence_completeness(
    tmp_path: Path, committed: bool
) -> None:
    """`--fail-on-gate` depends on hard-gate findings and nothing else.

    This is the invariant ADR 002 was rejected for assuming otherwise:
    the flag never consumed the grade, so a withheld verified grade must
    not start making builds fail.
    """
    _tested_repo(tmp_path)
    if committed:
        _commit(tmp_path, "start")
    report = build_report(tmp_path, load_config(None))
    assert not report["hard_gate_failures"], "fixture must be gate-clean"

    result = subprocess.run(
        [sys.executable, "-m", "maintainability_audit", "--root", str(tmp_path), "--fail-on-gate"],
        capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr[-400:]
