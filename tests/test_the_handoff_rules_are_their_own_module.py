"""Who gets handed what lives in one module, and only one (D208).

D207 pushed `_work_order.py` to 752 lines against this repository's own
750-line gate. It came back under by shortening a docstring, which is
not a fix: the next change needed ten more lines, and the pressure to
pass a length gate is pressure to delete the comments that record why a
rule exists. Two had already been trimmed for length that day.

The split is the fix, and **its falsifier is the boundary rather than a
behaviour**, because a pure move changes no behaviour. What can be
falsified is that the seam exists and runs one way:

* the handoff rules are defined in `_handoff` and nowhere else, so
  extending one of them cannot be done in half the places again, and
* `_work_order` imports nothing from `_handoff`, which is what makes
  this a boundary rather than a shuffle — a re-export back into
  `_work_order` would spare every caller an edit and restore the cycle
  the split exists to prevent.

`architecture.md` had already carved this out in prose: presentation may
import *"`_work_order`'s presentation-facing prompt selection"*, naming
a module that did not exist. The population below is `_handoff`'s own
public surface, read from the module, so a rule added there later is
covered without editing this file.
"""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"


def _defined(module: str) -> set[str]:
    """Top-level names a module defines, read from its source."""
    tree = ast.parse((PACKAGE / f"{module}.py").read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return names


def _imports_of(module: str) -> set[str]:
    """Internal modules this one imports, at any level."""
    tree = ast.parse((PACKAGE / f"{module}.py").read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level and node.module:
            found.add(node.module)
    return found


def test_the_handoff_rules_are_defined_once() -> None:
    """The population is `_handoff`'s public surface, not a list typed here.

    A name defined in both modules is the state this split removed: one
    rule with two homes, extended in whichever the author had open.
    """
    handoff = {name for name in _defined("_handoff") if not name.startswith("_")}
    work_order = _defined("_work_order")

    assert handoff, "`_handoff` defines no public names, so this sweeps nothing"
    both = sorted(handoff & work_order)

    assert not both, (
        f"these handoff rules are defined in `_work_order` as well: {both}"
    )


def test_the_boundary_runs_one_way() -> None:
    """`_work_order` may not import `_handoff`.

    A re-export would spare every caller an edit and restore exactly the
    cycle the split exists to prevent — which is also why the callers
    were repointed rather than given a compatibility shim.
    """
    assert "_handoff" not in _imports_of("_work_order"), (
        "`_work_order` imports `_handoff`; the split is a shuffle, not a boundary"
    )
    assert "_work_order" in _imports_of("_handoff"), (
        "`_handoff` no longer reads `_work_order`, so the dependency it was "
        "split away from has moved rather than been directed"
    )


def test_neither_module_sits_on_its_own_file_gate() -> None:
    """The gate that started this, asserted on both halves.

    Read from the repository's own configuration rather than a number
    repeated here: this project grades other repositories on the
    thresholds it publishes, and a test carrying its own copy could
    disagree with the audit that failed at 752.
    """
    import json

    config = json.loads(
        (PACKAGE.parents[1] / "maintainability-agent.json").read_text(encoding="utf-8")
    )
    limit = config["thresholds"]["max_file_lines"]
    for module in ("_work_order", "_handoff"):
        lines = len((PACKAGE / f"{module}.py").read_text(encoding="utf-8").splitlines())

        assert lines <= limit, f"{module}.py is {lines} lines against a limit of {limit}"
