"""D20: a configured history path cannot escape its repository.

`paths.history` comes from a file inside the repository under audit, so
a traversal, an absolute path, or a symlink pointing outward is that
repository asking the tool to write somewhere it was never authorized
to touch. An audit reproduced the external write through the public MCP
seam; these hold both doors to the same boundary.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from maintainability_audit.cli import main
from maintainability_audit.config import CONFIG_FILENAME, PathNotAllowed
from maintainability_audit.mcp_server import audit_repository


def _repo(root: Path, history: str) -> Path:
    root.mkdir(parents=True)
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (root / "app.py").write_text("x = 1\n", encoding="utf-8")
    (root / CONFIG_FILENAME).write_text(
        json.dumps({
            "version": 1,
            "analyzers": {"run": False},
            "paths": {"history": history},
        }),
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def _audit(root: Path, **kwargs: Any) -> dict[str, Any]:
    return audit_repository(
        str(root), format="json", record_history=True,
        roots=(root.parent.resolve(),), **kwargs,
    )


def test_mcp_history_rejects_parent_traversal_without_external_write(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path / "repo", "../outside.jsonl")
    outside = tmp_path / "outside.jsonl"

    with pytest.raises(PathNotAllowed):
        _audit(root)

    assert not outside.exists(), "a traversal escaped the authorized repository"


def test_mcp_history_rejects_absolute_escape_without_external_write(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "absolute.jsonl"
    root = _repo(tmp_path / "repo", str(outside))

    with pytest.raises(PathNotAllowed):
        _audit(root)

    assert not outside.exists(), "an absolute path escaped the repository"


def test_mcp_history_rejects_symlink_escape_without_external_write(
    tmp_path: Path,
) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    root = _repo(tmp_path / "repo", "linked/history.jsonl")
    (root / "linked").symlink_to(elsewhere)

    with pytest.raises(PathNotAllowed):
        _audit(root)

    assert not (elsewhere / "history.jsonl").exists(), (
        "a symlinked directory carried the history outside the repository"
    )


def test_a_history_path_inside_the_repository_still_records(tmp_path: Path) -> None:
    """The boundary refuses escapes, not ordinary configuration."""
    root = _repo(tmp_path / "repo", "state/history.jsonl")

    _audit(root)

    assert (root / "state" / "history.jsonl").is_file()


@pytest.mark.parametrize(
    "history",
    ["../cli-outside.jsonl", "linked/cli-history.jsonl"],
)
def test_the_cli_door_applies_the_same_boundary(
    tmp_path: Path, history: str,
) -> None:
    """Both doors, one rule: the CLI cannot be the way around it."""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    root = _repo(tmp_path / "repo", history)
    (root / "linked").symlink_to(elsewhere)

    with pytest.raises(PathNotAllowed):
        main(["--root", str(root), "--record-history", "--format", "json",
              "--output", str(tmp_path / "report.json")])

    assert not (tmp_path / "cli-outside.jsonl").exists()
    assert not (elsewhere / "cli-history.jsonl").exists()
