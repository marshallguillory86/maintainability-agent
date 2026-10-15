"""Written by the Claude Sonnet test seat (Codex at its usage limit); Codex reviews.

Defect: an analyzer rewrote the audited repository (2026-10-14).

MA's contract is that it never edits source. The ruff adapter ran
`ruff check` in the audited repository, ruff honoured that repository's own
`fix = true`, and 102 files were rewritten. Three layers are specified:

1. the ruff and fortitude argv carry `--no-fix`;
2. no registered adapter's argv carries a write-enabling token (the bug
   class, swept over the registry so a new adapter is covered);
3. the structural block: if a tracked file of the audited git repository
   changes while an analyzer runs, the audit raises `RepositoryModifiedError`
   from `_analysis._run_batches` (the function that runs an adapter's
   invocations) naming the changed path, instead of succeeding quietly;
4. end to end with the real ruff.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from maintainability_audit import _analysis, _runner
from maintainability_audit._adapters import BaseAdapter
from maintainability_audit._runner import Outcome, ToolResult
from maintainability_audit._tool_adapters import ADAPTERS

WRITE_TOKENS = ("--fix", "--write", "--in-place", "-i", "--apply", "--fix-only", "--unsafe-fixes")


def _tree(root: Path) -> list[str]:
    """A few files of several kinds, so file-list adapters have targets."""
    names = ("mod.py", "Main.java", "main.f90", "app.js", "lib.c", "x.go", "y.rs", "z.ts")
    for name in names:
        (root / name).write_text("x\n", encoding="utf-8")
    return [str(root / name) for name in names]


def _argvs(slug: str, root: Path) -> list[tuple[str, ...]]:
    adapter = ADAPTERS[slug]()
    files = _tree(root)
    runs = list(adapter.invocations(root, ()))
    runs.append(adapter.invocation(root, files))
    return [tuple(run.argv) for run in runs]


@pytest.mark.parametrize("slug", ["ruff", "fortitude"])
def test_the_linters_that_can_fix_are_told_not_to(slug: str, tmp_path: Path) -> None:
    for argv in _argvs(slug, tmp_path):
        assert "--no-fix" in argv, f"{slug} may rewrite the audited repository: {argv}"


# --- the structural block -------------------------------------------------


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _repo(root: Path) -> Path:
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "mod.py").write_text("import os\n", encoding="utf-8")
    (root / "other.py").write_text("y = 1\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "init")
    return root


class _Probe(BaseAdapter):
    def __init__(self) -> None:
        super().__init__(slug="fake", emits="verdict", executable="fake", concepts=("style",))

    def _read(self, result: ToolResult):  # pragma: no cover - parse is not the subject
        from maintainability_audit._adapters import Extraction
        return Extraction()


def _fake_run(monkeypatch: pytest.MonkeyPatch, effect) -> None:
    def fake(slug, invocation, **kwargs):
        effect()
        return ToolResult(slug=slug, outcome=Outcome.RAN, stdout="[]", exit_code=0)

    monkeypatch.setattr(_analysis, "run", fake)


def test_an_analyzer_that_edits_a_tracked_file_is_an_integrity_failure(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repo(tmp_path)
    _fake_run(monkeypatch, lambda: (root / "mod.py").write_text("", encoding="utf-8"))

    with pytest.raises(_analysis.RepositoryModifiedError) as raised:
        _analysis._run_batches(_Probe(), root, (), 60)

    assert "mod.py" in str(raised.value)
    assert "other.py" not in str(raised.value)


# --- end to end with the real tool ----------------------------------------


@pytest.mark.skipif(_runner.locate("ruff") is None, reason="ruff is not installed here")
def test_real_ruff_with_fix_true_leaves_the_audited_repository_untouched(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path
    # ruff reads `fix` from the config found from its working directory, not
    # from the audited file's directory, so the defect only shows when the
    # audit runs from inside the repository (the CLI's case, and the incident's).
    monkeypatch.chdir(root)
    (root / "ruff.toml").write_text('fix = true\n[lint]\nselect = ["F"]\n', encoding="utf-8")
    (root / "mod.py").write_text("import os\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "init")
    before = (root / "mod.py").read_bytes()

    _analysis._run_batches(ADAPTERS["ruff"](), root, (), 60)

    assert (root / "mod.py").read_bytes() == before
    status = subprocess.run(["git", "status", "--porcelain"], cwd=root, check=True,
                            capture_output=True, text=True).stdout
    assert status == ""
