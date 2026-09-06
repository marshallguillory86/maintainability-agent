"""Contract for ``--staged``: the index, not the tree, and nothing else.

A pre-commit scan that reads the working tree passes content nobody
measured. This file is the other half of that claim: the public names
below, invoked against a real repository, either block what the index
will commit or they stay silent.
"""

from __future__ import annotations

import copy
import json
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from maintainability_audit.cli import main
from maintainability_audit.config import DEFAULT_CONFIG

NOQA = "#" + " noqa"


def _git(root: Path, *args: str) -> None:
    subprocess.check_output(["git", *args], cwd=root, text=True)


def _repo(tmp_path: Path) -> Path:
    """The fixture idiom at tests/test_scope_conformance.py:276."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    _git(tmp_path, "init", "--quiet", "-b", "main")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "config", "commit.gpgsign", "false")
    return tmp_path


def _stage(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    _git(root, "add", "--", relative)


def _oversized(start_line: int = 7) -> str:
    """A function whose declaration starts at ``start_line``, over budget."""
    body = "".join(f"    value_{index} = {index}\n" for index in range(100))
    return ("\n" * (start_line - 1)) + "def oversized():\n" + body + "    return value_0\n"


def _invoke(root: Path, *extra: str) -> int:
    try:
        return main(["--root", str(root), "--staged", *extra])
    except SystemExit as exit:
        return int(exit.code or 0)


def _report_and_findings(root: Path, config: dict | None = None) -> tuple[dict, list[dict]]:
    from maintainability_audit._precommit import staged_findings, staged_report

    report = staged_report(root, copy.deepcopy(config or DEFAULT_CONFIG))
    required = {
        "scanned", "largest_files", "function_hotspots", "risk_findings",
        "added_suppressions", "summary",
    }
    assert required <= report.keys(), f"staged report missing {sorted(required - report.keys())}"
    return report, staged_findings(report)


def _tree_snapshot(root: Path) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    for path in root.rglob("*"):
        if ".git" in path.parts or not path.is_file() or path.is_symlink():
            continue
        snapshot[path.relative_to(root).as_posix()] = path.read_bytes()
    return snapshot


def test_staged_reads_the_index_not_the_working_tree(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The classic pre-commit bug: the worktree is not what will land."""
    root = _repo(tmp_path)
    _stage(root, "widget.py", "def small():\n    return 1\n")
    (root / "widget.py").write_text(_oversized(), encoding="utf-8")

    assert _invoke(root) == 0, "a dirty worktree over a clean index blocked the commit"
    assert capsys.readouterr().out == ""

    _stage(root, "widget.py", _oversized())
    (root / "widget.py").write_text("def small():\n    return 1\n", encoding="utf-8")

    assert _invoke(root) == 1, "a clean worktree over a breaching index was allowed"
    assert "widget.py" in capsys.readouterr().out


def test_a_clean_index_exits_zero_with_empty_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _repo(tmp_path)
    _stage(root, "widget.py", "def small():\n    return 1\n")

    assert _invoke(root) == 0
    assert capsys.readouterr().out == "", "a clean index printed findings"

    from maintainability_audit._precommit_view import render_staged

    report, findings = _report_and_findings(root)
    assert render_staged(findings, report["scanned"]) == []


