"""Third-party imports must be declared extras. The class, not the instance.

CI died because a test imported ``yaml`` while PyYAML was not in
``pyproject.toml``. Deleting that one import is not the fix: the next
undeclared ``import foo`` fails the same way, after merge.

Rules:

- ``tests/`` may import the stdlib, first-party test helpers, and packages
  named by the ``test`` extra. They may not import ``dev``-only tools
  (ruff, pip-audit, PyYAML). The ``test`` extra is what a thin CI
  install is allowed to be.
- ``tools/`` may import the stdlib and packages named by the ``dev`` extra.
  ``build_catalog.py`` reads upstream YAML; that is why PyYAML is on
  ``dev`` and not on the runtime package.
- ``src/`` is a separate graph (``test_architecture.py``). It must not
  grow a PyYAML import; the catalog is checked-in JSON.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
TOOLS = ROOT / "tools"

# Distribution name -> import names. Empty means the extra is a CLI, not
# an import. Keep this in lockstep with pyproject extras; the test below
# fails if an extra is added and forgotten here.
_EXTRA_IMPORTS: dict[str, frozenset[str]] = {
    "pytest": frozenset({"pytest"}),
    "pytest-cov": frozenset(),
    "jsonschema": frozenset({"jsonschema"}),
    "ruff": frozenset({"ruff"}),
    "pip-audit": frozenset({"pip_audit"}),
    "mcp": frozenset({"mcp"}),
    "PyYAML": frozenset({"yaml"}),
}

# Every declared extra. Tests may import these (mcp tests need `mcp`).
# They may not import yaml: that parser is for catalog regen, not the suite.
_DECLARED_EXTRAS = frozenset({
    "pytest", "pytest-cov", "jsonschema", "ruff", "pip-audit", "mcp", "PyYAML",
})
_TEST_FORBIDDEN = frozenset({"yaml"})


def _top_level(name: str) -> str:
    return name.split(".", 1)[0]


def _imports_in(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(_top_level(alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(_top_level(node.module))
    return names


def _allowed(extras: frozenset[str]) -> set[str]:
    allowed = set(sys.stdlib_module_names)
    for extra in extras:
        allowed.update(_EXTRA_IMPORTS[extra])
    return allowed


def _first_party(name: str) -> bool:
    if name == "maintainability_audit" or name.startswith("test_"):
        return True
    if name in {"_ast_reading", "_mcp_fixtures", "_scoring_fixtures", "conftest"}:
        return True
    return any(path.stem == name for path in TOOLS.rglob("*.py"))


def _offenders(root: Path, extras: frozenset[str], *, forbid: frozenset[str] = frozenset()) -> list[str]:
    allowed = _allowed(extras) - set(forbid)
    found: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if path.name == "test_declared_imports.py":
            continue
        for name in sorted(_imports_in(path)):
            if name in allowed or _first_party(name):
                continue
            found.append(f"{path.relative_to(ROOT)}: import {name}")
    return found


def test_pyproject_extras_are_accounted_for() -> None:
    """A new extra nobody mapped is how an undeclared import sneaks back."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for extra in _DECLARED_EXTRAS:
        assert extra in text, f"{extra} is in the import map but not in pyproject.toml"
    test_line = next(line for line in text.splitlines() if line.startswith("test = "))
    assert "PyYAML" not in test_line, (
        "PyYAML on the test extra would pull a catalog-regen parser into every test install"
    )


def test_tests_do_not_import_undeclared_or_catalog_yaml() -> None:
    offenders = _offenders(TESTS, _DECLARED_EXTRAS, forbid=_TEST_FORBIDDEN)
    assert not offenders, "undeclared third-party import in tests:\n" + "\n".join(offenders)


def test_tools_only_import_declared_extras() -> None:
    offenders = _offenders(TOOLS, _DECLARED_EXTRAS)
    assert not offenders, "undeclared third-party import in tools:\n" + "\n".join(offenders)


def test_the_shipped_package_does_not_import_yaml() -> None:
    """Runtime stays dependency-light. The catalog is checked-in JSON."""
    src = ROOT / "src" / "maintainability_audit"
    hits = [
        f"{path.relative_to(ROOT)}"
        for path in src.glob("*.py")
        if "yaml" in _imports_in(path)
    ]
    assert not hits, "src imported yaml:\n" + "\n".join(hits)
