"""ADR 001 stage 7: what every consumer says about evidence.

The distinction the report has carried since stage 5 — estimate, range,
evidence completeness, verified grade — only matters if the artifacts a
human or an agent actually reads carry it too. Before this stage the
Markdown, the PR comment, the prompt and the agent instructions all
headlined `score.grade`, which is banded from the evidence floor: on an
incomplete report that is "the worst the evidence allows", presented as
though it were the repository's grade.

Every case starts from `build_report` on a real repository, per the
closure rules. Three evidence shapes are exercised, because they are
genuinely different and were conflated before: complete, `Unknown`
(could not look), and `NotApplicable` (looked, no population).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from maintainability_audit._evidence_view import NOT_VERIFIED
from maintainability_audit.config import load_config
from maintainability_audit.prompts import render_agent_instructions, render_ai_prompt
from maintainability_audit.renderers import render_markdown, render_pr_comment
from maintainability_audit.report import build_report
from maintainability_audit.sarif import report_to_sarif

ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    "PATH": "/usr/bin:/bin",
}


def _source(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
    (root / "app.py").write_text("def ok(value):\n    return value + 1\n", encoding="utf-8")
    (root / "test_app.py").write_text(
        "from app import ok\n\n\ndef test_ok():\n    assert ok(1) == 2\n", encoding="utf-8"
    )


def _commit(root: Path) -> None:
    env = {**ENV, "HOME": str(root)}
    for command in (["git", "init", "-q", "."], ["git", "add", "-A"],
                    ["git", "commit", "-qm", "start"]):
        subprocess.run(command, cwd=root, check=True, capture_output=True, env=env)


@pytest.fixture
def complete_report(tmp_path: Path) -> dict:
    """One commit: every required measurement resolved.

    Ownership is NotApplicable here (no file has three commits), which is
    the point — NotApplicable is complete evidence and must not surface
    as a missing measurement anywhere.
    """
    root = tmp_path / "complete"
    _source(root)
    _commit(root)
    return build_report(root, load_config(None))


@pytest.fixture
def incomplete_report(tmp_path: Path) -> dict:
    """No git at all: history is Unknown, so verification is withheld."""
    root = tmp_path / "incomplete"
    _source(root)
    return build_report(root, load_config(None))


def _all_artifacts(report: dict) -> dict[str, str]:
    return {
        "markdown": render_markdown(report),
        "pr_comment": render_pr_comment(report),
        "ai_prompt": render_ai_prompt(report),
        "agent_instructions": render_agent_instructions(report),
    }


# ---------------------------------------------------------------------------
# Complete evidence
# ---------------------------------------------------------------------------

def test_complete_evidence_shows_the_verified_grade_everywhere(complete_report: dict) -> None:
    score = complete_report["score"]
    assert score["verified_grade"] is not None, "fixture must actually verify"

    for name, text in _all_artifacts(complete_report).items():
        assert score["verified_grade"] in text, f"{name} omits the verified grade"
        assert NOT_VERIFIED not in text, f"{name} claims not verified on a verified report"


def test_complete_evidence_carries_no_warning_language(complete_report: dict) -> None:
    """A clean report should not be decorated with reassurance."""
    for name, text in _all_artifacts(complete_report).items():
        assert "Evidence unavailable" not in text, name
        assert "must not widen the work order" not in text, name


def test_not_applicable_ownership_is_never_called_missing(complete_report: dict) -> None:
    """"Looked, nothing to measure" must not read as "could not look".

    The one-commit fixture has NotApplicable ownership. It is complete
    evidence, so no consumer may list it as an unavailable measurement.
    """
    assert complete_report["score"]["evidence_status"]["status"] == "complete"
    assert complete_report["score"]["evidence_status"]["reasons"] == []

    for name, text in _all_artifacts(complete_report).items():
        assert "single_author_files" not in text, f"{name} reported NotApplicable as missing"


# ---------------------------------------------------------------------------
# Unknown evidence
# ---------------------------------------------------------------------------

def test_unknown_history_says_not_verified_in_every_consumer(incomplete_report: dict) -> None:
    score = incomplete_report["score"]
    assert score["verified_grade"] is None, "fixture must actually withhold"

    for name, text in _all_artifacts(incomplete_report).items():
        assert NOT_VERIFIED in text, f"{name} does not say the grade was withheld"


def test_the_compatibility_grade_is_never_presented_as_authoritative(
    incomplete_report: dict,
) -> None:
    """It stays visible, labelled for what it is.

    Removing it is stage 8. Until then it must not appear as *the* grade
    on a report that issued none — it is banded from the evidence floor,
    so on an incomplete report it means "the worst the evidence allows".
    """
    for name, text in _all_artifacts(incomplete_report).items():
        if "Compatibility grade" in text or "compatibility" in text:
            assert "compatibility" in text.lower(), name
    markdown = render_markdown(incomplete_report)
    assert "Verified grade | Not verified" in markdown
    assert "compatibility, evidence-floor" in markdown


def test_every_reason_reaches_the_reader_with_path_and_provenance(
    incomplete_report: dict,
) -> None:
    reasons = incomplete_report["score"]["evidence_status"]["reasons"]
    assert reasons, "fixture must actually have reasons"

    markdown = render_markdown(incomplete_report)
    prompt = render_ai_prompt(incomplete_report)
    for item in reasons:
        assert item["measurement"] in markdown, item["measurement"]
        assert item["provenance"] in markdown, item["provenance"]
        assert item["measurement"] in prompt, item["measurement"]


def test_the_prompt_forbids_widening_the_work_order(incomplete_report: dict) -> None:
    """Missing evidence is not a defect an agent should refactor toward.

    Without this the agent is told "evidence is incomplete" and does what
    agents do: starts changing code. The measured cost of an unbounded
    instruction is in docs/studies.md.
    """
    prompt = render_ai_prompt(incomplete_report)

    assert "not a code defect" in prompt
    assert "must not widen the work order" in prompt
    assert "fetch-depth" in prompt, "the actionable cause should be named"


# ---------------------------------------------------------------------------
# One missing summary input
# ---------------------------------------------------------------------------

def test_a_single_missing_summary_input_reaches_every_output(complete_report: dict) -> None:
    from maintainability_audit.scoring import score_report

    report = dict(complete_report)
    report["summary"] = {k: v for k, v in report["summary"].items() if k != "test_file_count"}
    report["score"] = score_report(report)

    assert report["score"]["verified_grade"] is None
    for name, text in _all_artifacts(report).items():
        assert NOT_VERIFIED in text, name
    assert "summary.test_file_count" in render_markdown(report)


# ---------------------------------------------------------------------------
# SARIF
# ---------------------------------------------------------------------------

def test_sarif_carries_evidence_at_run_level_and_invents_no_result(
    complete_report: dict, incomplete_report: dict
) -> None:
    """Missing evidence is not a source-code finding.

    Emitting it as a result would place "this clone was shallow" in the
    Security tab beside real defects, which is both wrong and the kind
    of noise that teaches people to ignore the tab.
    """
    complete = report_to_sarif(complete_report)
    incomplete = report_to_sarif(incomplete_report)

    assert len(complete["runs"][0]["results"]) == len(incomplete["runs"][0]["results"]), (
        "incomplete evidence changed the result count"
    )
    properties = incomplete["runs"][0]["properties"]
    assert properties["evidenceStatus"] == "incomplete"
    assert properties["verifiedGrade"] is None
    assert properties["evidenceProfile"] == "default-v1"
    assert len(properties["evidenceReasons"]) == len(
        incomplete_report["score"]["evidence_status"]["reasons"]
    )
    assert all(
        set(item) == {"measurement", "reason", "provenance"}
        for item in properties["evidenceReasons"]
    )
    assert complete["runs"][0]["properties"]["verifiedGrade"] is not None
    for result in incomplete["runs"][0]["results"]:
        assert "evidence" not in json.dumps(result).lower()


def test_sarif_results_are_unchanged_by_the_migration(complete_report: dict) -> None:
    """Rule ids, levels and locations must be exactly as before."""
    run = report_to_sarif(complete_report)["runs"][0]

    for result in run["results"]:
        assert set(result) >= {"ruleId", "level", "message"}
        assert result["ruleId"].startswith("maintainability.")


# ---------------------------------------------------------------------------
# JSON contract and CLI behaviour
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("committed", [True, False], ids=["complete", "incomplete"])
def test_cli_json_carries_the_evidence_contract(tmp_path: Path, committed: bool) -> None:
    root = tmp_path / "cli"
    _source(root)
    if committed:
        _commit(root)

    result = subprocess.run(
        [sys.executable, "-m", "maintainability_audit", "--root", str(root), "--format", "json"],
        capture_output=True, text=True, check=True,
    )
    score = json.loads(result.stdout)["score"]

    status = score["evidence_status"]
    assert set(status) == {"status", "profile", "reasons"}
    assert status["profile"] == "default-v1"
    assert status["status"] == ("complete" if committed else "incomplete")
    assert ("verified_grade" in score) and (
        score["verified_grade"] is not None if committed else score["verified_grade"] is None
    )


@pytest.mark.parametrize("committed", [True, False], ids=["complete", "incomplete"])
def test_fail_on_gate_still_ignores_the_verified_grade(tmp_path: Path, committed: bool) -> None:
    """ADR 002: the gate reads hard findings, never a letter.

    Stage 7 is presentation. A withheld verified grade must not start
    failing builds, or a shallow CI clone would block merges for having
    nothing to measure.
    """
    root = tmp_path / "gate"
    _source(root)
    if committed:
        _commit(root)
    report = build_report(root, load_config(None))
    assert not report["hard_gate_failures"], "fixture must be gate-clean"

    result = subprocess.run(
        [sys.executable, "-m", "maintainability_audit", "--root", str(root), "--fail-on-gate"],
        capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr[-400:]


def test_the_baseline_still_records_fingerprints_only(complete_report: dict, tmp_path: Path) -> None:
    """A deliberate no-op, confirmed rather than assumed.

    `write_baseline` stores a score snapshot nobody reads, and
    `load_baseline` reads only the fingerprint list. Stage 7 does not
    promote that snapshot into a gating contract.
    """
    from maintainability_audit.baseline import load_baseline, write_baseline

    path = tmp_path / "baseline.json"
    write_baseline(str(path), complete_report)
    data = json.loads(path.read_text(encoding="utf-8"))

    assert set(load_baseline(str(path))) == set(data["findings"])
    assert all(isinstance(item, str) for item in data["findings"])
