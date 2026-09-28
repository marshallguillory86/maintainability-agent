"""Did the diff weaken the tests that are supposed to judge it?

Decision 12: a deterministic check is only evidence when the work under
review could not author the record. The tests in a remediating diff are a
record the agent *can* write — the pairing rule lets a test file into
scope so the failing test can ship with its fix, and that same door lets
an agent make the suite pass by making it unable to fail. Alias a matcher,
write `assert True`, delete the assertion, skip the test, swallow the
`AssertionError`: the build goes green and nothing was fixed.

This reads the diff's test files for those shapes. It is still **shape,
never correctness** — whether a changed assertion expects the *right*
value is a judgment this package does not make, and a wrong assertion
written before the work began leaves no trace here at all (Decision 12's
third home). The precision bar was frozen before this module existed:
`tests/test_oracle_weakening_precision_bar.py`, zero false alarms on its
legitimate edits. A check that cries wolf is switched off, so every rule
below is narrow on purpose.
"""

from __future__ import annotations

import re
from typing import Any

from ._metrics_types import is_test_path

Lines = dict[str, list[tuple[int, str]]]

#: Markers that switch a checker off rather than satisfy it. Per language,
#: because the vocabulary differs and a single regex over all of them
#: matches prose: "# type: ignore" in a docstring explaining the convention
#: is not a suppression, and neither is this comment.
#:
#: Deliberately narrow. A marker here has to be a real directive that a
#: real tool obeys; guessing wider would report ordinary comments as
#: evasion, and a check that cries wolf is a check that gets switched off —
#: the same reasoning as the test-pairing rule above.
SUPPRESSION_MARKERS: tuple[tuple[str, str], ...] = (
    (r"#\s*noqa\b", "noqa"),
    (r"#\s*type:\s*ignore\b", "type: ignore"),
    (r"#\s*pragma:\s*no\s*cover\b", "pragma: no cover"),
    (r"#\s*nosec\b", "nosec"),
    (r"//\s*eslint-disable", "eslint-disable"),
    (r"/\*\s*eslint-disable", "eslint-disable"),
    (r"//\s*@ts-(ignore|expect-error)\b", "ts-ignore"),
    (r"@SuppressWarnings\b", "SuppressWarnings"),
    (r"//\s*NOSONAR\b", "NOSONAR"),
    (r"#\s*pylint:\s*disable\b", "pylint: disable"),
    (r"@pytest\.mark\.(skip|skipif|xfail)\b", "skipped test"),
    (r"@unittest\.skip(If|Unless)?\b", "skipped test"),
    (r"\bit\.skip\(|\bdescribe\.skip\(", "skipped test"),
    (r"@Disabled\b", "disabled test"),
    (r"@Ignore\b", "ignored test"),
)

_SUPPRESSION = tuple(
    (re.compile(pattern, re.IGNORECASE), label) for pattern, label in SUPPRESSION_MARKERS
)


def _is_quoted(text: str, start: int) -> bool:
    """Whether the marker at `start` is being *mentioned* rather than used.

    A directive is never immediately preceded by a quote or a backtick,
    and never sits inside an open backtick span. Prose about directives
    does both constantly — this file's own comments do it, and so does
    the docstring that says a marker in a docstring is not a suppression.
    """
    prefix = text[:start]
    if prefix[-1:] in {"`", "'", '"'}:
        return True
    return prefix.count("`") % 2 == 1


def markers_in(text: str) -> str | None:
    """The suppression this line declares, or None if it only mentions one.

    The one place that question is answered, because it is asked twice —
    by the conformance record after a change, and by the pre-commit scan
    before one — and a rule that disagrees with itself between the hook
    and the gate blocks commits CI would pass.

    D108: the marker set's own comment promised that "`# type: ignore` in
    a docstring explaining the convention is not a suppression", and for
    four versions nothing enforced it. The `--staged` scan found it
    immediately, by blocking the commit of a docstring containing the
    words `# noqa` — the first time the rule ran somewhere a false
    positive cost something.

    Still narrow, and deliberately: a marker written into ordinary prose
    with no quoting around it is still reported. Quoting is the signal
    that is actually reliable, and widening past it starts guessing at
    English. This paragraph cannot give the example it would like to,
    because writing one unquoted would report this line — which is the
    rule demonstrating itself, and the reason the sentence stays abstract.
    """
    for pattern, label in _SUPPRESSION:
        match = pattern.search(text)
        if match and not _is_quoted(text, match.start()):
            return label
    return None


#: An assertion that cannot fail.
_TAUTOLOGIES = tuple(re.compile(p) for p in (
    r"^assert\s+(?:True|1|not\s+False)\s*(?:,.*)?$",
    r"^assert\s+([\w.]+)\s*==\s*\1\s*(?:,.*)?$",
    r"\bassertTrue\(\s*(?:True|true|1)\s*\)",
    r"\bexpect\(\s*(?:true|1)\s*\)\.(?:toBe|toEqual|toBeTruthy)\(\s*(?:true|1)?\s*\)",
    r"\bexpect\(\s*([\w.]+)\s*\)\.(?:toBe|toEqual|toStrictEqual)\(\s*\1\s*\)",
))

