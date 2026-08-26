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
    for ident, title in re.findall(r"^### (D\d+) — (.+)$", entries, re.MULTILINE):
        section = _entry(entries, ident)
        # An open entry has no falsifier yet — that is what open means —
        # and demanding one would push a writer to cite something
        # adjacent just to satisfy the check. What it must not do is
        # *claim* one, so `pending` is the only accepted placeholder and
        # it is checked below.
        if "Closed" not in title:
            assert "pending" in section.lower(), (
                f"{ident} is open but does not say its falsifier is pending; "
                "an open entry may name no test, and must claim none"
            )
            continue
        closing = re.split(r"\*Closing (?:test|tests|suite|suites):\*", section)
        assert len(closing) > 1, (
            f"{ident} names no *Closing test:* — an entry whose falsifier "
            "is only prose cannot be held to pointing at a real one"
        )
        citation = " ".join(closing[1:])
        # A file name is not a falsifier. An audit closed an entry with
        # nothing but a `tests/….py` path and the first version of this
        # check passed it, because it looked for names to resolve and
        # found none to object to. The second version demanded a
        # `test_` token and passed the same attack, because the token it
        # found was the *filename inside the path* — a check that reads
        # `tests/test_x.py` as "names test_x" cannot tell a citation
        # from an address. Paths are stripped before looking (D33).
        named = re.findall(r"\btest_\w+\b", re.sub(r"tests/\S+\.py", " ", citation))
        assert named, (
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
    loaded labor rates" — while the form asked four separate fields and
    the three bounds sat in the schema unconditionally. D28 made the
    page describe that.

    The form has since changed, and this test inverted with it: the
    bounds are a second ask now, put only to someone who answered
    `include`, because asking three money questions of a person who
    just declined money is not a description problem. The page must
    describe *that*, and the check reads both stages from the code so
    neither can drift into merely being old.

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

    from maintainability_audit._mcp_setup import economics_bound_questions

    assert not [q for q in questions if q["name"].startswith("labor_")], (
        "a labor rate is back on the first form, which is asked of "
        "everyone including the people who declined the economic scenario"
    )
    bounds = economics_bound_questions()
    assert len(bounds) == 3, "the labor bounds changed shape; re-read the page"
    for question in bounds:
        assert str(question["default"]) in page, (
            f"the help page never states the default {question['default']!r} "
            f"for {question['name']!r}, which the second form shows"
        )

    lowered = " ".join(page.lower().split())
    assert "second question set" in lowered or "only if you include" in lowered, (
        "the page does not tell the reader the labor rates are a second "
        "ask that follows including the economic scenario"
    )
    assert "0 < low <= base <= high" in page, (
        "the page does not state the rule the rates are refused against"
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


def test_the_security_policy_supports_the_shipped_release_line() -> None:
    """D45: a policy naming a dead version line supports nothing.

    `SECURITY.md` still said `0.1.x` at version 0.9.1 — eight release
    lines of drift, which read literally meant the shipped release
    received no security fixes. Nobody noticed because nothing looked.

    Checked against `config.VERSION` rather than a written-in number,
    so the next release either updates the table or fails here.
    """
    from maintainability_audit.config import VERSION

    line = ".".join(VERSION.split(".")[:2])
    policy = _read(ROOT / "SECURITY.md")
    assert f"`{line}.x`" in policy, (
        f"SECURITY.md does not name the shipped release line {line}.x; "
        "its supported-versions table has drifted from the package"
    )


def test_the_security_policy_does_not_deny_executing_repository_code() -> None:
    """The claim an audit disproved, and why it cannot come back quietly.

    `SECURITY.md` asserted the agent "does not execute scanned code"
    while `eslint` was being invoked in a mode that *requires* the
    audited repository's own configuration and then runs it. Whether
    repositories should be trusted is an open product decision (D39,
    D44); asserting a property the code does not have is not.

    Deliberately narrow: this does not demand any particular wording,
    only that the denial is gone and the behaviour is named.
    """
    policy = _read(ROOT / "SECURITY.md")
    assert "execute code from the repository" in policy.lower(), (
        "SECURITY.md no longer discloses that analyzers run repository code"
    )

    # Only what the document *asserts*, not what it recounts. The entry
    # explaining why the old claim was wrong necessarily quotes it, and
    # a check that cannot tell an assertion from its own correction
    # would forbid explaining the fix.
    asserted = policy.split("This sentence previously read", maxsplit=1)[0].lower()
    assert "not execute scanned code" not in " ".join(asserted.split()), (
        "SECURITY.md asserts the agent does not execute scanned code; "
        "analyzers still run repository-provided configuration"
    )


def test_the_declared_python_floor_supports_the_features_in_use() -> None:
    """D42: metadata that promises a Python the code cannot run on.

    `requires-python` said `>=3.10` while three runtime modules import
    `enum.StrEnum`, which is 3.11. Pip installed happily on 3.10 and
    the import then failed — and nothing caught it, because CI runs
    3.12 and the composite action pins 3.11, so no machine in the
    pipeline ever stood where the metadata said a user could stand.

    I first recorded that no honest test was possible here, on the
    grounds that any such check restates a constant. That was wrong.
    This does not restate the floor; it ties the floor to the language
    features actually imported, which is the relationship that broke.
    A CI matrix entry on the floor version is still worth having, and
    is still recorded as follow-up — but it is not the only check
    available.
    """
    import re as _re

    features = {
        # feature -> (minimum minor version, why)
        "StrEnum": (11, "enum.StrEnum landed in 3.11"),
        "ExceptionGroup": (11, "ExceptionGroup landed in 3.11"),
        "tomllib": (11, "tomllib landed in 3.11"),
        "override": (12, "typing.override landed in 3.12"),
    }

    declared = _re.search(
        r'requires-python\s*=\s*">=3\.(\d+)"',
        _read(ROOT / "pyproject.toml"),
    )
    assert declared, "pyproject.toml no longer declares a requires-python floor"
    floor = int(declared.group(1))

    package = ROOT / "src" / "maintainability_audit"
    for module in sorted(package.rglob("*.py")):
        # Imports and decorators only. A first version matched the bare
        # word anywhere and flagged `_economics.py` for the English
        # "override" in a docstring — a check that cries wolf is a check
        # somebody turns off.
        lines = [
            line for line in _read(module).splitlines()
            if line.startswith(("import ", "from ")) or line.lstrip().startswith("@")
        ]
        text = "\n".join(lines)
        for feature, (needs, why) in features.items():
            if _re.search(rf"\b{feature}\b", text) and needs > floor:
                raise AssertionError(
                    f"{module.relative_to(ROOT)} uses {feature} ({why}) but "
                    f"pyproject declares >=3.{floor}; pip would install on "
                    f"3.{floor} and the import would fail"
                )


def test_the_disposition_names_the_entries_that_are_open() -> None:
    """The prose count and the headings cannot drift apart.

    The disposition read "Six entries are open: D34 through D39" for two
    days after D34-D37 closed. Nothing failed, because the existing
    checks read the headings and the *count* lived in a sentence. A
    ledger that gates a release has to be countable from the register
    itself, so the sentence is now derived from the headings and checked
    against them.
    """
    register = _read(REGISTER)
    open_headings = sorted(
        int(number)
        for number in re.findall(r"^### D(\d+) — Open", register, re.MULTILINE)
    )
    disposition = register.split("## Disposition", maxsplit=1)[1]
    # Only the bolded claim: the prose around it legitimately names
    # entries that closed, and counting those would make this test
    # fail on an accurate register.
    claim = re.search(r"\*\*(.+?)\*\*", disposition, re.DOTALL)
    assert claim, "the disposition no longer opens with a bolded claim"
    claimed = sorted({int(n) for n in re.findall(r"\bD(\d+)\b", claim.group(1))})

    if not open_headings:
        # The ledger reached zero, which is the state a release cuts
        # from. The claim must say so in words rather than list nothing,
        # because an empty list reads identically to a broken parser.
        assert not claimed, (
            "no entry is marked Open, but the disposition still names "
            f"{[f'D{n}' for n in claimed]}"
        )
        assert "closed" in claim.group(1).lower(), (
            "with nothing open the disposition must say every entry is "
            f"closed, not merely omit them: {claim.group(1)[:120]}"
        )
        return
    assert claimed == open_headings, (
        "the disposition names a different open set than the headings do: "
        f"prose={[f'D{n}' for n in claimed]} "
        f"headings={[f'D{n}' for n in open_headings]}"
    )
