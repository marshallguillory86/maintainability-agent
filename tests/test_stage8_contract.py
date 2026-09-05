"""ADR 001 stage 8: the version-2 public score contract.

Two things are asserted here and nowhere else. That the contract *is*
version 2 — canonical field names present, the four compatibility fields
gone, version 1 rejected rather than migrated. And that renaming them
moved no value: every parity check reads the anchors captured from
commit a6b3c0f in ``fixtures/stage8_anchors/``, never a number chosen by
whoever wrote the test.

The anchors cover the four shapes that behave differently: complete,
complete-with-NotApplicable, incomplete from unavailable history, and
incomplete from a missing summary measurement.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from _git_path import GIT_PATH

from maintainability_audit.config import load_config
from maintainability_audit.evidence import REPORT_SCHEMA_VERSION, SCHEMA_VERSION_KEY, UnsupportedReportSchema
from maintainability_audit.report import build_report
from maintainability_audit.scoring import score_report

ANCHORS = Path(__file__).parent / "fixtures" / "stage8_anchors"

REMOVED = ("overall", "overall_range", "grade", "grade_blockers")
CANONICAL = (
    "standard", "maintainability_estimate", "maintainability_range", "evidence_status",
    "verified_grade", "verified_grade_blockers", "categories", "aspects", "rubric",
    "dimensions", "worst_dimension", "reference", "analyzer_scored_dimensions",
)
# Pure renames: same value, new key.
RENAMED = {
    "overall": "maintainability_estimate",
    "overall_range": "maintainability_range",
}
# grade_blockers -> verified_grade_blockers is *not* a pure rename. When
# no grade is issued the list is deliberately emptied, because the old
# one explained a floor-banded grade that no longer exists and its
# content ("graded on the evidence floor…") is an evidence statement,
# not a quality one. Those explanations live in evidence_status.reasons.

ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    "PATH": GIT_PATH,
}


def _tree(root: Path, commits: int) -> Path:
    """The exact tree each anchor was captured from."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
    (root / "CHANGELOG.md").write_text("## 0.1.0\n", encoding="utf-8")
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "i.md").write_text("# D\n", encoding="utf-8")
    (root / "app.py").write_text("def ok(value):\n    return value + 1\n", encoding="utf-8")
    (root / "test_app.py").write_text(
        "from app import ok\n\n\ndef test_ok():\n    assert ok(1) == 2\n", encoding="utf-8"
    )
    env = {**ENV, "HOME": str(root)}
    for index in range(commits):
        if index == 0:
            subprocess.run(["git", "init", "-q", "."], cwd=root, check=True, capture_output=True, env=env)
        (root / "app.py").write_text(f"def ok(value):\n    return value + {index + 1}\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True, env=env)
        subprocess.run(
            ["git", "commit", "-qm", f"c{index}"], cwd=root, check=True, capture_output=True,
            env={**env, "GIT_AUTHOR_NAME": f"a{index}", "GIT_AUTHOR_EMAIL": f"a{index}@t"},
        )
    return root


def _live(name: str, tmp_path: Path) -> dict:
    commits = {"not_applicable": 1, "complete": 4, "unknown_history": 0, "missing_summary": 1}[name]
    report = build_report(_tree(tmp_path / name, commits), load_config(None))
    if name == "missing_summary":
        del report["summary"]["test_file_count"]
        report["score"] = score_report(report)
    return report


def _anchor(name: str) -> dict:
    return json.loads((ANCHORS / f"{name}.json").read_text(encoding="utf-8"))


# The two Class 5 deltas to a pre-Class-5 rubric, applied to the frozen
# anchor so the test states the intended new values rather than reading
# them back out of the code it is checking. `test_aspect_coverage` and
# the testability renormalization test guard the weights themselves.
CLASS5_TESTABILITY = {
    "test_presence": 0.40, "declaration_size": 0.24,
    "policy_gates": 0.16, "test_effectiveness": 0.20,
}


def _rubric_after_class5(rubric: dict) -> dict:
    return {
        **rubric,
        "category_aspects": {**rubric["category_aspects"], "testability": CLASS5_TESTABILITY},
        "unscored": {name: reason for name, reason in rubric["unscored"].items()
                     if name != "test_effectiveness"},
    }


ANCHOR_NAMES = ("complete", "not_applicable", "unknown_history", "missing_summary")


@pytest.mark.parametrize("name", ANCHOR_NAMES)
def test_the_public_contract_is_version_two(name: str, tmp_path: Path) -> None:
    score = _live(name, tmp_path)["score"]

    assert set(CANONICAL) == set(score), sorted(set(CANONICAL) ^ set(score))
    for removed in REMOVED:
        assert removed not in score, f"{removed} survived the migration"


@pytest.mark.parametrize("name", ANCHOR_NAMES)
def test_renaming_moved_no_value(name: str, tmp_path: Path) -> None:
    """Every field compared against the captured a6b3c0f output.

    Values come from the anchor, never from this file: a test that
    hard-codes what it expects cannot distinguish "unchanged" from
    "changed to the number I typed".
    """
    anchor = _anchor(name)
    score = _live(name, tmp_path)["score"]

    for old, new in RENAMED.items():
        assert score[new] == anchor[old], f"{old} -> {new} moved"
    if score["verified_grade"] is not None:
        assert score["verified_grade_blockers"] == anchor["grade_blockers"], (
            "for an issued grade the blockers are a pure rename"
        )
    else:
        assert score["verified_grade_blockers"] == []
        assert anchor["grade_blockers"], (
            "the anchor should have carried floor-grade blockers that stage 8 retires"
        )
    for unchanged in ("standard", "categories", "dimensions",
                      "worst_dimension", "evidence_status", "verified_grade"):
        assert score[unchanged] == anchor[unchanged], unchanged
    # `reference` has gained three fields since a6b3c0f, every one a
    # disclosure rather than a change of meaning. The multiple a report
    # prints is unchanged; what is new is that it says what it is a
    # multiple *of*, and now also what it is *not* a multiple of.
    #
    # `corpus_languages` and `corpus_note` came first: the corpus behind
    # "1.0x = the median mature-OSS repo" was 40 repositories of Python,
    # TypeScript and JavaScript while the scanner read seven languages.
    # `unanchored_languages` followed for the same reason one release
    # later — Swift and COBOL ship parsed and outside the corpus, and the
    # note claimed "every language this scanner parses" for three
    # releases after that stopped being true (Grok, 2026-09-04).
    # Stated as a delta on the frozen anchor, the way Class 5's aspect and
    # rubric changes are.
    assert score["reference"] == {
        **anchor["reference"],
        "corpus_languages": [
            "Python", "TypeScript", "JavaScript", "Java", "C", "C++", "C#", "Fortran",
        ],
        "unanchored_languages": score["reference"]["unanchored_languages"],
        "corpus_note": score["reference"]["corpus_note"],
    }, "reference gained only the corpus disclosure"
    assert "docs/standard.md" in score["reference"]["corpus_note"]
    # aspects gained exactly one field after a6b3c0f: test_effectiveness,
    # the Class 5 opt-in coverage aspect. None of these fixtures opts a
    # suite in, so it is NotApplicable — present and None — and every
    # aspect the anchor recorded still matches it value for value.
    assert score["aspects"]["test_effectiveness"] is None
    assert {name: value for name, value in score["aspects"].items()
            if name != "test_effectiveness"} == anchor["aspects"]
    # The published rubric changed with Class 5 in exactly two ways:
    # test_effectiveness left `unscored` to become a scored aspect, and
    # testability was reweighted to make room for it (the other three
    # scaled by 0.8 so the category renormalizes to its old value while
    # coverage is NotApplicable). Stated as deltas on the frozen anchor.
    assert score["rubric"] == _rubric_after_class5(anchor["rubric"])


@pytest.mark.parametrize("name", ANCHOR_NAMES)
def test_blockers_explain_an_issued_grade_only(name: str, tmp_path: Path) -> None:
    score = _live(name, tmp_path)["score"]

    if score["verified_grade"] is None:
        assert score["verified_grade_blockers"] == []
        assert score["evidence_status"]["status"] == "incomplete"
        assert score["evidence_status"]["reasons"], "the gap must be named somewhere"


def test_the_report_stamps_the_current_schema_version(tmp_path: Path) -> None:
    report = _live("complete", tmp_path)

    assert report[SCHEMA_VERSION_KEY] == 3 == REPORT_SCHEMA_VERSION


@pytest.mark.parametrize("version", [1, 2, None, 99, "3"],
                         ids=["v1", "v2", "unversioned", "v99", "string"])
def test_only_the_current_version_is_accepted(version: object, tmp_path: Path) -> None:
    """Version 1 is rejected, not migrated.

    Deliberate: the consumer inventory established that nothing rescores
    a persisted report, so a migration would exist for no caller.
    """
    report = _live("complete", tmp_path)
    if version is None:
        del report[SCHEMA_VERSION_KEY]
    else:
        report[SCHEMA_VERSION_KEY] = version

    with pytest.raises(UnsupportedReportSchema):
        score_report(report)


def test_cli_json_carries_the_current_contract(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "maintainability_audit", "--root", str(_tree(tmp_path / "cli", 1)),
         "--format", "json"],
        capture_output=True, text=True, check=True,
    )
    report = json.loads(result.stdout)

    assert report[SCHEMA_VERSION_KEY] == REPORT_SCHEMA_VERSION
    assert set(CANONICAL) == set(report["score"])
    for removed in REMOVED:
        assert removed not in report["score"]
