"""Class 3 (plan-81dc6870): practice reads a gate wherever it is declared.

Practice measures what is *enforced*. A repo-root-only manifest read missed
`api/pyproject.toml`'s `--cov-fail-under` (CI ran pytest and inherited it),
and the recorded-decisions detector required a basename starting with
`adr`, so `docs/decisions/` — the same practice under another name — did
not count. A gate in a nested package and a decision record under a
different folder name are both still enforcement.

Population, derived from source: the gate manifests (`GATE_MANIFESTS`) and
the decision conventions (`_DECISION_GLOBS`). Unnamed members: the `.adr/`
decision convention and the `setup.cfg` / `tox.ini` nested manifests, each
exercised by the product cases below without being singled out. The AST
guard fails a regression to reading only `root / name`.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from maintainability_audit._practice import (
    _DECISION_GLOBS,
    GATE_MANIFESTS,
    _gate_manifests,
    _recorded_decisions,
    practice_level,
)
from maintainability_audit.config import DEFAULT_CONFIG

SRC = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit" / "_practice.py"
_EXCLUDES = list(DEFAULT_CONFIG["paths"]["exclude_patterns"])


def test_the_gate_and_decision_populations_are_derived_and_not_empty() -> None:
    assert len(GATE_MANIFESTS) >= 5
    assert {"pyproject.toml", "package.json"} <= set(GATE_MANIFESTS)
    assert len(_DECISION_GLOBS) >= 4
    assert any("decision" in glob for glob in _DECISION_GLOBS)


def test_manifest_reading_walks_the_tree_not_only_the_root() -> None:
    """The AST guard for the unnamed member: `_gate_manifests` must walk
    the tree (`rglob`). A regression to `root / name` — the exact defect —
    fails here even though no functional case names the module."""
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    fn = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "_gate_manifests"
    )
    called = {
        n.func.attr for n in ast.walk(fn)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    }
    assert "rglob" in called, "_gate_manifests no longer walks the tree for nested manifests"


@pytest.mark.parametrize("manifest", sorted(GATE_MANIFESTS))
def test_a_nested_gate_manifest_is_found(tmp_path: Path, manifest: str) -> None:
    """Every gate manifest is reachable from a nested package, not only the
    repository root."""
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / manifest).write_text("--cov-fail-under=90\n", encoding="utf-8")
    found = {rel for rel, _path in _gate_manifests(tmp_path, _EXCLUDES)}
    assert f"api/{manifest}" in found


def test_a_vendored_nested_manifest_is_not_read(tmp_path: Path) -> None:
    """`node_modules/**/package.json` is someone else's gate. Excluded
    directories drop out, so a vendored threshold does not lift practice."""
    (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "node_modules" / "pkg" / "package.json").write_text(
        '{"jest":{"coverageThreshold":{}}}\n', encoding="utf-8")
    found = {rel for rel, _path in _gate_manifests(tmp_path, _EXCLUDES)}
    assert not any("node_modules" in rel for rel in found)


@pytest.mark.parametrize("layout,evidence", [
    ("docs/adr", "docs/adr"),
    ("docs/decisions", "docs/decisions"),
    (".adr", ".adr"),
])
def test_a_decision_record_counts_under_any_convention(
    tmp_path: Path, layout: str, evidence: str,
) -> None:
    """`docs/decisions/` and `.adr/` count as recorded decisions, not only
    a folder whose basename starts with `adr`."""
    directory = tmp_path / layout
    directory.mkdir(parents=True)
    (directory / "0001-choice.md").write_text("# a decision\n", encoding="utf-8")
    recorded = _recorded_decisions(tmp_path)
    assert recorded is not None
    assert recorded.relative_to(tmp_path).as_posix().startswith(evidence)


def test_a_nested_coverage_gate_lifts_practice_to_a_gated_level(tmp_path: Path) -> None:
    """The reproduced field miss, end to end: CI runs pytest, the gate lives
    in `api/pyproject.toml`, and practice reads it as gated (>= 4)."""
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
        "jobs:\n  t:\n    steps:\n      - run: python -m pytest\n", encoding="utf-8")
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\naddopts = '--cov-fail-under=90'\n", encoding="utf-8")
    practice = practice_level(tmp_path, DEFAULT_CONFIG)
    assert practice.level >= 4
    assert any(
        signal["signal"] == "coverage-gate" and signal["evidence"] == "api/pyproject.toml"
        for signal in practice.signals
    )
