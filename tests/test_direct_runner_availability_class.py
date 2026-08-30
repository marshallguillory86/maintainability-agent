"""Class B (Grok 63ab820), third seam: a standalone analyzer that turns a
runner result into an availability verdict cannot read a not-usable run as
clean.

``test_empty_output_not_clean`` closed the runner seam (a findings-exit
with an empty body is ``NOT_WORKING``) and ``..._adapters`` closed the
adapter population (every ``_read`` with a silent empty default becomes a
``parse_error``). Both rest on ``BaseAdapter.parse``, which refuses a
not-usable run before ``_read`` ever sees it.

This seam is the analyzer that does **not** go through ``parse``: it calls
``_runner.run`` itself and builds its own result dict. ``local_tsc_analysis``
did exactly that and gated on ``exit_code is None`` -- true only for a
timeout or an exec failure -- so a ``tsc`` config error (FAILED, exit 3+)
or a findings exit with an empty body (NOT_WORKING, exit set) fell through
and reported ``status: available`` with an empty ``diagnostics`` list: no
type errors, from a compiler that never checked. Absence read as a pass,
the class ADR 001 forbids.

Population: derived from source, not listed. Any function that both calls
``run`` and builds a dict carrying a ``"status"`` key is a direct-runner
verdict. The AST guard fails **any** such function that does not consult
``result.usable`` -- a future standalone analyzer that forgets the gate
fails here even though only ``local_tsc_analysis`` is exercised below.
"""

from __future__ import annotations

import ast
from pathlib import Path

from maintainability_audit import _semantic_ts
from maintainability_audit._runner import Outcome, ToolResult

SRC = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"


def _calls_run(fn: ast.FunctionDef) -> bool:
    return any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "run"
        for n in ast.walk(fn)
    )


def _builds_a_status_dict(fn: ast.FunctionDef) -> bool:
    for node in ast.walk(fn):
        if isinstance(node, ast.Dict) and any(
            isinstance(k, ast.Constant) and k.value == "status" for k in node.keys
        ):
            return True
    return False


def _consults_usable(fn: ast.FunctionDef) -> bool:
    return any(
        isinstance(n, ast.Attribute) and n.attr == "usable" for n in ast.walk(fn)
    )


def _direct_runner_verdicts() -> dict[str, ast.FunctionDef]:
    found: dict[str, ast.FunctionDef] = {}
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
            if _calls_run(fn) and _builds_a_status_dict(fn):
                found[f"{path.name}:{fn.name}"] = fn
    return found


def test_the_direct_runner_verdict_population_is_derived_and_not_empty() -> None:
    """The class exists: at least one analyzer builds an availability
    verdict straight from a runner result, without ``BaseAdapter.parse``."""
    verdicts = _direct_runner_verdicts()
    assert verdicts, "no function both calls run() and builds a status dict"
    assert any(name.endswith(":local_tsc_analysis") for name in verdicts)


def test_every_direct_runner_verdict_consults_usable() -> None:
    """A direct-runner verdict that never reads ``result.usable`` cannot
    tell a clean run from a crash, so it prices a failure as clean. The
    gate is the only honest signal; a new one that omits it fails here."""
    offenders = [
        name for name, fn in _direct_runner_verdicts().items()
        if not _consults_usable(fn)
    ]
    assert not offenders, (
        f"direct-runner verdicts that ignore result.usable: {offenders}; "
        "return None/unavailable when the run is not usable"
    )


def _tsc_repo(tmp_path: Path) -> Path:
    (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")
    return tmp_path


def _patch_tsc_present(monkeypatch) -> None:
    monkeypatch.setattr(_semantic_ts, "locate", lambda _name: "/usr/bin/tsc")


def test_a_failed_tsc_run_is_not_reported_as_a_clean_type_check(
    tmp_path: Path, monkeypatch,
) -> None:
    """FAILED (a config error, exit set, empty stdout) must not become
    ``status: available`` with no diagnostics -- the reproduced hole."""
    _patch_tsc_present(monkeypatch)
    monkeypatch.setattr(_semantic_ts, "run", lambda *a, **k: ToolResult(
        slug="typescript", outcome=Outcome.FAILED, exit_code=3,
        stdout="", stderr="error TS5058: config not found", detail="tsc failed"))
    assert _semantic_ts.local_tsc_analysis(_tsc_repo(tmp_path)) is None


def test_a_not_working_tsc_run_is_not_reported_as_a_clean_type_check(
    tmp_path: Path, monkeypatch,
) -> None:
    """NOT_WORKING (a findings exit that produced nothing, exit set) is the
    other half the ``exit_code is None`` guard let through."""
    _patch_tsc_present(monkeypatch)
    monkeypatch.setattr(_semantic_ts, "run", lambda *a, **k: ToolResult(
        slug="typescript", outcome=Outcome.NOT_WORKING, exit_code=1,
        stdout="", stderr="", detail="findings exit, no output"))
    assert _semantic_ts.local_tsc_analysis(_tsc_repo(tmp_path)) is None


def test_a_clean_tsc_run_still_reports_available_with_no_diagnostics(
    tmp_path: Path, monkeypatch,
) -> None:
    """The complementary half: a RAN with an empty body is a compiler that
    checked and found nothing, and must stay a real clean result -- the
    fix must not fail an honest pass."""
    _patch_tsc_present(monkeypatch)
    monkeypatch.setattr(_semantic_ts, "run", lambda *a, **k: ToolResult(
        slug="typescript", outcome=Outcome.RAN, exit_code=0,
        stdout="", stderr="", detail=""))
    analysis = _semantic_ts.local_tsc_analysis(_tsc_repo(tmp_path))
    assert analysis is not None
    assert analysis["status"] == "available"
    assert analysis["diagnostics"] == []
