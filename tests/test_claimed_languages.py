"""Decision 10: the documented languages and the parsed languages are one set.

An audit found `docs/language-support.md` and Decision 10 saying v1.0
handles Python and Java, while the scanner also read JS, TS, JSX and
HTML and produced `declarations_scanned=140`, `evidence_status:
complete` and a verified grade for a JavaScript repository.

The mismatch was in the writing. This project *does* detect and score
JavaScript: the brace scanner reads it, and three baseline-tier
adapters — lizard, jscpd and multimetric — measure it. Marshall's
ruling, 2026-08-26: *"keep JS in since we have a detector and can score
it."* A language belongs in the claim when the tool can detect and
score it, and the documentation follows the capability rather than the
other way round.

What must never happen is a declaration population for a language the
tool can neither parse nor hand to an adapter — a number a reader with
the repository in front of them would call absurd, which is the P7
failure. These tests hold the two sets together in both directions, so
a suffix added to the parser has to reach the page and vice versa.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

import pytest

from maintainability_audit.config import load_config
from maintainability_audit.declarations import DECLARATION_SUFFIXES
from maintainability_audit.report import build_report

DOCS = Path(__file__).resolve().parents[1] / "docs"


def _documented_suffixes() -> set[str]:
    """Every suffix the language-support table offers ranges for."""
    page = (DOCS / "language-support.md").read_text(encoding="utf-8")
    table = page.split("## How each language is measured", maxsplit=1)[1]
    rows = [line for line in table.splitlines() if line.startswith("| ")]
    return {
        suffix
        for row in rows
        # Digits are part of a suffix (`.f90`, `.f03`) and case is
        # significant (`.F90` is preprocessed Fortran, and this project
        # matches suffixes case-sensitively). A letters-only reader saw
        # none of the Fortran row and reported the page as silent about
        # nine suffixes it documents in full.
        for suffix in re.findall(r"`(\.[A-Za-z][A-Za-z0-9]*)`", row)
        if "not parsed" not in row.lower()
    }


def test_the_parsed_languages_are_exactly_the_documented_languages() -> None:
    """A suffix added to one has to reach the other, in both directions.

    The failure this replaces was silent: the page named two languages,
    the parser handled nine, and a JavaScript repository was graded on
    a claim nobody had written down.
    """
    documented = _documented_suffixes()
    assert documented == DECLARATION_SUFFIXES, (
        "docs/language-support.md and the parser disagree.\n"
        f"  only in the page:   {sorted(documented - DECLARATION_SUFFIXES)}\n"
        f"  only in the parser: {sorted(DECLARATION_SUFFIXES - documented)}\n"
        "A language is claimed when this project can detect and score it; "
        "the page, Decision 10 and DECLARATION_SUFFIXES move together."
    )


def test_every_scanned_source_suffix_can_be_read_by_something() -> None:
    """No suffix is opened as source with neither a parser nor an adapter.

    The rule the claim rests on. `.md` and `.css` are scanned and are
    not source; `.go` and `.rs` are source and are deliberately absent
    from the default extensions, because nothing here reads them.
    """
    from maintainability_audit._metrics_types import KNOWN_SOURCE_SUFFIXES

    included = set(load_config(None)["paths"]["include_extensions"])
    source = {s for s in included if s in KNOWN_SOURCE_SUFFIXES}
    unreadable = sorted(source - DECLARATION_SUFFIXES)
    assert not unreadable, (
        f"default include_extensions opens {unreadable} as source and "
        "nothing parses them; a declaration rate built from that "
        "population would be a number nobody measured"
    )

    # The other direction, which was missing and cost 2.4.0 its language.
    # Swift shipped in `DECLARATION_SUFFIXES`, in `SCANNERS`, in the README
    # table and in `language-support.md` — and not in the default
    # `include_extensions`, so no `.swift` file was ever opened. The scanner
    # was correct, tested, documented, and unreachable: an audit of a Swift
    # repository found zero Swift files and withheld its rates, which is
    # indistinguishable from not supporting the language at all.
    #
    # Caught by a corpus run reporting `vapor/vapor` as three files, not by
    # any test, because every test that could have caught it exercised the
    # scanner directly rather than through the configuration a user gets.
    unopened = sorted(DECLARATION_SUFFIXES - included)
    assert not unopened, (
        f"{unopened} are parsed but absent from the default "
        "include_extensions, so no such file is ever opened; the language "
        "is claimed and unreachable"
    )


# One sample of real source per claimed language, by suffix. This was a
# chain of nested conditionals until 1.4.0, when the fifth language took
# it to complexity 24 and this project's own gate failed the fixture —
# correctly. A table is what a per-language lookup wanted to be all
# along, and the next language is a row rather than another `else if`.
_SAMPLE_SOURCE: dict[str, str] = {
    ".py": "def f():\n    return 1\n",
    ".java": "class M { void f() { return; } }\n",
    **dict.fromkeys((".c", ".h"), "int f(void) { return 1; }\n"),
    **dict.fromkeys(
        (".cpp", ".hpp", ".cc", ".cxx", ".hh"), "struct S { void f() { go(); } };\n"
    ),
    ".cs": "class M { public void F() { Go(); } }\n",
    **dict.fromkeys(
        (".f90", ".f95", ".f03", ".f08", ".F90", ".F95", ".F03", ".F08", ".pf"),
        "module m_mod\ncontains\n  subroutine f(n)\n"
        "    integer :: n\n  end subroutine f\nend module m_mod\n",
    ),
}
_DEFAULT_SAMPLE = "function f(){return 1}\n"      # the JS/TS family


def _repo(root: Path, suffix: str, count: int = 140) -> Path:
    root.mkdir(parents=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    body = _SAMPLE_SOURCE.get(suffix, _DEFAULT_SAMPLE)
    for index in range(count):
        (root / f"m{index}{suffix}").write_text(body, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "one"], check=True)
    return root


@pytest.mark.parametrize(
    "suffix",
    [".py", ".java", ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".hh", ".cs",
     ".f90", ".F90", ".f95", ".f03", ".f08", ".pf", ".js", ".ts"],
)
def test_a_claimed_language_produces_the_population_it_claims(
    suffix: str, real_population_floors: object,
) -> None:
    """Each claimed language yields declarations, not a withheld rate.

    Shipped population floors on purpose: the suite lifts them to zero
    so rubric tests can use small trees, and a test about what a real
    repository gets has to ask for what a real repository meets.
    """
    with tempfile.TemporaryDirectory() as work:
        report = build_report(_repo(Path(work) / "tree", suffix), load_config(None))

    summary = report["summary"]
    assert summary["files_scanned"] > 1, f"{suffix} was not scanned at all"
    assert summary.get("declarations_scanned"), (
        f"{suffix} is claimed in language-support.md and produced no "
        "declaration population"
    )


# ---------------------------------------------------------------------------
# The per-language decision table is a claim about the readers, and readers
# change. It drifted badly in 2.11.0: the page listed Go's `select` and
# `goto`, Rust's `loop`, and PHP's `do` as counted, and Rust's `?` as not,
# after every one of those had been reversed in the code — and it had no
# Python row at all while Python's own pattern was being written.
# ---------------------------------------------------------------------------

#: Which reader each row of the table speaks for.
ROW_SUFFIX = {
    "Python": ".py",
    "Go": ".go",
    "Rust": ".rs",
    "PHP": ".php",
    "Ruby": ".rb",
    "Swift": ".swift",
    "C, C++, C#, Java, JS, TS, HTML": ".java",
}


def _decision_table() -> list[tuple[str, str, str]]:
    """(row label, counted cell, not-counted cell) for each language row."""
    page = (DOCS / "language-support.md").read_text(encoding="utf-8")
    section = page.split("## What counts as a decision, per language", 1)[1]
    rows = []
    for line in section.splitlines():
        # `\|\|` is an escaped pipe inside a cell, not a column break —
        # every row but Python's carries one, so a naive split found one
        # row and the guard would have passed on a table it never read.
        cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
        parts = [cell.strip() for cell in cells]
        if len(parts) == 3 and parts[0] in ROW_SUFFIX:
            rows.append((parts[0], parts[1], parts[2]))
    return rows


def _keywords(cell: str) -> list[str]:
    """Backticked tokens that are a single plain word.

    Symbols (`&&`, `??`, `=>`) and multi-word forms (`case _`, `else if`)
    are probed by the grammar fixtures, which have real syntax around
    them. A lone keyword needs no context: every reader matches keywords
    with `\\b`, so a bare word matches exactly when it is in the set.
    """
    return [
        token for token in re.findall(r"`([^`]+)`", cell)
        if token.isalpha()
    ]


def test_every_keyword_the_page_claims_is_counted_actually_is() -> None:
    """The `Counted` column, probed against the reader it names."""
    from maintainability_audit.declarations import metrics_for

    rows = _decision_table()
    assert len(rows) == len(ROW_SUFFIX), (
        f"the decision table lost a row: found {[r[0] for r in rows]}"
    )

    wrong = []
    for label, counted, _ in rows:
        branch_points, _cognitive = metrics_for(ROW_SUFFIX[label])
        wrong += [
            f"{label}: the page says `{word}` is counted, and it is not"
            for word in _keywords(counted)
            if branch_points(word) == 0
        ]
    assert not wrong, "\n".join(wrong)


def test_every_keyword_the_page_claims_is_not_counted_is_not() -> None:
    """The `Deliberately not counted` column, same probe.

    Only the *leading* keyword of each clause is a claim. The clauses
    explain themselves — "`do`, whose `while` carries the loop" — and the
    keyword doing the explaining is often one that is counted, which is
    the whole point of the sentence.
    """
    from maintainability_audit.declarations import metrics_for

    wrong = []
    for label, _, excluded in _decision_table():
        branch_points, _cognitive = metrics_for(ROW_SUFFIX[label])
        for clause in excluded.split(";"):
            words = _keywords(clause)
            if words and branch_points(words[0]) != 0:
                wrong.append(
                    f"{label}: the page says `{words[0]}` is deliberately "
                    "not counted, and it is counted"
                )
    assert not wrong, "\n".join(wrong)


def test_the_readme_names_every_language_the_page_claims() -> None:
    """The front page is a claim too, and it is the one users read first.

    It went stale in 2.11.0: four languages were added, the page and the
    parser were updated together — the tests above see to that — and the
    README's own list kept advertising eight of fourteen. It ships to
    PyPI, so it is the version most people see and the least likely to
    be checked.
    """
    page = (DOCS / "language-support.md").read_text(encoding="utf-8")
    section = page.split("## How each language is measured", 1)[1]
    section = section.split("**This table is the claim", 1)[0]

    claimed = set()
    for line in section.splitlines():
        cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
        if len(cells) != 3:
            continue
        # Trim the suffix list, the free/fixed-form qualifier, and a
        # family cell down to its lead name: `JS / TS / JSX / TSX` is one
        # scanner and the README names it `JS/TS/HTML family`.
        name = cells[0].split("(")[0].split(",")[0].split("/")[0].strip()
        if name[:1].isalpha() and name not in {"Language", "Anything else"}:
            claimed.add(name)
    assert len(claimed) >= 10, f"the measurement table did not parse: {claimed}"

    readme = (DOCS.parent / "README.md").read_text(encoding="utf-8")
    lead = readme.split("**Languages parsed:**", 1)[1].split("\n\n", 1)[0]

    missing = sorted(
        name for name in claimed
        if not re.search(rf"(?<!\w){re.escape(name)}(?!\w)", lead)
    )
    assert not missing, (
        f"the README's languages line does not name {missing}, which "
        "docs/language-support.md says this tool parses"
    )


#: Prose that asserts a language is *not* read by the built-in scanner.
#: Each is a sentence a reader acts on, so naming a parsed language in one
#: is worse than saying nothing.
UNPARSED_CLAIMS = (
    (Path("README.md"), "not parsed for declarations by the built-in scanner"),
    (Path("docs/roadmap.md"), "no scanner is scheduled for any of them"),
)


def test_no_parsed_language_is_named_as_unparsed() -> None:
    """A language cannot be both in the table and in the "not parsed" list.

    The README shipped exactly that: three lines under a table listing Go,
    Rust, PHP and Ruby as parsed, a paragraph told the reader that those
    same four produce "no function-size, complexity, duplication or
    dead-code findings". The roadmap said no scanner was scheduled for
    them in the release that shipped their scanners.

    Nothing checked, because the prose and the table are far apart and
    both read fine alone. This reads the sentence that makes the negative
    claim and holds it against the languages the tool actually parses.
    """
    page = (DOCS / "language-support.md").read_text(encoding="utf-8")
    section = page.split("## How each language is measured", 1)[1]
    section = section.split("**This table is the claim", 1)[0]

    parsed = set()
    for line in section.splitlines():
        cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
        if len(cells) != 3:
            continue
        name = cells[0].split("(")[0].split(",")[0].split("/")[0].strip()
        if name[:1].isalpha() and name not in {"Language", "Anything else"}:
            parsed.add(name)

    root = DOCS.parent
    wrong = []
    for relative, marker in UNPARSED_CLAIMS:
        text = (root / relative).read_text(encoding="utf-8")
        assert marker in text, (
            f"{relative} no longer contains {marker!r}; this guard is "
            "reading for a sentence that moved, so it is checking nothing"
        )
        # The claim and the list of languages sit in one paragraph.
        start = text.rindex("\n\n", 0, text.index(marker)) + 2
        end = text.index("\n\n", text.index(marker))
        paragraph = text[start:end]
        wrong += [
            f"{relative}: `{name}` is parsed, and this says it is not — {marker!r}"
            for name in sorted(parsed)
            if re.search(rf"(?<!\w){re.escape(name)}(?!\w)", paragraph)
        ]
    assert not wrong, "\n".join(wrong)
