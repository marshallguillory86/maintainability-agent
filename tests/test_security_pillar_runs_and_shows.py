"""The security pillar is measured by every audit, and shown where it is read.

D176 and D177, reported running an audit from the ChatGPT desktop app.

D177's claim: **an audit runs secure-code-agent for the security pillar,
and the only thing it leaves in the audited tree is that tool's declared
history.** Until 3.7.0 the pillar was measured only when another process had
left `security-pillar.json` in the tree, which no audit through the chat door
ever had.

D176's claim: **every skin that reports on the pillars shows every pillar,
in every state it can be in.** The chat view printed nothing about security,
measured or not, and the remediation prompt likewise — so a missing pillar
read exactly like a clean one, which ADR 007 forbids.

Populations are derived: pillars from `PILLARS`, postures from
`POSTURE_NOTE`, and the files a run leaves behind from `git status` on a
real repository rather than from a list of the other tool's outputs.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "app.py").write_text("def run(value):\n    return value + 1\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    return repo


def _security(report: dict[str, Any]) -> dict[str, Any]:
    found = [entry for entry in report["pillars"] if entry["pillar"] == "security"]
    assert found, "the report carries no security pillar"
    return found[0]


def _document(**overrides: Any) -> dict[str, Any]:
    payload = {
        "schema": "secure-code-agent/security-pillar", "schema_version": 2,
        "pillar": "security", "generated": "2026-09-13T00:00:00Z",
        "producer": {"tool": "secure-code-agent", "version": "0.10.0"},
        "reason": "secure-code-agent owns the security pillar",
        "practice": {"level": 5, "summary": "discipline", "signals": [], "caps": []},
        "condition": 5.0, "condition_letter": "A", "posture": "healthy",
        "verified_grade": "A", "evidence_status": "complete", "evidence_reasons": [],
        "coverage": {"status": "complete", "scanners_run": ["gitleaks"], "scanners_missing": []},
        "findings_by_severity": {}, "reported_not_scored": {}, "loc_scanned": 1000,
    }
    payload.update(overrides)
    return payload


def test_an_audit_runs_secure_code_agent_and_leaves_only_its_declared_history(
    tmp_path, real_security_delegate,
) -> None:
    """D177: no document handed over, so the audit measures the pillar itself."""
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    repo = _repo(tmp_path)
    before = set(_git(repo, "status", "--porcelain", "-uall", "--ignored").splitlines())
    report = build_report(repo, load_config(None), run_analyzers=False)

    entry = _security(report)
    assert entry.get("delegated_to") == "secure-code-agent", (
        f"the audit did not measure the security pillar: {entry}"
    )
    assert entry.get("producer_version"), "the pillar does not say which release measured it"
    after = set(_git(repo, "status", "--porcelain", "-uall", "--ignored").splitlines())
    written = sorted(line[3:] for line in after - before)
    assert written == [".secure-code/history.jsonl"], (
        f"running secure-code-agent left more than its declared history in the tree: {written}"
    )


def test_a_pillar_document_the_tree_supplies_is_not_reported_as_the_measurement(
    tmp_path, real_security_delegate,
) -> None:
    """D177: a repository may not report its own security posture in place of a run."""
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    repo = _repo(tmp_path)
    planted = _document(producer={"tool": "planted-by-the-tree", "version": "9.9.9"})
    target = repo / ".maintainability" / "security-pillar.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(planted), encoding="utf-8")

    entry = _security(build_report(repo, load_config(None), run_analyzers=False))
    assert entry.get("producer_version") != "9.9.9" and entry.get("delegated_to") != "planted-by-the-tree", (
        f"the report carried the document the tree supplied: {entry}"
    )


def test_an_operator_document_is_used_as_given_and_nothing_else_runs(tmp_path, monkeypatch) -> None:
    """CI names the document with `--security-pillar`; the audit does not run the tool again.

    Covers existing behaviour: `--security-pillar` was read as given before
    D177; this guards that running the delegate did not override an operator.
    """
    from maintainability_audit import report as report_module
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    repo = _repo(tmp_path)
    (repo / "handed.json").write_text(json.dumps(_document()), encoding="utf-8")

    def refuse(*_args, **_kwargs):
        raise AssertionError("the delegate ran although the operator named a document")

    monkeypatch.setattr(report_module, "run_security_delegate", refuse, raising=False)
    entry = _security(build_report(repo, load_config(None), run_analyzers=False,
                                   security_pillar="handed.json"))
    assert entry.get("posture") == "healthy"


def test_a_missing_delegate_is_stated_with_its_remedy(tmp_path, monkeypatch) -> None:
    """D177: not installed is a reason on the pillar and a line in the environment work order."""
    import importlib.util

    from maintainability_audit import _security_delegate
    from maintainability_audit import report as report_module
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    real_find = importlib.util.find_spec
    monkeypatch.setattr(_security_delegate.importlib.util, "find_spec",
                        lambda name, *a: None if name == "secure_code_audit" else real_find(name, *a))
    monkeypatch.setattr(report_module, "run_security_delegate",
                        _security_delegate.run_security_delegate, raising=False)

    report = build_report(_repo(tmp_path), load_config(None), run_analyzers=False)
    entry = _security(report)
    assert "not installed" in entry["reason"], entry["reason"]
    remedies = [item for item in report["environment_work_order"] if item["tool"] == "secure-code-agent"]
    assert remedies and "pip install" in remedies[0]["install"], report["environment_work_order"]


@pytest.mark.parametrize("installed", ["0.10.0", "0.12.0", "1.0.0"])
def test_an_unsupported_release_is_stated_not_run(tmp_path, monkeypatch, installed) -> None:
    """D177: installed but outside the supported range is a reason and a remedy, never a run.

    secure-code-agent is no longer a package dependency, so the version a machine has is
    whatever it has. Running a release outside the range would read a contract this
    audit has not been checked against.
    """
    import importlib.machinery
    import importlib.metadata as metadata

    from maintainability_audit import _security_delegate
    from maintainability_audit import report as report_module
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    real_version = metadata.version
    monkeypatch.setattr(metadata, "version",
                        lambda name: installed if name == "secure-code-agent" else real_version(name))
    # Installed, as far as the audit can tell, whatever this environment holds:
    # the release build ran this without secure-code-agent and read "not installed".
    real_find = _security_delegate.importlib.util.find_spec
    monkeypatch.setattr(_security_delegate.importlib.util, "find_spec",
                        lambda name, *a: importlib.machinery.ModuleSpec(name, None)
                        if name == "secure_code_audit" else real_find(name, *a))
    monkeypatch.setattr(_security_delegate, "run",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("an unsupported release ran")),
                        raising=False)
    monkeypatch.setattr(report_module, "run_security_delegate",
                        _security_delegate.run_security_delegate, raising=False)

    report = build_report(_repo(tmp_path), load_config(None), run_analyzers=False)
    entry = _security(report)
    assert installed in entry["reason"] and "is installed" in entry["reason"], entry["reason"]
    remedies = [item for item in report["environment_work_order"] if item["tool"] == "secure-code-agent"]
    assert remedies and "secure-code-agent>=" in remedies[0]["install"], report["environment_work_order"]


def _states() -> dict[str, dict[str, Any]]:
    """Every state the security pillar can be in, as `pillar_report` builds it."""
    from maintainability_audit._pillars import pillar_report

    practice = {"level": 3, "summary": "enforcement", "signals": [], "caps": []}
    score = {"aspects": {}}
    return {
        "unmeasured": {"pillars": pillar_report(score, practice, None,
                                                {"security": "secure-code-agent did not run"}),
                       "practice": practice},
        "measured": {"pillars": pillar_report(score, practice, {"security": _document()}),
                     "practice": practice},
        "ungraded": {"pillars": pillar_report(score, practice, {"security": _document(
                         condition=None, condition_letter=None, posture="unverified",
                         verified_grade=None, evidence_status="incomplete",
                         evidence_reasons=["scanner coverage is partial"])}),
                     "practice": practice},
    }


@pytest.mark.parametrize("state", ["unmeasured", "measured", "ungraded"])
def test_every_pillar_reaches_the_chat_view_and_the_prompt(tmp_path, state) -> None:
    """D176: the bounded chat view and the prompt carry the pillars in every state."""
    from maintainability_audit._pillars import PILLARS
    from maintainability_audit.config import load_config
    from maintainability_audit.prompts import render_ai_prompt
    from maintainability_audit.renderers import render_markdown
    from maintainability_audit.report import build_report

    names = [pillar.name for pillar in PILLARS]
    assert names, "PILLARS is empty"
    report = build_report(_repo(tmp_path), load_config(None), run_analyzers=False)
    report.update(_states()[state])

    chat = render_markdown(report, complete=False)
    missing = [name for name in names if f"| {name} |" not in chat]
    assert not missing, f"the chat view omits pillars {missing} when security is {state}"
    assert "Security pillar" in render_ai_prompt(report), (
        f"the remediation prompt says nothing about security when it is {state}"
    )


def test_an_ungraded_pillar_is_never_described_as_a_clean_scan() -> None:
    """D176: `unverified` with no condition means nothing was graded, not a clean scan."""
    from maintainability_audit._scan_view import POSTURE_NOTE, pillar_cells

    assert POSTURE_NOTE, "no posture notes to check"
    wrong = []
    for posture_name, note in POSTURE_NOTE.items():
        _, reading = pillar_cells({"condition": None, "posture": posture_name,
                                   "evidence_reasons": ["scanner coverage is partial"]})
        if note in reading:
            wrong.append((posture_name, reading))
    assert not wrong, f"ungraded pillars given a graded pillar's note: {wrong}"
