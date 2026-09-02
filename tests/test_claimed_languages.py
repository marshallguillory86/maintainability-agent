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
