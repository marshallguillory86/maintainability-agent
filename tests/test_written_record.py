"""The register and the docs, held against machine-readable sources.

Split out of ``test_chat_primary_docs.py`` at this repository's own
file-length gate. That file asks whether the chat surfaces teach the
product; these ask whether the written record is true — that every
closed entry names a falsifier a reader can actually run, that the
first-run page describes the form the code builds, and that no document
claims a register entry is open after the register closed it.

Every one of these came from an audit finding prose that contradicted
the code, which is why none of them restates what it checks: they read
`setup_questions`, the register, and the test suite itself.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs/defect-register-chat-surface.md"
HELP = ROOT / "docs/help"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_the_register_states_a_falsifier_for_every_entry() -> None:
    """Closure is a named test, and the count is read, never asserted.

    An earlier version demanded an all-closed state by a written-in
    number, which is a test that can require a lie: when two audit
    findings were entered the register grew and the assertion still
    said seventeen. Entries are counted from their own headings, and
    each closed one must name the test that would fail if its defect
    returned.
    """
    register = _read(REGISTER)
    headings = re.findall(r"^### (D\d+) — (.+)$", register, re.MULTILINE)
    assert len(headings) >= 19, f"register shrank: {len(headings)} entries"

    body = register.split("## Disposition", maxsplit=1)
    assert len(body) == 2, "the register lost its disposition"
    entries, disposition = body[0], body[1].lower()

    open_entries = [f"{ident} {title}" for ident, title in headings
                    if "Closed" not in title]
    if open_entries:
        # An open entry is legitimate; claiming everything is closed
        # while one is open is not.
        assert "every entry" not in disposition, (
            f"the disposition claims all closed while these are open: {open_entries}"
        )
        return

    # Every `test_...` the register names, resolved against the suite.
    # Naming a token that merely looks like a test was the whole check
    # until an audit found two entries citing tests that had been
    # renamed out of existence — D3 and D14, both broken by renames in
    # this very branch, both passing this test. A citation nobody
    # resolves is not a falsifier; it is a claim about one.
    for ident, _title in headings:
        section = _entry(entries, ident)
        # Substance, not phrasing: some entries write "Closing test",
        # some "Closing suite", some name the tests inline. What every
        # closed entry must do is point at a real falsifier.
        assert re.search(r"`tests/\S+\.py`|`test_\w+`|\btest_\w+\b", section), (
            f"{ident} closes without naming the falsifier that would fail"
        )

    # The security entry names both doors it had to bound.
    assert "test_mcp_history_rejects_parent_traversal_without_external_write" in register
    assert "test_the_cli_door_applies_the_same_boundary" in register


def _entry(entries: str, ident: str) -> str:
    return entries.split(f"### {ident} — ", maxsplit=1)[1].split("\n### ", maxsplit=1)[0]


def test_every_closing_citation_names_a_test_that_exists() -> None:
    """A citation nobody resolves is a claim about a falsifier, not one.

    The register's guarantee is that each closed entry names the test
    that would fail if its defect returned. Nothing checked the name
    resolved, so when a branch renamed two tests, D2, D3 and D14 went on
    closing on functions that no longer existed — and the register test
    passed, because the names still *looked* like tests.

    Only the closing citation is held to this. Entry prose legitimately
    names tests that are gone: D27 quotes the old name of a test it
    renamed, as the history it exists to record. Telling a falsifier
    from a mention is what the ``*Closing test:*`` marker is for, which
    is why the marker is mandatory — D14 cited its falsifier in prose
    and went unchecked for precisely that reason.

    The citation must also be findable, not merely real. An audit beat
    the first version of this check by pointing at a function that
    exists in a *different* file from the one the entry names: the
    module stem in the path counted as its own hit, so the wrong
    address passed. A reader given the wrong file cannot run the
    falsifier, which is the only thing a citation is for (D30).
    """
    entries = _read(REGISTER).split("## Disposition", maxsplit=1)[0]
    # `async def` and class-nested (indented) definitions both count.
    # Neither exists in this tree today, which is exactly why an audit
    # had to point them out twice: a collector that only sees the shape
    # currently written will silently stop seeing the day someone
    # writes another one.
    by_module = {
        path.stem: set(re.findall(r"^\s*(?:async\s+)?def (test_\w+)",
                                  _read(path), re.MULTILINE))
        for path in (ROOT / "tests").glob("test_*.py")
    }
    everywhere = set().union(*by_module.values())

    problems = []
    for ident in re.findall(r"^### (D\d+) — ", entries, re.MULTILINE):
        closing = re.split(
            r"\*Closing (?:test|tests|suite|suites):\*", _entry(entries, ident),
        )
        assert len(closing) > 1, (
            f"{ident} names no *Closing test:* — an entry whose falsifier "
            "is only prose cannot be held to pointing at a real one"
        )
        citation = " ".join(closing[1:])
        # A file name is not a falsifier. An audit closed an entry with
        # nothing but a `tests/....py` path on the closing line and this
        # check passed, because it only looked for names to resolve and
        # found none to object to. "Which test fails if this defect
        # returns?" has to have an answer (D32).
        assert re.search(r"\btest_\w+\b", citation), (
            f"{ident} closes on a file with no test named in it; a reader "
            "cannot tell which test fails if the defect returns"
        )
        problems += _misdirected(ident, citation, by_module, everywhere)

    assert not problems, (
        "the register closes entries on falsifiers a reader cannot run: "
        + "; ".join(problems)
    )


def _misdirected(ident: str, citation: str, by_module: dict[str, set[str]],
                 everywhere: set[str]) -> list[str]:
    """Every cited function that is missing, or filed under the wrong file."""
    named = set(re.findall(r"\b(test_\w+)\b", citation))
    files = {stem for stem in re.findall(r"tests/(\w+)\.py", citation)}
    problems = []
    for name in sorted(named - set(by_module)):
        if name not in everywhere:
            problems.append(f"{ident} closes on {name}, which does not exist")
        elif files and not any(name in by_module.get(stem, ()) for stem in files):
            actual = sorted(s for s, names in by_module.items() if name in names)
            problems.append(
                f"{ident} files {name} under {sorted(files)}; it lives in {actual}"
            )
    return problems


def test_the_first_run_help_describes_the_form_a_person_actually_sees() -> None:
    """D28: the help page is read against the question set, not a memory of it.

    The page grouped economics as one bullet — "skip, or low/base/high
    loaded labor rates" — while the form asks four separate fields, and
    the three labor bounds sit in the elicitation schema
    unconditionally. Someone answering "skip" is still shown all three,
    and the page gave them no way to expect that.

    Read from `setup_questions`, so a question added to the form has to
    reach the page before it ships, and a page that restates the form
    from memory drifts into failure rather than into being merely old.
    """
    from maintainability_audit._first_run import PRESENTATIONS
    from maintainability_audit._mcp_setup import setup_questions
    from maintainability_audit.config import load_config

    page = _read(HELP / "first-run.md")
    questions = setup_questions(load_config(None))

    # Every field, and its default, stated where the reader will meet it.
    for question in questions:
        default = str(question["default"])
        assert default in page, (
            f"the help page never states the default {default!r} for "
            f"{question['name']!r}, which the form shows"
        )

    labor = [q for q in questions if q["name"].startswith("labor_")]
    assert len(labor) == 3, "the labor bounds changed shape; re-read the page"
    # The specific misdescription: bounds presented as conditional.
    lowered = " ".join(page.lower().split())
    assert "even when" in lowered or "unconditional" in lowered, (
        "the page does not tell the reader the labor fields appear "
        "regardless of the economics answer"
    )
    for presentation in PRESENTATIONS:
        assert presentation in lowered


def test_no_document_says_a_register_entry_is_open_that_the_register_closed() -> None:
    """D29: a status claim about another document goes stale silently.

    ADR 011 ended a decision with "that free-text ask remains open under
    D3" long after D3 closed. The decision text itself is history and
    must not be rewritten — an ADR records what was decided when — but a
    reader takes an unqualified status claim as current, and nothing
    linked the sentence to the register that could contradict it.

    The class, not the instance: any document asserting an entry is
    open must be corrected or stamped when the register closes it. A
    dated amendment note beside the claim satisfies this, which is how
    ADR 011 now reads and how the register marks its own superseded
    clauses.
    """
    register = _read(REGISTER)
    closed = {
        ident
        for ident, title in re.findall(r"^### (D\d+) — (.+)$", register, re.MULTILINE)
        if "Closed" in title
    }
    assert closed, "no closed entries to check against"

    stale = []
    for path in sorted(ROOT.glob("docs/*.md")) + sorted(ROOT.glob("docs/help/*.md")):
        if path.name == REGISTER.name:
            continue
        paragraphs = re.split(r"\n\s*\n", _read(path))
        for index, paragraph in enumerate(paragraphs):
            # A stamp sits in the claim's own paragraph or directly
            # beneath it — the latter being the form an ADR takes, where
            # the decision text is history and must not be edited.
            nearby = " ".join(paragraphs[index:index + 2]).lower()
            if "amended" in nearby or "amendment" in nearby:
                continue
            for match in re.finditer(
                r"(?:remains?|still|is)\s+open[^.]{0,60}?\b(D\d+)\b", paragraph,
            ):
                if match.group(1) in closed:
                    stale.append(f"{path.relative_to(ROOT)} calls {match.group(1)} open")

    assert not stale, (
        "documents assert a register entry is open that the register records "
        "as closed; correct the claim or stamp it: " + "; ".join(stale)
    )
