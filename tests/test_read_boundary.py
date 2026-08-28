"""D36: the agent reads inside the grant, wherever the path came from.

`SECURITY.md` puts reads outside `--root` in scope. Two audits found
two ways past it on the same day, and both start from the same place:
the audited repository supplies a path, and the code trusts it because
it *looks* relative.

The scan escape is the one with teeth. `Path.is_file()` follows
symlinks, so a repository containing `linked.py -> ../secret.py` had
that file's contents read, measured, and copied into the report — an
audit got `TOP_SECRET_VALUE = 42` back inside a findings payload.

Symlinks that stay inside the root remain allowed on purpose. They are
ordinary in real trees, they resolve within the grant, and refusing
them would silently drop first-party code the operator asked to audit.
The boundary is where the path lands, not whether a link was involved.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from maintainability_audit._jvm_adapters import SpotBugsAdapter
from maintainability_audit._metric_adapters import expand_files
from maintainability_audit.config import load_config
from maintainability_audit.metrics import iter_files
from maintainability_audit.report import build_report

CONFIG = {"version": 1, "analyzers": {"run": False}}


def _repo(base: Path) -> Path:
    root = base / "repo"
    root.mkdir(parents=True)
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (root / "owned.py").write_text("def owned():\n    return 1\n", encoding="utf-8")
    (root / "maintainability-agent.json").write_text(
        json.dumps(CONFIG), encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def test_a_symlink_out_of_the_tree_is_never_scanned(tmp_path: Path) -> None:
    """The reproduction: an outside file's contents reached the report."""
    root = _repo(tmp_path)
    secret = tmp_path / "outside.py"
    secret.write_text("TOP_SECRET_VALUE = 42\n", encoding="utf-8")
    (root / "linked.py").symlink_to(secret)

    scanned = {path.name for path in iter_files(root, load_config(None))}
    assert "linked.py" not in scanned, "a file outside the grant was scanned"
    assert "owned.py" in scanned, "the boundary swallowed first-party code"

    report = build_report(root, load_config(str(root / "maintainability-agent.json")))
    rendered = json.dumps(report)
    assert "TOP_SECRET_VALUE" not in rendered, (
        "contents from outside the repository reached the report"
    )
    # Deliberately not asserting the *name* is absent everywhere:
    # `git_status_short` lists the symlink as an untracked entry, which
    # is git describing the working tree and not this agent reading
    # past its grant. What must not appear is the file among the things
    # measured.
    measured = json.dumps(report.get("largest_files") or [])
    assert "linked.py" not in measured


def test_a_symlink_that_stays_inside_the_tree_is_still_scanned(
    tmp_path: Path,
) -> None:
    """The boundary is where a path lands, not whether it is a link.

    Refusing every symlink would be easier and wrong: they are common
    in real repositories, and dropping them would quietly shrink the
    population a score is computed over.
    """
    root = _repo(tmp_path)
    (root / "nested").mkdir()
    (root / "nested" / "alias.py").symlink_to(root / "owned.py")

    scanned = {
        path.relative_to(root).as_posix() for path in iter_files(root, load_config(None))
    }
    assert "nested/alias.py" in scanned


def test_analyzer_argv_never_names_a_file_outside_the_tree(tmp_path: Path) -> None:
    """`expand_files` output becomes a child process's arguments.

    Worse than a read: the path is handed to an analyzer, which opens
    it with the host's privileges and reports on it as though it were
    the repository's own code.
    """
    root = _repo(tmp_path)
    secret = tmp_path / "outside.py"
    secret.write_text("SECRET = 1\n", encoding="utf-8")
    (root / "linked.py").symlink_to(secret)

    named = expand_files(root, ())
    assert not any("linked.py" in path for path in named)
    assert any("owned.py" in path for path in named)


def test_class_dirs_from_repository_config_cannot_leave_the_tree(
    tmp_path: Path,
) -> None:
    """D20's escape under a different field name.

    `Path(root) / "/"` is `/`, so four characters of repository config
    turned a bytecode scan into a walk of the filesystem — on an MCP
    child with no timeout.
    """
    root = _repo(tmp_path)

    assert SpotBugsAdapter()._target_dirs(root, ["/", "/etc", "../.."]) == ()

    classes = root / "target" / "classes"
    classes.mkdir(parents=True)
    (classes / "Widget.class").write_bytes(b"\xca\xfe\xba\xbe")
    assert SpotBugsAdapter()._target_dirs(root, []) == (classes,), (
        "the bound refused a legitimate in-tree class directory"
    )
