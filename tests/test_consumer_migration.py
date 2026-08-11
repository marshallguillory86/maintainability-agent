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
from dataclasses import replace
from pathlib import Path

import pytest

from maintainability_audit import _evidence_view as view
from maintainability_audit._evidence_view import NOT_VERIFIED
from maintainability_audit._verification import DEFAULT_V1_REQUIRED
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


PRE_STAGE7_SARIF = Path(__file__).parent / "fixtures" / "pre_stage7_sarif_run.json"


def _findings_repo(root: Path) -> Path:
    """A tree that actually produces SARIF results.

    The anchor is worthless against a clean repository: zero results
    compared with zero results proves nothing, which is what the first
    version of this test did.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# F\n", encoding="utf-8")
    body = "\n".join(f"    step_{i} = {i} * 2" for i in range(120))
    branch = "\n".join(f"    if step_{i} > 10:\n        step_{i} += 1" for i in range(25))
    (root / "big.py").write_text(
        f"def enormous(value):\n{body}\n{branch}\n    return value\n", encoding="utf-8"
    )
    dup = "\n".join(f"    value_{i} = {i}" for i in range(14))
    for name in ("a.py", "b.py", "c.py"):
        (root / name).write_text(
            f"def helper_{name[0]}(value):\n{dup}\n    return value\n", encoding="utf-8"
        )
    (root / "test_a.py").write_text(
        "from a import helper_a\n\n\ndef test_a():\n    assert helper_a(1) == 1\n", encoding="utf-8"
    )
    return root


def test_sarif_results_are_identical_to_the_pre_stage_seven_output(tmp_path: Path) -> None:
    """Every result, rule, level and location, against a real anchor.

    The first version of this test asserted only that required keys
    existed and that rule ids began with "maintainability." — it could
    not have detected a changed level, a moved location or a dropped
    result, while its name claimed otherwise. An audit called that out.

    `fixtures/pre_stage7_sarif_run.json` was captured by running commit
    91430f3 — the last commit before consumer migration — against the
    tree `_findings_repo` builds.
    """
    expected = json.loads(PRE_STAGE7_SARIF.read_text(encoding="utf-8"))
    assert expected["results"], "the anchor must contain real findings"

    run = report_to_sarif(build_report(_findings_repo(tmp_path / "findings"), load_config(None)))["runs"][0]

    assert run["results"] == expected["results"]
    assert run["tool"]["driver"]["rules"] == expected["rules"]


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


@pytest.mark.parametrize("path", sorted(DEFAULT_V1_REQUIRED))
def test_a_collapsed_range_never_claims_complete_evidence(
    complete_report: dict, path: str
) -> None:
    """Rounding can collapse the bounds; it cannot verify the evidence.

    Swept over every required measurement rather than the one an audit
    demonstrated. Concealing a lightly-weighted input can leave the
    endpoints coincident at one decimal while the verified grade is
    withheld — `[4.9, 4.9]` was being rendered as "no unmeasured
    evidence" on exactly such a report. Completeness is a property of
    the typed evidence, never of two numbers that happen to match.
    """
    from maintainability_audit.evidence import Unknown, normalize_report_evidence
    from maintainability_audit.scoring import score_evidence

    evidence = normalize_report_evidence(complete_report)
    section, _, field = path.partition(".")
    node = getattr(evidence, section)
    hidden = replace(evidence, **{section: replace(node, **{field: Unknown("swept", path)})})

    score = score_evidence(hidden)
    rendered = view.score_range(score)

    assert score["verified_grade"] is None, f"{path} should withhold the grade"
    if score["overall_range"][0] == score["overall_range"][1]:
        assert "no unmeasured evidence" not in rendered, (
            f"concealing {path} collapsed the range and claimed completeness: {rendered}"
        )
        assert "still incomplete" in rendered


# ---------------------------------------------------------------------------
# The agent-instruction contract, and cause-specific guidance.
#
# Both were implemented and then described as covered when they were not:
# the consumer assertions above only check that a verified-grade string
# appears, and a regression restoring blanket clone-depth advice would
# have passed every test in this file.
# ---------------------------------------------------------------------------

def test_agent_instructions_carry_the_whole_evidence_contract(incomplete_report: dict) -> None:
    """Not just the grade value — the range, profile, paths and the rule."""
    score = incomplete_report["score"]
    instructions = render_agent_instructions(incomplete_report)

    assert NOT_VERIFIED in instructions
    assert view.score_range(score) in instructions
    assert score["evidence_status"]["profile"] in instructions
    for item in score["evidence_status"]["reasons"]:
        assert item["measurement"] in instructions, item["measurement"]
        assert item["provenance"] in instructions, item["provenance"]
    assert "not** a code defect" in instructions
    assert "do not refactor or widen scope" in instructions


def test_complete_agent_instructions_carry_no_evidence_guard(complete_report: dict) -> None:
    instructions = render_agent_instructions(complete_report)

    assert complete_report["score"]["verified_grade"] in instructions
    assert "do not refactor or widen scope" not in instructions


def _hint_for(report: dict) -> str:
    return view._restore_hint(report["score"])


def test_history_only_gaps_get_clone_depth_advice(incomplete_report: dict) -> None:
    sections = {r["measurement"].split(".")[0] for r in view.reasons(incomplete_report["score"])}
    assert sections == {"history"}, "fixture must be history-only"

    assert "fetch-depth" in _hint_for(incomplete_report)


def test_summary_only_gaps_do_not_get_clone_depth_advice(complete_report: dict) -> None:
    """The defect an audit found: a missing scanner count told to fix git."""
    from maintainability_audit.scoring import score_report

    report = dict(complete_report)
    report["summary"] = {k: v for k, v in report["summary"].items() if k != "test_file_count"}
    report["score"] = score_report(report)
    sections = {r["measurement"].split(".")[0] for r in view.reasons(report["score"])}
    assert sections == {"summary"}, "fixture must be summary-only"

    hint = _hint_for(report)
    assert "fetch-depth" not in hint, "summary gaps must not blame clone depth"
    assert "scanner outputs" in hint
    assert "fetch-depth" not in render_ai_prompt(report)


def test_mixed_gaps_name_more_than_one_producer(complete_report: dict) -> None:
    """The branch nothing executed: gaps in both summary and history."""
    from maintainability_audit.scoring import score_report

    report = dict(complete_report)
    report["summary"] = {k: v for k, v in report["summary"].items() if k != "test_file_count"}
    report["history"] = {k: v for k, v in report["history"].items() if k != "files_changed"}
    report["score"] = score_report(report)
    sections = {r["measurement"].split(".")[0] for r in view.reasons(report["score"])}
    assert sections == {"summary", "history"}, f"fixture must be mixed, got {sections}"

    hint = _hint_for(report)
    assert "more than one producer" in hint
    assert "fetch-depth" not in hint, "mixed causes must not single out clone depth"
