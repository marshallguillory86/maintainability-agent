"""D33: every named exception is either a declared refusal or excluded on purpose.

A reviewer eyeballing ``ANTICIPATED_REFUSALS`` got the set wrong twice
in one night, in opposite directions. This file derives the product's
named exception types from the package and demands each one is either
in the tuple the transport excepts, or named here with a reason. Adding
a sixth type and touching neither fails the build.
"""

from __future__ import annotations

import ast
from pathlib import Path

from maintainability_audit.mcp_server import ANTICIPATED_REFUSALS

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"
MCP_SERVER = PACKAGE / "mcp_server.py"

# Exception subclasses that must not be translated. A reason is the
# proof; an empty string is not a classification.
EXCLUSIONS: dict[str, str] = {
    "EvidenceValidationError": (
        "on the MCP tool path the report is built internally, so a "
        "failure is an internal bug; the crash path is right to withhold it"
    ),
    "UnsupportedReportSchema": (
        "subclass of EvidenceValidationError; same exclusion"
    ),
    "SkillDrift": (
        "CLI --install-skill only; never raised through the MCP tool "
        "or resource seams"
    ),
}

_EXCEPTION_ROOTS = frozenset(
    {"BaseException", "Exception", "ValueError", "RuntimeError", "Error"}
)


def _base_names(node: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
    return names


def _named_exceptions() -> dict[str, str]:
    """Every class in the package that inherits from Exception, by name.

    Walks the source, not the import graph, so a type added in a module
    nobody imports still has to be classified.
    """
    bases_of: dict[str, set[str]] = {}
    defined_in: dict[str, str] = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases_of[node.name] = _base_names(node)
                defined_in[node.name] = str(path.relative_to(PACKAGE.parent.parent))

    named: set[str] = set()
    changed = True
    while changed:
        changed = False
        for name, bases in bases_of.items():
            if name in named:
                continue
            if bases & _EXCEPTION_ROOTS or bases & named:
                named.add(name)
                changed = True
    return {name: defined_in[name] for name in sorted(named)}


def _except_handler_types(tree: ast.AST) -> tuple[list[str], list[tuple[str, ...]]]:
    """Except names, and except-tuples, from one module."""
    names: list[str] = []
    groups: list[tuple[str, ...]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler) or node.type is None:
            continue
        if isinstance(node.type, ast.Name):
            names.append(node.type.id)
        elif isinstance(node.type, ast.Tuple):
            groups.append(tuple(
                elt.id for elt in node.type.elts if isinstance(elt, ast.Name)
            ))
    return names, groups


def test_every_named_exception_is_a_declared_refusal_or_excluded() -> None:
    """A sixth type added tomorrow, with nobody touching the tuple, fails here.

    The tuple is the MCP translation set. The derivation is every named
    exception in the package, so SkillDrift (CLI-only) and
    EvidenceValidationError (internal on this path) have to be excluded
    with a reason rather than silently omitted.
    """
    discovered = _named_exceptions()
    anticipated = {cls.__name__ for cls in ANTICIPATED_REFUSALS}

    empty_reasons = [name for name, reason in EXCLUSIONS.items() if not reason.strip()]
    assert not empty_reasons, (
        "an exclusion without a reason is not a classification: "
        f"{empty_reasons}"
    )

    overlap = anticipated & set(EXCLUSIONS)
    assert not overlap, (
        f"classified as both a refusal and an exclusion: {sorted(overlap)}"
    )

    missing = set(EXCLUSIONS) - set(discovered)
    assert not missing, (
        f"exclusions that are not named exception types in the package: {sorted(missing)}"
    )

    stale = anticipated - set(discovered)
    assert not stale, (
        f"ANTICIPATED_REFUSALS names types the package does not define: {sorted(stale)}"
    )

    unclassified = set(discovered) - anticipated - set(EXCLUSIONS)
    assert not unclassified, (
        "named exception types with no classification — add each to "
        "ANTICIPATED_REFUSALS or to EXCLUSIONS with a reason: "
        + ", ".join(f"{name} ({discovered[name]})" for name in sorted(unclassified))
    )

    assert anticipated == set(discovered) - set(EXCLUSIONS), (
        "ANTICIPATED_REFUSALS is not exactly the discovered types minus "
        f"the exclusions. tuple={sorted(anticipated)} "
        f"expected={sorted(set(discovered) - set(EXCLUSIONS))}"
    )
    assert all(issubclass(cls, BaseException) for cls in ANTICIPATED_REFUSALS)


def test_the_transport_excepts_the_named_tuple_not_a_copy() -> None:
    """The three seams must except ANTICIPATED_REFUSALS, not a stale list.

    Membership in the tuple is not enough if a copy at an ``except``
    site omits a type. The night's second miss — StaleBaseline and
    PolicyError dropped from the tuple — would have been invisible at
    those sites if they listed three types by hand.
    """
    tree = ast.parse(MCP_SERVER.read_text(encoding="utf-8"), filename=str(MCP_SERVER))
    caught, listed = _except_handler_types(tree)
    anticipated_names = {cls.__name__ for cls in ANTICIPATED_REFUSALS}
    # A hand-written subset of the tuple is the night's second miss
    # wearing a different coat. `except (PathNotAllowed, ValueError)` in
    # the setup resolver is not that: ValueError is not an anticipated
    # name, and that handler swallows so the tool body can raise.
    stale = [group for group in listed if group and set(group) <= anticipated_names]

    assert caught.count("ANTICIPATED_REFUSALS") >= 3, (
        "the tool, the report resource and its security validator must "
        f"except ANTICIPATED_REFUSALS; found {caught}"
    )
    assert not stale, (
        "an except site lists anticipated types by hand instead of the "
        f"named tuple: {stale}"
    )
