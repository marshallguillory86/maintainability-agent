"""A scope-limited scan carries no whole-repository score.

The scale is calibrated over whole repositories, so a diff is not a small
repository — it is a different kind of object, and scoring one on this scale
is a category error rather than a precision problem.

Before this, `--changed-only HEAD~1` on this repository reported
`maintainability_estimate 4.2`, `evidence_status complete`, over 2 files and
**zero declarations**. Every PR-scoped CI run inherited it. ADR 005.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from maintainability_audit._evidence_view import NO_SCORE, estimate, score_range, status_sentence
from maintainability_audit.config import load_config
from maintainability_audit.evidence import (
    KNOWN_SCOPES,
    SCOPE_FULL,
    EvidenceValidationError,
    normalize_report_evidence,
)
from maintainability_audit.report import build_report
from maintainability_audit.scoring import score_report


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "r"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    for i in range(6):
        (root / f"m{i}.py").write_text(f"def f{i}():\n    return {i}\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "x"],
        check=True,
    )
    return root


@pytest.mark.parametrize("scope", sorted(KNOWN_SCOPES - {SCOPE_FULL}))
def test_no_limited_scope_produces_a_score(tmp_path: Path, scope: str) -> None:
    """Every non-full scope, not just the one that was reported.

    Swept over the scope vocabulary so a scope added later fails here
    rather than silently inheriting a whole-repository grade.
    """
    report = build_report(_repo(tmp_path), load_config(None))
    report["mode"] = scope
    score = score_report(report)

    assert score["maintainability_estimate"] is None
    assert score["maintainability_range"] is None
    assert score["verified_grade"] is None
    assert score["evidence_status"]["status"] == "insufficient"


def test_a_full_scan_is_unchanged(tmp_path: Path) -> None:
    """The fix must not cost a real scan its score."""
    score = score_report(build_report(_repo(tmp_path), load_config(None)))

    assert isinstance(score["maintainability_estimate"], float)
    assert score["maintainability_range"] is not None
    assert score["evidence_status"]["status"] != "insufficient"


def test_the_reason_names_the_scope_and_the_remedy(tmp_path: Path) -> None:
    report = build_report(_repo(tmp_path), load_config(None))
    report["mode"] = "changed-only"
    reasons = score_report(report)["evidence_status"]["reasons"]

    assert len(reasons) == 1
    only = reasons[0]
    assert only["measurement"] == "scan.scope"
    assert "changed-only" in only["reason"]
    assert "Re-run" in only["reason"], "a reason without a remedy leaves the reader stuck"
    assert only["provenance"], "every reason carries provenance or consumers special-case it"


def test_findings_survive_a_scope_limited_scan(tmp_path: Path) -> None:
    """Only the rolled-up judgment is withheld.

    A diff with a 300-line function still reports it: that is an
    observation about a specific line of code and needs no population to
    be true. Suppressing findings would turn a withheld score into a
    withheld audit.
    """
    root = _repo(tmp_path)
    body = "\n".join(f"    x{i} = {i}" for i in range(120))
    (root / "big.py").write_text(f"def huge():\n{body}\n    return 0\n", encoding="utf-8")
    report = build_report(root, load_config(None))
    report["mode"] = "changed-only"
    report["score"] = score_report(report)

    assert report["score"]["maintainability_estimate"] is None
    assert any(f["status"] == "fail" for f in report["function_hotspots"])
    assert report["score"]["aspects"], "aspects are observations and are not suppressed"


def test_no_consumer_renders_a_withheld_score_as_a_number(tmp_path: Path) -> None:
    """Not a dash, not a zero — both read as a value.

    A reader scanning a table cannot tell a withheld score from a bad
    one if the withheld case borrows a number's shape.
    """
    report = build_report(_repo(tmp_path), load_config(None))
    report["mode"] = "changed-only"
    score = score_report(report)

    for rendered in (estimate(score), score_range(score)):
        assert rendered == NO_SCORE
        assert "0" not in rendered
        assert rendered.strip() not in {"-", "–", "—", "n/a", "N/A"}
    assert "No score issued" in status_sentence(score)


def test_an_unknown_scope_is_rejected_rather_than_defaulted(tmp_path: Path) -> None:
    """Defaulting would grant a grade to a scan nobody can describe."""
    report = build_report(_repo(tmp_path), load_config(None))
    report["mode"] = "some-future-mode"

    with pytest.raises(EvidenceValidationError, match="unknown scan scope"):
        normalize_report_evidence(report)


def test_changed_only_through_the_cli_withholds_the_score(tmp_path: Path) -> None:
    """End to end, because the defect was reported against the flag."""
    root = _repo(tmp_path)
    (root / "m0.py").write_text("def f0():\n    return 99\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "y"],
        check=True,
    )
    result = subprocess.run(
        [sys.executable, "-m", "maintainability_audit", "--root", str(root),
         "--format", "json", "--changed-only", "HEAD~1"],
        capture_output=True, text=True, check=True,
    )
    score = json.loads(result.stdout)["score"]

    assert score["maintainability_estimate"] is None
    assert score["verified_grade"] is None
