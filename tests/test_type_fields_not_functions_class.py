"""Claim 4: a type-shaped field is not a function declaration.

D93 stopped ``name: (args) => Type`` inflating the declaration count
inside ``interface`` and ``type`` blocks; the e88b429 fix extended it to
class fields. This is the class across all four block kinds -- class,
`implements`, interface, type -- driven through the real JS/TS extractor
(`_ranges.js_declaration_ranges`), not a single regex. A function-typed
field is a type annotation, not a body; it must not count. Real methods
and object-literal arrow handlers, which carry a body, still do -- the
guard against over-correcting the exclusion into dropping real code.

Unnamed spelling: a **`readonly` (and `public`, `?:`, generic-return)**
class field, which the D93 tests do not use. Each is generated below and
asserted not to count; if the annotation exclusion regressed to only the
bare `name: (a) => T;` spelling, one of these members would start
counting and this test fails.
"""

from __future__ import annotations

import pytest

from maintainability_audit._ranges import js_declaration_ranges


def _names(src: str) -> list[str]:
    ranges, _ = js_declaration_ranges(src.splitlines())
    return [r.name for r in ranges]


# Function-typed fields across the four block kinds and several spellings.
# Derived by combining block wrappers with field spellings, so the
# population is a product, not a hand-list of one example.
_FIELD_SPELLINGS = [
    "handler: (e: Event) => void;",
    "readonly handler: (e: Event) => void;",
    "public handler: (e) => void;",
    "handler?: (e) => void;",
    "handler: (id: string) => Promise<void>;",
]
_BLOCKS = {
    "class": "class C {{\n  {field}\n}}",
    "implements": "class C implements I {{\n  {field}\n}}",
    "interface": "interface I {{\n  {field}\n}}",
    "type": "type T = {{\n  {field}\n}};",
}


def _population() -> list[tuple[str, str, str]]:
    return [
        (block, spelling, tmpl.format(field=spelling))
        for block, tmpl in _BLOCKS.items()
        for spelling in _FIELD_SPELLINGS
    ]


def test_the_type_field_population_is_a_product_and_not_empty() -> None:
    pop = _population()
    assert len(pop) == len(_BLOCKS) * len(_FIELD_SPELLINGS) >= 16


@pytest.mark.parametrize("block,spelling,src", _population())
def test_a_function_typed_field_is_not_counted_as_a_function(
    block: str, spelling: str, src: str,
) -> None:
    names = _names(src)
    assert "handler" not in names, (
        f"a function-typed field counted as a declaration in a {block} block: "
        f"{spelling!r} -> {names}"
    )


def test_real_methods_and_handlers_still_count() -> None:
    """The over-correction guard: bodies still count."""
    assert "onTick" in _names("class C {\n  onTick(n) {\n    return n;\n  }\n}")
    assert "onSave" in _names("const o = {\n  onSave: (a) => { go(); },\n};")
    assert "handler" in _names("class C {\n  handler = (e) => { go(); };\n}")
