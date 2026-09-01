"""Class C (Grok 63ab820): a JS/TS declaration counts iff it has a body.

Two directions, one rule -- a declaration is code to measure only when it
carries a body (a block ``{``) or an arrow value (``=>``). ``_ranges_js``
mistook both:

* type-only signatures were counted. ``declare function f(): void;``, a
  TypeScript overload signature, an abstract method: each has the shape of
  a declaration and no body behind it, so counting one mints a member with
  nothing to measure -- the same absence-as-population D93 refused for
  type-shaped fields, one layer over.
* real bodies were dropped. A single-line method ``f(x) { return x }`` was
  rejected because ``_is_method`` required the line to *end* in ``{``; an
  ``override`` method was invisible because ``override`` was not a stripped
  modifier; a private ``#method`` was invisible because ``#`` is not an
  identifier character.

Both populations are products driven through the real extractor
(`js_declaration_ranges`), not one regex each. Unnamed members: the
**abstract method** and the **overload signature paired with its
implementation** on the type-only side; the **single-line ``#private``**
and the **``override``** method on the real-body side -- spellings the
D93/e88b429 tests never used, each generated below.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from maintainability_audit._ranges_js import js_declaration_ranges

SRC = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"


def _names(src: str) -> list[str]:
    ranges, _ = js_declaration_ranges(src.splitlines())
    return [r.name for r in ranges]


# --- type-only signatures: shape of a declaration, no body to measure ----
# `sig` names its member `m`; `impl` is the same name with a real body, so
# a paired file must count exactly one, never the signature as well.
_TYPE_ONLY = {
    "declare-function": ("declare function m(): void;", "function m() { return; }"),
    "overload-signature": ("function m(x: string): string;", "function m(x: any) { return x; }"),
    "abstract-method": ("class C {\n  abstract m(): void;\n}", "class C {\n  m() { return 1; }\n}"),
    "interface-method": ("interface I {\n  m(): void;\n}", "class C {\n  m() { return 1; }\n}"),
}


def test_the_type_only_population_is_derived_and_not_empty() -> None:
    assert len(_TYPE_ONLY) >= 4


@pytest.mark.parametrize("kind", sorted(_TYPE_ONLY))
def test_a_type_only_signature_is_not_counted(kind: str) -> None:
    sig, _impl = _TYPE_ONLY[kind]
    assert "m" not in _names(sig), f"{kind}: a bodyless signature counted -> {_names(sig)}"


@pytest.mark.parametrize("kind", sorted(_TYPE_ONLY))
def test_a_signature_beside_its_implementation_counts_once(kind: str) -> None:
    sig, impl = _TYPE_ONLY[kind]
    # The signature line, then the implementation of the same name. Only
    # the body is a declaration; the overload/ambient line is not.
    combined = sig.rsplit("}", 1)[0] + "\n" + impl if sig.strip().endswith("}") else sig + "\n" + impl
    names = _names(combined)
    assert names.count("m") == 1, f"{kind}: expected one 'm', got {names}"


# --- real bodies: each must count, across modifier and body spellings -----
_REAL_BODIES = {
    "single-line": "f(x) { return x; }",
    "override": "override f() { return 1; }",
    "private": "#f() { return 2; }",
    "private-single-line": "#f(a) { return a; }",
    "static": "static f(y) {\n    return y + 1;\n  }",
    "generator": "*f() { yield 1; }",
    "arrow-field": "f = () => run();",
    "empty-body": "f() {}",
}


def test_the_real_body_population_is_derived_and_not_empty() -> None:
    assert len(_REAL_BODIES) >= 6


@pytest.mark.parametrize("kind", sorted(_REAL_BODIES))
def test_a_real_body_member_is_counted(kind: str) -> None:
    src = "class C {\n  " + _REAL_BODIES[kind] + "\n}"
    names = _names(src)
    # The member is named `f` or, when private, `#f`; either way the class
    # body yields a second declaration beyond `C` itself.
    members = [name for name in names if name != "C"]
    assert members == ["f"] or members == ["#f"], (
        f"{kind}: a real body was not counted -> {names}"
    )


def test_a_call_expression_is_still_not_a_declaration() -> None:
    """The over-correction guard: widening the body test must not start
    counting a bare call that shares the ``name(`` shape."""
    assert _names("doThing(x);") == []
    assert _names("useEffect(() => {\n  go();\n});") == []


def test_the_bare_signature_skip_is_wired_into_the_extractor() -> None:
    """Structural guard for the unnamed member: even with no functional
    case naming it, deleting the bodyless-signature skip from
    ``js_declaration_ranges`` fails here."""
    tree = ast.parse((SRC / "_ranges_js.py").read_text(encoding="utf-8"))
    extractor = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "js_declaration_ranges"
    )
    calls = {
        n.func.id for n in ast.walk(extractor)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    assert "_is_bare_signature" in calls, (
        "js_declaration_ranges no longer skips bodyless signatures"
    )
