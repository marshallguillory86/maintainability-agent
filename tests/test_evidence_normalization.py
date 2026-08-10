"""The typed evidence boundary, tested against production reports.

Stage 3 of ADR 001. Every test here starts from a report built by
``build_report`` on a real temporary repository, not from a
hand-assembled summary dictionary. That is deliberate and it is the
ADR's own instruction: six audit rounds were survived by hand-built
fixtures that happened to carry whichever field the scorer needed, and
a fixture cannot demonstrate that the *production* report satisfies a
property.

Hand-built dictionaries do appear below, but only where the case being
tested is a malformed or legacy input that ``build_report`` cannot
produce by construction.

Scoring is not migrated in this slice, so nothing here asserts a score.
What is asserted is that the boundary tells the truth about what
evidence exists.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from maintainability_audit.config import load_config
from maintainability_audit.evidence import (
    REPORT_SCHEMA_VERSION,
    SCHEMA_VERSION_KEY,
    EvidenceValidationError,
    HistoryEvidence,
    Measured,
    NotApplicable,
    SummaryEvidence,
    Unknown,
    UnsupportedReportSchema,
    normalize_report_evidence,
    walk_evidence,
)
from maintainability_audit.report import build_report

ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    "PATH": "/usr/bin:/bin",
}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _commit(root: Path, message: str) -> None:
    env = {**ENV, "HOME": str(root)}
    if not (root / ".git").exists():
        subprocess.run(["git", "init", "-q", "."], cwd=root, check=True, capture_output=True, env=env)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True, env=env)
    subprocess.run(["git", "commit", "-qm", message], cwd=root, check=True, capture_output=True, env=env)


def _tested_repo(root: Path) -> Path:
    _write(root / "README.md", "# Test\n")
    _write(root / "app.py", "def ok():\n    return 1\n")
    _write(root / "test_app.py", "from app import ok\n\n\ndef test_ok():\n    assert ok() == 1\n")
    return root


def _report(root: Path) -> dict:
    return build_report(root, load_config(None))


def test_a_production_report_normalizes_with_every_scoring_input_present(tmp_path: Path) -> None:
    """A complete report loses nothing at the boundary.

    Walks the model rather than checking a list of names, so an input
    added to the typed model later is covered without anyone editing
    this test.
    """
    _tested_repo(tmp_path)
    _commit(tmp_path, "start")

    evidence = normalize_report_evidence(_report(tmp_path))

    unresolved = [path for path, state in walk_evidence(evidence) if isinstance(state, Unknown)]
    assert not unresolved, f"a complete report left evidence unknown: {unresolved}"
    assert evidence.schema_version == REPORT_SCHEMA_VERSION
    assert evidence.history_present is True


def test_the_walker_reaches_every_field_of_the_typed_model(tmp_path: Path) -> None:
    """The recursive helper must not silently skip a nested structure.

    Guards the mechanism the other tests rely on: if ``walk_evidence``
    stopped descending into history, the sweep above would pass while
    checking nothing.
    """
    _tested_repo(tmp_path)
    _commit(tmp_path, "start")

    walked = {path for path, _ in walk_evidence(normalize_report_evidence(_report(tmp_path)))}

    expected = {f"summary.{field.name}" for field in SummaryEvidence.__dataclass_fields__.values()}
    expected |= {f"history.{field.name}" for field in HistoryEvidence.__dataclass_fields__.values()}
    assert walked == expected


def test_measured_zero_stays_measured_zero(tmp_path: Path) -> None:
    """The distinction the whole model exists for.

    A clean repository genuinely has zero risk findings and zero
    duplicate blocks. Those are findings, not absences, and must not
    normalize to the same state as a count that was never taken.
    """
    _tested_repo(tmp_path)
    _commit(tmp_path, "start")
    report = _report(tmp_path)
    assert report["summary"]["risk_findings"] == 0, "fixture must actually measure zero"

    evidence = normalize_report_evidence(report)

    assert evidence.summary.risk_findings == Measured(0, "summary.risk_findings")
    assert isinstance(evidence.summary.duplicate_blocks, Measured)
    assert evidence.summary.duplicate_blocks.value == 0


def test_absent_test_evidence_is_unknown_not_zero(tmp_path: Path) -> None:
    """Withholding a field cannot look like reporting a zero.

    The sixth audit's finding in its typed form: a report with no
    ``test_file_count`` is not a report of no tests. Under the raw
    dictionary these were the same value.
    """
    _tested_repo(tmp_path)
    _commit(tmp_path, "start")
    report = _report(tmp_path)
    del report["summary"]["test_file_count"]

    state = normalize_report_evidence(report).summary.test_file_count

    assert isinstance(state, Unknown)
    assert state.provenance == "summary.test_file_count"
    assert state.reason


def test_absent_history_is_unknown_with_a_reason(tmp_path: Path) -> None:
    """A shallow clone must not read as a quiet repository."""
    _tested_repo(tmp_path)  # no git init: build_report emits history: None
    report = _report(tmp_path)
    assert report["history"] is None, "fixture must actually have no history"

    evidence = normalize_report_evidence(report)

    assert evidence.history_present is False
    states = [state for path, state in walk_evidence(evidence.history)]
    assert states and all(isinstance(state, Unknown) for state in states)
    assert all("no history" in state.reason for state in states)


def test_missing_files_changed_does_not_become_a_measured_zero(tmp_path: Path) -> None:
    """A history block missing one count is not a history of no changes."""
    _tested_repo(tmp_path)
    _commit(tmp_path, "start")
    report = _report(tmp_path)
    del report["history"]["files_changed"]

    evidence = normalize_report_evidence(report)

    assert isinstance(evidence.history.files_changed, Unknown)
    assert evidence.history_present is True, "the block exists; only one count is missing"


def test_missing_single_author_files_does_not_raise(tmp_path: Path) -> None:
    """Direct indexing of optional history crashed once; it must not now."""
    _tested_repo(tmp_path)
    _commit(tmp_path, "start")
    report = _report(tmp_path)
    del report["history"]["single_author_files"]

    evidence = normalize_report_evidence(report)

    assert isinstance(evidence.history.single_author_files, Unknown)


def test_deleting_a_field_never_resolves_it_into_a_better_defined_state(tmp_path: Path) -> None:
    """Absence must not be upgraded to NotApplicable.

    Found while writing these tests, not by an audit. The first version
    marked ``single_author_files`` NotApplicable whenever no file had
    three commits — including when the field had been deleted, so
    removing evidence produced a *more* resolved state than leaving it
    in. NotApplicable is a claim about the population; it can only be
    made about a count the report actually recorded.
    """
    _tested_repo(tmp_path)
    _commit(tmp_path, "start")
    report = _report(tmp_path)
    assert report["history"]["multi_commit_files"] == 0, "the N/A condition must hold for this to bite"
    del report["history"]["single_author_files"]

    state = normalize_report_evidence(report).history.single_author_files

    assert isinstance(state, Unknown), "deleting a field resolved it into NotApplicable"


def test_no_settled_files_is_not_applicable_rather_than_unknown(tmp_path: Path) -> None:
    """"Looked, and there is nothing to measure" is its own state.

    A one-commit repository has no file with three commits, so ownership
    concentration has no population. That is distinct from a shallow
    clone where ownership could not be looked at, and the existing
    scorer already treats the two differently.
    """
    _tested_repo(tmp_path)
    _commit(tmp_path, "start")
    report = _report(tmp_path)
    assert report["history"]["multi_commit_files"] == 0, "fixture must have no settled files"

    evidence = normalize_report_evidence(report)

    assert isinstance(evidence.history.single_author_files, NotApplicable)
    assert isinstance(evidence.history.multi_commit_files, Measured)


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda r: r.update({"summary": []}), "summary"),
        (lambda r: r.update({"history": 7}), "history"),
        (lambda r: r["summary"].update({"files_scanned": -1}), "negative"),
        (lambda r: r["summary"].update({"risk_findings": "many"}), "number"),
        (lambda r: r.pop("summary"), "no summary"),
    ],
)
def test_invalid_structures_raise_the_named_validation_error(tmp_path: Path, mutate, expected: str) -> None:
    """Malformed input fails loudly instead of scoring cleanly.

    Hand-mutated on purpose: ``build_report`` cannot emit these, and the
    boundary's job is to be the place that refuses them.
    """
    _tested_repo(tmp_path)
    _commit(tmp_path, "start")
    report = _report(tmp_path)
    mutate(report)

    with pytest.raises(EvidenceValidationError) as caught:
        normalize_report_evidence(report)

    assert expected in str(caught.value)


def test_an_unsupported_schema_version_fails_clearly(tmp_path: Path) -> None:
    _tested_repo(tmp_path)
    _commit(tmp_path, "start")
    report = _report(tmp_path)
    report[SCHEMA_VERSION_KEY] = REPORT_SCHEMA_VERSION + 1

    with pytest.raises(UnsupportedReportSchema) as caught:
        normalize_report_evidence(report)

    assert str(REPORT_SCHEMA_VERSION + 1) in str(caught.value)


def test_an_unversioned_report_is_refused_rather_than_guessed_at(tmp_path: Path) -> None:
    """No consumer rescores persisted reports, so none is migrated.

    docs/report-contract.md records the inventory this rests on: the
    only persisted artifact read back is the baseline, and it carries
    fingerprint strings, not evidence. Accepting an unversioned report
    would be compatibility for a consumer that does not exist.
    """
    _tested_repo(tmp_path)
    _commit(tmp_path, "start")
    report = _report(tmp_path)
    del report[SCHEMA_VERSION_KEY]

    with pytest.raises(UnsupportedReportSchema):
        normalize_report_evidence(report)


def test_normalizing_does_not_change_the_report_or_its_score(tmp_path: Path) -> None:
    """Shadow mode: the boundary observes, it does not mutate.

    This slice must leave scoring output identical, so the normalizer is
    checked for side effects on the report it reads.
    """
    _tested_repo(tmp_path)
    _commit(tmp_path, "start")
    report = _report(tmp_path)
    before = (dict(report["score"]), dict(report["summary"]), dict(report["history"]))

    normalize_report_evidence(report)

    assert (report["score"], report["summary"], report["history"]) == before