def test_a_breaching_index_names_path_line_and_remedy(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _repo(tmp_path)
    start_line = 7
    _stage(root, "widget.py", _oversized(start_line))

    assert _invoke(root) == 1
    printed = capsys.readouterr().out
    assert "widget.py" in printed

    from maintainability_audit._precommit_view import render_staged

    report, findings = _report_and_findings(root)
    assert findings, "a breaching index produced no findings"
    scanned = report["scanned"]
    count = scanned if isinstance(scanned, int) else len(scanned)
    rendered = "\n".join(render_staged(findings, count))
    for item in findings:
        assert item["path"], "a finding named no path"
        assert item["line"], "a finding named no line"
        # JSON names this `target`; the text rendering prints it as the remedy.
        assert item["target"], "a finding named no remedy"
        assert item["path"] in printed and item["path"] in rendered
        assert item["target"] in printed or item["target"] in rendered
    assert any(item["path"] == "widget.py" and item["line"] == start_line for item in findings), (
        "an oversized declaration reported line 1 instead of its start_line"
    )


def test_an_added_suppression_blocks_and_sorts_above_threshold_breaches(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _stage(root, "old.py", "old = 1  " + NOQA + "\n")
    _git(root, "commit", "--quiet", "-m", "existing directive")
    _stage(root, "widget.py", _oversized())
    _stage(root, "new.py", "new = 1  " + NOQA + "\n")

    report, findings = _report_and_findings(root)
    assert report["added_suppressions"], "an added suppression was invisible"
    assert findings, "nothing blocked"
    assert findings[0]["path"] == "new.py", "the added suppression did not sort first"
    assert findings[0]["severity"] == 250.0
    assert any(item["path"] == "widget.py" for item in findings)
    assert all(item["path"] != "old.py" for item in findings)
    assert _invoke(root) == 1


def test_staged_never_runs_the_test_suite(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _stage(root, "widget.py", "def small():\n    return 1\n")
    sentinel = root / "sentinel-test-command-ran"
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["test_execution"] = {"requested": True}
    config.setdefault("expected_commands", {})
    config["expected_commands"]["test"] = [
        sys.executable, "-c",
        f"from pathlib import Path; Path({str(sentinel)!r}).write_text('ran')",
    ]
    (root / "maintainability-agent.json").write_text(
        json.dumps({
            "version": 1,
            "test_execution": {"requested": True},
            "expected_commands": {"test": config["expected_commands"]["test"]},
        }),
        encoding="utf-8",
    )

    assert _invoke(root) == 0
    assert not sentinel.exists(), "the opt-in test command ran under --staged"
    _, findings = _report_and_findings(root, config)
    assert findings == []
    assert not sentinel.exists()


def test_staged_applies_no_repository_hard_gates(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _repo(tmp_path)
    _stage(root, "widget.py", "def small():\n    return 1\n")
    assert not (root / "README.md").exists()

    assert _invoke(root) == 0
    assert capsys.readouterr().out == ""


def test_staged_writes_nothing(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _stage(root, "widget.py", "def small():\n    return 1\n")
    history = root / ".maintainability" / "history.jsonl"
    history.parent.mkdir()
    history.write_text('{"existing": true}\n', encoding="utf-8")
    before = _tree_snapshot(root)

    assert _invoke(root) == 0
    assert _tree_snapshot(root) == before, "--staged wrote into the tree"


def test_staged_json_is_unscored_and_emitted_when_clean(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _repo(tmp_path)
    _stage(root, "widget.py", "def small():\n    return 1\n")

    assert _invoke(root, "--format", "json") == 0
    clean = json.loads(capsys.readouterr().out)
    assert clean["scored"] is False
    assert clean["scored_reason"]
    assert clean["blocked"] is False
    assert clean["staged"]
    assert clean["findings"] == []

    _stage(root, "widget.py", _oversized())
    assert _invoke(root, "--format", "json") == 1
    blocked = json.loads(capsys.readouterr().out)
    assert blocked["scored"] is False
    assert blocked["scored_reason"]
    assert blocked["blocked"] is True
    assert blocked["staged"]
    assert blocked["findings"]
    for item in blocked["findings"]:
        assert {"path", "target", "severity", "band"} <= item.keys()

    from maintainability_audit._precommit_view import staged_json

    report, findings = _report_and_findings(root)
    assert json.loads(staged_json(report, findings)) == blocked


@pytest.mark.parametrize(
    "extra, named",
    [
        (["--changed-only", "main...HEAD"], "--changed-only"),
        (["--record-history"], "--record-history"),
        (["--output", "x.md"], "--output"),
        (["--format", "html"], "html"),
    ],
)
def test_staged_refuses_flags_it_would_have_to_ignore(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], extra: list[str], named: str,
) -> None:
    """Each refused flag carries its argument; a bare ``--changed-only`` is argparse."""
    root = _repo(tmp_path)
    _stage(root, "widget.py", "def small():\n    return 1\n")

    code = _invoke(root, *extra)
    err = capsys.readouterr().err
    assert code == 2
    assert named in err, f"{named!r} was not named on stderr: {err!r}"
    assert "expected one argument" not in err


def test_staged_never_prompts_on_an_unconfigured_tty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    from maintainability_audit import cli, _first_run

    root = _repo(tmp_path)
    _stage(root, "widget.py", "def small():\n    return 1\n")
    monkeypatch.setattr(cli, "_stdin_is_a_tty", lambda: True)
    monkeypatch.setattr(_first_run, "_stdin_is_a_tty", lambda: True)

    def reject_prompt(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("--staged prompted on an unconfigured TTY")

    monkeypatch.setattr("builtins.input", reject_prompt)

    assert _invoke(root) == 0
    assert capsys.readouterr().out == ""
    assert not (root / "maintainability-agent.json").exists()


def test_fresh_hook_install_is_executable_and_marked(tmp_path: Path) -> None:
    from maintainability_audit._precommit_install import (
        HOOK_NAME, MARKER, hooks_directory, install_precommit_hook,
    )

    root = _repo(tmp_path)
    code, _message = install_precommit_hook(root)
    assert code == 0
    hook = hooks_directory(root) / HOOK_NAME
    assert stat.S_IMODE(hook.stat().st_mode) == 0o700
    assert MARKER in hook.read_text(encoding="utf-8")


def test_reinstall_over_our_hook_reports_updated(tmp_path: Path) -> None:
    from maintainability_audit._precommit_install import install_precommit_hook

    root = _repo(tmp_path)
    assert install_precommit_hook(root)[0] == 0
    code, message = install_precommit_hook(root)
    assert code == 0
    assert "updated" in message.lower()


def test_a_foreign_hook_is_refused_unchanged(tmp_path: Path) -> None:
    from maintainability_audit._precommit_install import (
        HOOK_NAME, hooks_directory, install_precommit_hook,
    )

    root = _repo(tmp_path)
    hook = hooks_directory(root) / HOOK_NAME
    original = b"#!/bin/sh\nprintf existing\\n\n"
    hook.write_bytes(original)
    code, message = install_precommit_hook(root)
    assert code == 1
    assert hook.read_bytes() == original
    assert "--staged" in message


def test_a_symlink_at_the_hook_path_is_refused(tmp_path: Path) -> None:
    from maintainability_audit._precommit_install import (
        HOOK_NAME, hooks_directory, install_precommit_hook,
    )

    root = _repo(tmp_path / "repo")
    outside = tmp_path / "outside-hook"
    hook = hooks_directory(root) / HOOK_NAME
    hook.symlink_to(outside)
    assert install_precommit_hook(root)[0] == 1
    assert hook.is_symlink()
    assert not outside.exists()


def test_core_hooks_path_is_read_from_config_files(tmp_path: Path) -> None:
    """hooks_directory reads the config files, not the git process (D92)."""
    from maintainability_audit._precommit_install import (
        HOOK_NAME, hooks_directory, install_precommit_hook,
    )

    root = _repo(tmp_path)
    _git(root, "config", "core.hooksPath", ".custom-hooks")
    assert hooks_directory(root) == root / ".custom-hooks", (
        "hooks_directory did not honour core.hooksPath from the config file"
    )
    assert install_precommit_hook(root)[0] == 0
    assert (root / ".custom-hooks" / HOOK_NAME).is_file()
    assert not (root / ".git" / "hooks" / HOOK_NAME).exists()
