"""Claim 2: every git spawn is read-only toward the audited tree.

D92 and the e88b429 backfill escape are the same class: a ``git``
subprocess run against an untrusted tree must carry ``READ_ONLY_GIT_CONFIG``
(no housekeeping writes, no code execution from `.git/config`) and the
``attr.tree`` empty-tree guard (no `.gitattributes` filter/textconv driver
runs). The population is not a hand-list: it is every argv in the source
whose head is the literal ``"git"``, found by AST walk. A new git spawn
that forgets a guard fails here whether or not this file names it.

The one spawn exempt from ``attr.tree`` is the object-format probe
(`git rev-parse --show-object-format`): it *computes* the empty-tree hash
attr.tree needs, so it cannot consume it, and it reads no tree content or
attributes. It is identified by its subcommand, not its location, so
moving it does not silently widen the exemption.

Unnamed member: **the backfill spawn** (`_backfill._git`, a `worktree
add`). It lives outside `git_tools`, which is exactly how the D92 sweep
missed it. Strip its ``_attr_tree_config`` splat and this guard fails on
that argv, with no functional worktree test needed to notice.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"


def _is_git_argv(arg: ast.expr) -> bool:
    return (isinstance(arg, ast.List) and bool(arg.elts)
            and isinstance(arg.elts[0], ast.Constant) and arg.elts[0].value == "git")


def _splat_name(elt: ast.Starred) -> str:
    value = elt.value
    if isinstance(value, ast.Name):
        return value.id
    if isinstance(value, ast.Call):
        return getattr(value.func, "id", getattr(value.func, "attr", ""))
    return ""


def _parse_git_argv(arg: ast.List) -> tuple[list[str], list[str]]:
    splats = [_splat_name(e) for e in arg.elts if isinstance(e, ast.Starred)]
    consts = [e.value for e in arg.elts
              if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    return splats, consts


def _git_spawns() -> list[tuple[str, int, list[str], list[str]]]:
    """(file, line, splatted guard names, constant string args) per git argv."""
    spawns = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            git_args = [a for a in getattr(node, "args", []) if _is_git_argv(a)] \
                if isinstance(node, ast.Call) else []
            for arg in git_args:
                splats, consts = _parse_git_argv(arg)
                spawns.append((path.name, node.lineno, splats, consts))
    return spawns


def _is_object_format_probe(consts: list[str]) -> bool:
    return "rev-parse" in consts and "--show-object-format" in consts


def test_the_git_spawn_population_is_derived_and_not_empty() -> None:
    spawns = _git_spawns()
    assert len(spawns) >= 2, f"expected several git spawns, found {spawns}"


def test_every_git_spawn_is_read_only_config() -> None:
    """No git argv touches the tree without READ_ONLY_GIT_CONFIG."""
    missing = [
        f"{name}:{line}"
        for name, line, splats, _consts in _git_spawns()
        if "READ_ONLY_GIT_CONFIG" not in splats
    ]
    assert not missing, f"git spawns without READ_ONLY_GIT_CONFIG: {missing}"


def test_every_content_git_spawn_carries_the_attr_tree_guard() -> None:
    """Every git spawn except the object-format probe carries attr.tree.

    A spawn that only pins `gc.auto` (READ_ONLY_GIT_CONFIG) but omits
    `_attr_tree_config` still runs a `.gitattributes` clean/textconv driver
    -- the backfill hole e88b429 found. The probe is the sole exemption
    because it reads no attributes.
    """
    offenders = [
        f"{name}:{line}"
        for name, line, splats, consts in _git_spawns()
        if "_attr_tree_config" not in splats and not _is_object_format_probe(consts)
    ]
    assert not offenders, (
        f"git spawns that run tree attributes without the attr.tree guard: {offenders}"
    )
