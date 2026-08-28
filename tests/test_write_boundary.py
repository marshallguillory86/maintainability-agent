"""D34: an audited tree cannot redirect where this agent writes.

Every attack here was reproduced against the product before it was
fixed, and each is the same shape: check the path, then open the name.
D18 closed that class for the packaged skill and paid for descriptor
binding and staged replacement; nothing carried the lesson to the three
writes an ordinary audit performs.

Hardlinks are the reason `O_NOFOLLOW` is not enough on its own. A
hardlink is not a symbolic link, so the flag does not see it, and
opening the name for writing truncates the shared inode wherever else
it lives. Only never opening that inode — staging a new file and
renaming over the name — actually holds.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from maintainability_audit._mcp_setup import apply_answers
from maintainability_audit._scan_history import ScanRecord, append_scan, read_history
from maintainability_audit.config import PathNotAllowed

ANSWERS = {
    "run_pool": "no",
    "depth": "baseline",
    "license_policy": "permissive",
    "economics": "skip",
    "default_format": "chat",
    "record_scan_history": "no",
}


def _repo(base: Path) -> Path:
    root = base / "repo"
    root.mkdir(parents=True)
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (root / "app.py").write_text("def ok(v):\n    return v\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def _record() -> ScanRecord:
    """Borrowed from `test_scan_history`, which owns this shape."""
    return ScanRecord(
        recorded_at="2026-08-23T09:00:00Z",
        commit="a" * 40,
        branch="main",
        scope="full",
        rubric_version="0.7.0",
        calibration=2.6279,
        thresholds_digest="t-abc",
        analyzers=("lizard",),
        scored_languages=("Python",),
        estimate=4.2,
        populations={"files_scanned": 2, "declarations_scanned": 1},
        fingerprints=("f1",),
    )


def test_setup_refuses_to_write_config_through_a_symlink(tmp_path: Path) -> None:
    """The reproduction, verbatim: a dangling link took config outside.

    `setup_pending` reads `True` here because `is_file()` is false on a
    dangling symlink, so setup believes the repository is unconfigured
    and writes — through the link, to a path the operator never granted.
    """
    root = _repo(tmp_path)
    outside = tmp_path / "outside.json"
    (root / "maintainability-agent.json").symlink_to(outside)

    with pytest.raises(PathNotAllowed):
        apply_answers(root, ANSWERS)

    assert not outside.exists(), (
        "first-run configuration was written outside the repository"
    )


def test_setup_refuses_a_symlink_pointing_back_inside_the_repository(
    tmp_path: Path,
) -> None:
    """Inside the root is not the same as the file the operator meant.

    A link that resolves within the repository passes every
    root-containment check and still redirects the write. Refused
    because it is a link, not because of where it points.
    """
    root = _repo(tmp_path)
    (root / "maintainability-agent.json").symlink_to(root / "README.md")

    with pytest.raises(PathNotAllowed):
        apply_answers(root, ANSWERS)

    assert (root / "README.md").read_text(encoding="utf-8") == "# fixture\n"


def test_history_append_cannot_reach_a_hardlinked_inode(tmp_path: Path) -> None:
    """The append that landed on an outside file.

    `repository_path` bounds the name and never the inode, so the old
    `open("a")` wrote wherever the hardlink pointed. The staged
    replacement means the outside file keeps its contents and simply
    stops being this name.
    """
    root = _repo(tmp_path)
    victim = tmp_path / "victim.jsonl"
    victim.write_text("KEEP\n", encoding="utf-8")
    history = root / ".maintainability" / "history.jsonl"
    history.parent.mkdir(parents=True)
    history.hardlink_to(victim)

    append_scan(history, _record(), root)

    assert victim.read_text(encoding="utf-8") == "KEEP\n", (
        "a scan record was appended onto a file outside the repository"
    )
    assert len(read_history(history)) == 1, "the scan was not recorded in the repo"


def test_a_first_scan_still_records_normally(tmp_path: Path) -> None:
    """The fix must not cost the feature it protects.

    A refusal that also refuses the ordinary case is not a fix, and a
    staged rewrite is exactly the kind of change that silently drops
    earlier lines.
    """
    root = _repo(tmp_path)
    history = root / ".maintainability" / "history.jsonl"

    append_scan(history, _record(), root)
    append_scan(history, _record(), root)

    assert len(read_history(history)) == 2, "the staged rewrite lost a record"


def test_a_baseline_may_not_overwrite_something_that_is_not_one(
    tmp_path: Path,
) -> None:
    """`baseline_path` arrives from a model on the primary surface.

    Being inside the granted root was the only check, so pointing it at
    `README.md` turned source into baseline JSON — in a tool whose MCP
    description promises five artifacts and "never source".
    """
    from maintainability_audit.mcp_server import audit_repository

    root = _repo(tmp_path)
    (root / "maintainability-agent.json").write_text(
        json.dumps({"version": 1, "analyzers": {"run": False}}), encoding="utf-8",
    )
    before = (root / "README.md").read_text(encoding="utf-8")

    with pytest.raises(PathNotAllowed):
        audit_repository(
            str(root), action="run", write_baseline=True,
            baseline_path="README.md", record_history=False,
            roots=(tmp_path.resolve(),),
        )

    assert (root / "README.md").read_text(encoding="utf-8") == before


def test_a_baseline_may_replace_a_baseline(tmp_path: Path) -> None:
    """Refusing everything would break adoption, which is the feature."""
    from maintainability_audit.mcp_server import audit_repository

    root = _repo(tmp_path)
    (root / "maintainability-agent.json").write_text(
        json.dumps({"version": 1, "analyzers": {"run": False}}), encoding="utf-8",
    )

    for _ in range(2):
        result = audit_repository(
            str(root), action="run", write_baseline=True,
            record_history=False, roots=(tmp_path.resolve(),),
        )
        assert result["audit_ran"] is True

    written = json.loads(
        (root / ".maintainability" / "baseline.json").read_text(encoding="utf-8")
    )
    assert "identities" in written
