"""The producer-derived invariant inventory, walked rather than sampled.

Split from ``test_evidence_normalization`` when that file crossed the
500-line ceiling this project enforces on everyone else — the tool
failed its own build on it, which is the gate doing its job on its
author for the fourth time this week.

These tests iterate the relation tables in ``evidence.py`` instead of
naming cases, so a relation added there is exercised the day it is
added. Two audits closed "the demonstrated examples" here and called
the class closed; the tables are the class.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from test_evidence_normalization import _commit, _report, _tested_repo

from maintainability_audit.evidence import (
    HISTORY_SUBSETS,
    SUMMARY_SUBSETS,
    SUMMARY_SUMS,
    EvidenceValidationError,
    SummaryEvidence,
    Unknown,
    normalize_report_evidence,
)

# ---------------------------------------------------------------------------
# The invariant *class*, not the examples an audit happened to name.
# ---------------------------------------------------------------------------

def _valid_report(tmp_path: Path) -> dict:
    _tested_repo(tmp_path)
    _commit(tmp_path, "start")
    report = _report(tmp_path)
    assert report["history"], "fixture must carry history for the history relations"
    return report


@pytest.mark.parametrize("part, whole", SUMMARY_SUBSETS, ids=lambda v: str(v))
def test_every_declared_summary_subset_is_enforced(tmp_path: Path, part: str, whole: str) -> None:
    """Iterates the table, so a relation added to it is tested that day.

    Two rounds of this audit added checks for the violations that had
    been demonstrated and then described the class as closed. The table
    in ``evidence.py`` is the class; this walks it.
    """
    report = _valid_report(tmp_path)
    report["summary"][whole] = 5
    report["summary"][part] = 6

    with pytest.raises(EvidenceValidationError, match="cannot be larger than its set"):
        normalize_report_evidence(report)


@pytest.mark.parametrize("parts, whole", SUMMARY_SUMS, ids=lambda v: str(v))
def test_every_declared_summary_sum_is_enforced(
    tmp_path: Path, parts: tuple[str, ...], whole: str
) -> None:
    """Statuses partition their population: each file and each
    declaration receives exactly one, so warnings plus failures can
    never exceed the count they were drawn from.

    The summary is built so the rule under test is the *only* one that
    can fire — otherwise a subset rule trips first and the test passes
    while proving nothing about the sum.
    """
    report = _valid_report(tmp_path)
    summary = dict.fromkeys(
        (field.name for field in SummaryEvidence.__dataclass_fields__.values()), 0
    )
    summary.update({name: True for name in ("has_readme", "has_changelog", "has_docs_dir")})
    summary["files_scanned"] = summary["declarations_scanned"] = 100
    summary["production_files_scanned"] = summary["production_declarations_scanned"] = 100
    summary[whole] = 4
    for index, name in enumerate(parts):
        summary[name] = 3 if index == 0 else 2
    for part_name, whole_name in SUMMARY_SUBSETS:
        if summary[part_name] <= summary[whole_name]:
            continue
        if whole_name == whole:
            summary[part_name] = summary[whole_name]  # never raise the population under test
        else:
            summary[whole_name] = summary[part_name]
    report["summary"] = summary

    with pytest.raises(EvidenceValidationError, match="one status"):
        normalize_report_evidence(report)


@pytest.mark.parametrize("part, whole", HISTORY_SUBSETS, ids=lambda v: str(v))
def test_every_declared_history_subset_is_enforced(tmp_path: Path, part: str, whole: str) -> None:
    report = _valid_report(tmp_path)
    report["history"][whole] = 5
    report["history"][part] = 6

    with pytest.raises(EvidenceValidationError, match="cannot be larger than its set"):
        normalize_report_evidence(report)


STATUS_TO_POPULATION = tuple(
    (part, whole)
    for part, whole in SUMMARY_SUBSETS
    if part.endswith(("_failures", "_warnings")) and whole.endswith("_scanned")
)


@pytest.mark.parametrize("part, whole", STATUS_TO_POPULATION, ids=lambda v: str(v))
def test_a_status_count_is_bounded_even_when_its_sibling_is_unknown(
    tmp_path: Path, part: str, whole: str
) -> None:
    """The sum relation skips on Unknown; the individual one must not.

    An audit found ``files_scanned=5, file_failures=6`` accepted
    whenever ``file_warnings`` was absent, because the only rule
    covering it was the sum and the sum needs both siblings Measured.
    A known count cannot exceed a known population no matter what is
    unknown beside it. Each pair is checked here with its sibling
    deleted, which is the exact condition that bypassed the inventory.
    """
    sibling = part.replace("_failures", "_warnings") if part.endswith("_failures") else part.replace("_warnings", "_failures")
    report = _valid_report(tmp_path)
    summary = dict.fromkeys(
        (field.name for field in SummaryEvidence.__dataclass_fields__.values()), 0
    )
    summary.update({name: True for name in ("has_readme", "has_changelog", "has_docs_dir")})
    summary["files_scanned"] = summary["declarations_scanned"] = 1_000
    summary["production_files_scanned"] = summary["production_declarations_scanned"] = 1_000
    summary[whole] = 5
    summary[part] = 6
    for other, other_whole in SUMMARY_SUBSETS:
        if other != part and summary.get(other, 0) > summary.get(other_whole, 0):
            summary[other] = summary[other_whole]
    del summary[sibling]
    report["summary"] = summary

    with pytest.raises(EvidenceValidationError, match="cannot be larger than its set"):
        normalize_report_evidence(report)


def test_an_unknown_never_manufactures_an_invariant_violation(tmp_path: Path) -> None:
    """An absent count constrains nothing and must not be read as zero.

    Without this, deleting ``files_scanned`` would make every count
    "exceed" a population of zero and turn a concealed field into a hard
    validation error — punishing absence in the one place that is
    supposed to represent it faithfully.
    """
    report = _valid_report(tmp_path)
    del report["summary"]["files_scanned"]

    evidence = normalize_report_evidence(report)

    assert isinstance(evidence.summary.files_scanned, Unknown)