#: The assertion API replaced, so every assertion through it passes.
#: Assignment only — `assert self.assertEqual == original` compares.
_ALIASES = tuple(re.compile(p) for p in (
    r"^(?:self\.|(?:\w+\.)+)?assert\w*\s*=(?!=)",
    r"\bsetattr\([^,]+,\s*[\"']assert\w*[\"']",
    r"^(?:(?:const|let|var)\s+)?expect\s*=(?!=)",
    r"\bexpect\.extend\(\s*\{[^}]*\b(?:toBe|toEqual|toStrictEqual|toBeTruthy|toThrow|toHaveBeenCalled\w*)\s*:",
    r"\bjest\.mock\(\s*[\"'](?:expect|assert|chai|@jest/expect)[\"']",
))

#: A skip written as a call rather than a directive. Read only here, not
#: by the pre-commit marker scan: `pytest.skip("mypy did not run")` is an
#: ordinary guard in a suite, and only in a remediating diff's test file is
#: it evidence about the change.
_SKIP_CALLS = re.compile(r"\bpytest\.skip\(|\bx(?:it|describe|test)\(|\b(?:it|describe|test)\.skip\(|\bthis\.skip\(\)")

#: A failing assertion caught and discarded.
_SWALLOWED = re.compile(r"^except\s+\(?\s*AssertionError\b")

#: Each line-level shape, in the order a line is tested against them.
_SHAPES = (
    ("skipped or suppressed test", (_SKIP_CALLS,)),
    ("assertion that cannot fail", _TAUTOLOGIES),
    ("assertion API replaced", _ALIASES),
    ("failing assertion swallowed", (_SWALLOWED,)),
)

#: A line that asserts, for the count of assertions a diff removed.
_ASSERTS = re.compile(r"^(?:assert\b|self\.assert\w*\(|assert\w*\(|expect\(|\w+\.should\b)")
#: A call to a helper the assertions could have moved into: a private
#: name, or one that says it checks. Any call used to count, so an added
#: `print(...)` excused a deleted assertion (Grok, 2026-09-28).
_CALLS = re.compile(r"^(?:self\.)?(?:_\w*|\w*(?:check|verify|assert|expect|ensure)\w*)\(", re.IGNORECASE)
#: The start of a whole test, so its deletion is named as such.
_TEST_HEADER = re.compile(r"^(?:async\s+)?def\s+test\w*\(|^(?:it|test)\(|^@Test\b")
_COMMENT_LEADS = ("#", "//", "/*", "*", '"""', "'''")


def _code(text: str) -> str | None:
    """The line as code, or ``None`` for a comment or a docstring line."""
    stripped = text.strip()
    if not stripped or stripped.startswith(_COMMENT_LEADS):
        return None
    return stripped


def _line_finding(path: str, number: int, text: str) -> dict[str, Any] | None:
    code = _code(text)
    if code is None:
        return None
    if markers_in(text):
        return {"path": path, "line": number, "kind": "skipped or suppressed test", "text": code}
    kind = next((name for name, patterns in _SHAPES
                 if any(pattern.search(code) for pattern in patterns)), None)
    return None if kind is None else {"path": path, "line": number, "kind": kind, "text": code}


def _codes(lines: list[tuple[int, str]]) -> list[str]:
    """The code lines among these, comments and docstring lines left out."""
    return [c for _n, t in lines if (c := _code(t)) is not None]


def _deleted_assertions(path: str, added: list[tuple[int, str]],
                        removed: list[tuple[int, str]]) -> dict[str, Any] | None:
    """Assertions removed and nothing asserting or called in their place.

    A helper the assertions moved into shows up as a call, and a changed
    expectation as one assertion for another, so neither is flagged: the
    count has to fall with nothing taking its place.
    """
    code_added, code_removed = _codes(added), _codes(removed)
    gone = sum(1 for c in code_removed if _ASSERTS.search(c))
    kept = sum(1 for c in code_added if _ASSERTS.search(c))
    if gone <= kept or any(_CALLS.search(c) for c in code_added):
        return None
    number = removed[0][0] if removed else 0
    if any(_TEST_HEADER.search(c) for c in code_removed):
        # The bluntest weakening, and sometimes an obsolete test retired:
        # named for what it is, and still not `clean`, because in a
        # remediating diff deleting the test is how a build goes green.
        return {"path": path, "line": number, "kind": "test deleted",
                "text": f"a test and {gone - kept} assertion(s) removed"}
    return {"path": path, "line": number, "kind": "assertion deleted",
            "text": f"{gone - kept} assertion(s) removed and nothing put in their place"}


def oracle_weakening(added: Lines, removed: Lines | None = None) -> list[dict[str, Any]]:
    """Every way this diff made a test unable to fail, per test file."""
    removed = removed or {}
    found: list[dict[str, Any]] = []
    for path in sorted(set(added) | set(removed)):
        if not is_test_path(path):
            continue
        for number, text in added.get(path, []):
            finding = _line_finding(path, number, text)
            if finding is not None:
                found.append(finding)
        deleted = _deleted_assertions(path, added.get(path, []), removed.get(path, []))
        if deleted is not None:
            found.append(deleted)
    return found
