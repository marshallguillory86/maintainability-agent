"""D93/D94/D95: what the JS and TS scanner counts as a declaration.

Three findings against D86, which closed the same morning. Each is the
same shape: the fix was real, and its closer used the one instance the
fix happened to handle.

* D93 -- TypeScript writes `onSave: (a: string) => void;` for an
  interface member, which is the object-literal shape D86 taught the
  scanner to find. Type members became functions, and a population that
  is not there bought a verified grade.
* D94 -- masking blanks string literals before any pattern runs, so a
  quoted key is gone by the time the property pattern looks for a name.
  D86's example was unquoted.
* D95 -- `_VALUE_MAY_BEGIN` decides where a regex literal may start. It
  lists `return`, the keyword D86's closer used, and not `)`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from maintainability_audit import declarations
from maintainability_audit._masking import mask_lines
from maintainability_audit._metrics_types import COMPLEXITY_RE
from maintainability_audit.config import DEFAULT_CONFIG

THRESHOLDS = DEFAULT_CONFIG["thresholds"]


def _names(source: str, tmp_path: Path, suffix: str = ".ts") -> list[str]:
    path = tmp_path / f"sample{suffix}"
    path.write_text(source, encoding="utf-8")
    found = declarations.detect_functions(
        tmp_path, path, source.splitlines(), THRESHOLDS)
    return [metric.name for metric in found]


TYPE_BLOCKS = [
    pytest.param(
        "interface Api {\n"
        "  onSave: (a: string) => void;\n"
        "  onLoad: (b: number) => Promise<void>;\n"
        "}\n"
        "export function real(x: string) { if (x) { return 1; } return 0; }\n",
        id="interface",
    ),
    pytest.param(
        "export type Handler = {\n"
        "  onThing: (x: number) => void;\n"
        "};\n"
        "export function real(x: string) { if (x) { return 1; } return 0; }\n",
        id="type alias",
    ),
    pytest.param(
        "declare interface Api {\n"
        "  onSave: (a: string) => void;\n"
        "}\n"
        "export function real(x: string) { if (x) { return 1; } return 0; }\n",
        id="declare interface",
    ),
]


@pytest.mark.parametrize("source", TYPE_BLOCKS)
def test_type_members_are_not_counted_as_declarations(
    source: str, tmp_path: Path,
) -> None:
    """D93: a population that is not there can buy a verified grade.

    Forty files of real functions scored `insufficient`. The same forty
    with an interface of three typed arrows each reported 160
    declarations, crossed the population floor, diluted band pressure
    fourfold and issued a verified C.
    """
    assert _names(source, tmp_path) == ["real"], (
        "a TypeScript type member was counted as a function; the "
        "declaration population is inflated by things nobody wrote a "
        f"body for: {_names(source, tmp_path)}"
    )


def test_a_real_object_literal_member_is_still_found(tmp_path: Path) -> None:
    """D93's fix must not undo D86."""
    source = (
        "const handlers = {\n"
        "  onSave: (a) => { if (a) { return 1; } return 2; },\n"
        "};\n"
    )
    assert _names(source, tmp_path, ".js") == ["onSave"]


QUOTED_KEYS = [
    ('  "onSave": (a) => { if (a) { return 1; } return 2; },', "onSave"),
    ("  'onLoad': function (b) { if (b) { return 1; } return 2; },", "onLoad"),
    ('  "on-error"(e) { if (e) { return 1; } return 2; },', "on-error"),
]


@pytest.mark.parametrize(
    ("member", "expected"), QUOTED_KEYS,
    ids=[expected for _member, expected in QUOTED_KEYS],
)
def test_a_string_keyed_member_is_a_declaration(
    member: str, expected: str, tmp_path: Path,
) -> None:
    """D94: masking removed the name before the pattern looked for it.

    `on-error` is not a valid identifier, so that key *must* be quoted.
    A scanner that only sees unquoted keys cannot claim to read the
    file's functions.
    """
    source = f"const handlers = {{\n{member}\n}};\n"
    assert _names(source, tmp_path, ".js") == [expected]


def test_a_sibling_function_does_not_stand_in_for_the_handlers(
    tmp_path: Path,
) -> None:
    """D86's original shape, reached through quoted keys.

    Whatever loose `function` sat beside the handlers was what got
    scored, and the file was reported as examined.
    """
    source = (
        "const handlers = {\n"
        '  "on-error"(e) { if (e) { return 1; } return 2; },\n'
        '  "onSave": (a) => { if (a) { return 1; } return 2; },\n'
        "};\n"
        "function helper() { return 1; }\n"
    )
    found = _names(source, tmp_path, ".js")
    assert found != ["helper"], "only the sibling was scored"
    assert set(found) == {"on-error", "onSave", "helper"}, found


REGEX_POSITIONS = [
    ("  if (x) /a?b?c?d?e?/;", 2, "a regex after a control paren is not code"),
    ("  while (a) /b?c?/;", 2, "the same for while"),
    ("  return /a?b?c?d?e?/;", 1, "the case D86 tested still holds"),
    ("  const y = f(x) / 2;", 1, "division after a call is not a regex"),
    ("  const z = (a + b) / 2;", 1, "division after a grouping paren"),
]


@pytest.mark.parametrize(
    ("line", "expected", "why"), REGEX_POSITIONS,
    ids=[why for _line, _expected, why in REGEX_POSITIONS],
)
def test_a_regex_literal_is_masked_wherever_a_value_may_begin(
    line: str, expected: int, why: str,
) -> None:
    """D95: `)` is the position a character alone cannot decide.

    `if (x) /re/` opens a value; `f(x) / 2` is division. Getting this
    wrong in either direction is a wrong number: the first scored 7
    against a McCabe 2, and a blanket rule would silently drop real
    division operators out of the complexity count.
    """
    masked = mask_lines([line])[0]
    complexity = 1 + len(COMPLEXITY_RE.findall(masked))
    assert complexity == expected, f"{why}: scored {complexity}, expected {expected}"
