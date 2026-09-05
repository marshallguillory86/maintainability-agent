"""Decision 9: the audited tree does not choose what this process execs.

SECURITY.md says the agent does not execute code from the repository
under audit, and that the sole exception is the operator's opt-in test
command. D39/D92 closed that claim by walking adapters. A spawn that is
not an adapter — a path the tree can plant — is the same claim, still
open.

Population: every ``Invocation(...)`` and ``subprocess.run(...)`` in
``src/maintainability_audit``. A module that both builds a
``node_modules`` path and passes a non-constant argv[0] to ``Invocation``
is a tree-chosen binary, unless the enclosing function consults
``suite_opted_in``.

*Mutation:* a planted ``node_modules/.bin/tsc`` under a ``tsconfig.json``
tree. The AST sweep does not name ``local_tsc_analysis``.
"""

from __future__ import annotations

import ast
import stat
from pathlib import Path

from maintainability_audit import _semantic_ts

SRC = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"


def _is_name(func: ast.expr, *names: str) -> bool:
    if isinstance(func, ast.Name):
        return func.id in names
    if isinstance(func, ast.Attribute):
        return func.attr in names
    return False


def _call_kwarg(call: ast.Call, name: str) -> ast.expr | None:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _argv0(call: ast.Call) -> ast.expr | None:
    """First argv element of an Invocation or subprocess.run, if visible."""
    if _is_name(call.func, "Invocation"):
        argv = call.args[0] if call.args else _call_kwarg(call, "argv")
        if isinstance(argv, ast.Tuple) and argv.elts:
            return argv.elts[0]
        return None
    if _is_name(call.func, "run") and isinstance(call.func, ast.Attribute):
        # subprocess.run([...]) — not _runner.run.
        if not (isinstance(call.func.value, ast.Name) and call.func.value.id == "subprocess"):
            return None
        if not call.args:
            return None
        first = call.args[0]
        if isinstance(first, ast.List) and first.elts:
            return first.elts[0]
    return None


def _enclosing_function(tree: ast.AST, node: ast.AST) -> ast.FunctionDef | None:
    parent: dict[ast.AST, ast.AST] = {}
    for current in ast.walk(tree):
        for child in ast.iter_child_nodes(current):
            parent[child] = current
    here: ast.AST | None = node
    while here is not None:
        if isinstance(here, ast.FunctionDef):
            return here
        here = parent.get(here)
    return None


def _calls_suite_opted_in(fn: ast.FunctionDef) -> bool:
    return any(isinstance(n, ast.Call) and _is_name(n.func, "suite_opted_in") for n in ast.walk(fn))


def _spawns() -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _is_name(node.func, "Invocation") or (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "run"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "subprocess"
            ):
                found.append((path.name, node.lineno))
    return found


def _tree_bin_modules() -> list[str]:
    """Modules that build a node_modules path and pass it to Invocation.

    argv[0] as ``self.executable``, a string constant, or a splat is the
    catalog/PATH case. A bare Name is a path the tree could have planted.
    ``suite_opted_in`` is Decision 9's disclosed exception.
    """
    offenders: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        has_node_modules_component = any(isinstance(n, ast.Constant) and n.value == "node_modules" for n in ast.walk(tree))
        if not has_node_modules_component:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not _is_name(node.func, "Invocation"):
                continue
            argv0 = _argv0(node)
            if argv0 is None or isinstance(argv0, (ast.Constant, ast.Attribute, ast.Starred)):
                continue
            fn = _enclosing_function(tree, node)
            if fn is not None and _calls_suite_opted_in(fn):
                continue
            offenders.append(f"{path.name}:{node.lineno}")
    return offenders


def test_the_spawn_population_is_derived_and_not_empty() -> None:
    spawns = _spawns()
    assert spawns, "no Invocation or subprocess.run in src/maintainability_audit; the Decision 9 sweep matched nothing"


def test_no_module_spawns_a_binary_from_node_modules() -> None:
    """A tree-chosen argv[0] is executing the audited repository.

    *Mutation:* ``_semantic_ts._resolve_tsc`` preferring
    ``node_modules/.bin/tsc``. This assertion does not name that
    function; it fails any module that builds that path and then
    Invokes a Name.
    """
    offenders = _tree_bin_modules()
    assert not offenders, (
        "Decision 9: these Invocation argv[0] values are resolved from "
        "the audited tree's node_modules, which is the tree choosing "
        f"what runs: {offenders}"
    )


def test_a_planted_tsc_in_the_tree_is_not_executed(tmp_path: Path) -> None:
    """Live half. The AST sweep can miss a helper that builds the path.

    A hostile tree does not need TypeScript: a tsconfig.json and a
    writable node_modules/.bin/tsc are enough. The planted script is
    not named in the assertion above.
    """
    bindir = tmp_path / "node_modules" / ".bin"
    bindir.mkdir(parents=True)
    marker = tmp_path / "PWNED"
    planted = bindir / "tsc"
    planted.write_text(
        f"#!/bin/sh\necho PWNED_RAN > '{marker}'\necho 'a.ts(1,1): error TS0000: planted'\n",
        encoding="utf-8",
    )
    planted.chmod(planted.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")
    (tmp_path / "a.ts").write_text("export const x = 1\n", encoding="utf-8")

    _semantic_ts.local_tsc_analysis(tmp_path)

    assert not marker.exists(), (
        "planted node_modules/.bin/tsc ran during local_tsc_analysis; "
        "the audited tree executed code. Decision 9 / SECURITY.md say "
        "the sole tree-execution path is the opt-in test command."
    )
