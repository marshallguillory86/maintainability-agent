"""Keep Java unscored until a dedicated declaration-range detector exists."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "maintainability_audit"
DECLARATIONS = PACKAGE / "declarations.py"
CONFIG = PACKAGE / "config.py"
RANGES = PACKAGE / "_ranges.py"


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _assignments(tree: ast.Module) -> dict[str, ast.expr]:
    assignments: dict[str, ast.expr] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments[target.id] = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
        ):
            assignments[node.target.id] = node.value
    return assignments


def _strings(node: ast.AST, assignments: dict[str, ast.expr]) -> set[str]:
    values = {
        item.value
        for item in ast.walk(node)
        if isinstance(item, ast.Constant) and isinstance(item.value, str)
    }
    for name in {
        item.id for item in ast.walk(node) if isinstance(item, ast.Name)
    }:
        if name in assignments:
            values |= _strings(assignments[name], assignments)
    return values


def _java_range_functions() -> set[str]:
    return {
        node.name
        for node in _tree(RANGES).body
        if isinstance(node, ast.FunctionDef)
        and "java" in node.name.lower()
        and "range" in node.name.lower()
    }


def _declaration_suffixes() -> set[str]:
    tree = _tree(DECLARATIONS)
    assignments = _assignments(tree)
    return _strings(assignments["DECLARATION_SUFFIXES"], assignments)


def _default_include_extensions() -> set[str]:
    tree = _tree(CONFIG)
    default_config = _assignments(tree)["DEFAULT_CONFIG"]
    for node in ast.walk(default_config):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values, strict=True):
            if isinstance(key, ast.Constant) and key.value == "include_extensions":
                return _strings(value, {})
    raise AssertionError("DEFAULT_CONFIG paths.include_extensions was not found")


@pytest.mark.skipif(
    bool(_java_range_functions()),
    reason="a dedicated Java declaration-range detector now exists",
)
def test_java_is_not_enabled_before_a_range_detector_exists() -> None:
    assert ".java" not in _declaration_suffixes()
    assert ".java" not in _default_include_extensions()


def test_java_is_never_routed_to_the_last_resort_patterns() -> None:
    tree = _tree(DECLARATIONS)
    assignments = _assignments(tree)
    dispatcher = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "declaration_ranges"
    )
    java_detectors = _java_range_functions()
    java_branches = [
        node
        for node in ast.walk(dispatcher)
        if isinstance(node, ast.If) and ".java" in _strings(node.test, assignments)
    ]

    for branch in java_branches:
        branch_tree = ast.Module(body=branch.body, type_ignores=[])
        calls = {
            node.func.id
            for node in ast.walk(branch_tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        names = {node.id for node in ast.walk(branch_tree) if isinstance(node, ast.Name)}
        assert "_regex_function_ranges" not in calls
        assert "FUNC_PATTERNS" not in names
        assert calls & java_detectors, (
            "a .java dispatch branch must call the dedicated Java range detector"
        )

    if ".java" in _declaration_suffixes():
        assert java_branches, (
            ".java is declaration-enabled but declaration_ranges has no Java branch"
        )
