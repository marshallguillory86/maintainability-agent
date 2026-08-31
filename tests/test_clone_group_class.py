"""Class 4 (plan-81dc6870), Part 1: one clone, one finding.

A duplicated block appears as many overlapping windows, each a distinct
fingerprint at consecutive lines. Reported one row per window it was 861
line-items of a single clone (bighound field test); reported one row per
clone it is one finding carrying the occurrence count and the span.
Genuinely separate clones stay separate.
"""

from __future__ import annotations

import ast
from pathlib import Path

from maintainability_audit.duplication import duplicate_blocks

SRC = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit" / "duplication.py"


def test_overlapping_windows_of_one_clone_collapse_to_one_group(tmp_path: Path) -> None:
    """Four saved copies of one 60-line block are one clone group, not the
    ~55 overlapping six-line windows the block decomposes into."""
    block = "\n".join(f"const value_{i} = compute({i}) + offset({i});" for i in range(60))
    for copy in range(4):
        (tmp_path / f"scene_v1.{copy}.0.js").write_text(block + "\n", encoding="utf-8")
    groups = duplicate_blocks(tmp_path, sorted(tmp_path.glob("*.js")), 6)
    assert len(groups) == 1, f"one clone should be one group, got {len(groups)}"
    assert groups[0]["count"] == 4, "the group must count all four copies"
    assert groups[0]["lines"] >= 55, "the group must carry the clone's span, not one window"


def test_two_clones_in_different_files_stay_separate(tmp_path: Path) -> None:
    """The over-correction guard: grouping merges overlapping windows of one
    clone, never two unrelated clones. Different file-sets can never join."""
    alpha = "\n".join(f"alpha_{i}(x, y, z);" for i in range(15))
    beta = "\n".join(f"beta_{i}(p, q, r);" for i in range(15))
    (tmp_path / "one.js").write_text(alpha + "\n", encoding="utf-8")
    (tmp_path / "two.js").write_text(alpha + "\n", encoding="utf-8")
    (tmp_path / "three.js").write_text(beta + "\n", encoding="utf-8")
    (tmp_path / "four.js").write_text(beta + "\n", encoding="utf-8")
    groups = duplicate_blocks(tmp_path, sorted(tmp_path.glob("*.js")), 6)
    assert len(groups) == 2, f"two distinct clones collapsed into one: {groups}"


def test_duplicate_blocks_routes_through_clone_grouping() -> None:
    """The structural guard: `duplicate_blocks` must return clone groups,
    so a regression to one-row-per-window fails here even without a
    functional case naming the sizes."""
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    extractor = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "duplicate_blocks"
    )
    called = {
        node.func.id for node in ast.walk(extractor)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "_clone_groups" in called, "duplicate_blocks no longer groups clones"
