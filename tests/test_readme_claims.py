"""The front page is a claim, and it is checked like one.

Split from `test_written_record.py` in 1.5.1, which had crossed this
project's 500-line file gate — the same reason `test_release_plan.py`
was split out of it before.

They belong together anyway. `docs/` is held to the code by several
guards; the README carries its own shorter version of the same claims
and is what most people actually read, so it drifted while the
documentation it summarises stayed true. Its version line sat at 1.0.0
through five releases, and its language table named neither the JS/TS
suffixes nor half of Fortran's.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_the_readme_names_the_shipped_version() -> None:
    """D45 again, one file over.

    `SECURITY.md` is guarded because it went eight release lines stale
    and nobody looked. The README's own version line had no guard at
    all, and it sat at **1.0.0** through 1.1, 1.2, 1.3, 1.4 and 1.5 —
    the first thing a reader sees, naming a release five behind, while
    four languages were added underneath it.

    Checked against `config.VERSION` rather than a written-in number, so
    the next release either updates the line or fails here.
    """
    from maintainability_audit.config import VERSION

    readme = _read(ROOT / "README.md")
    assert f"Version **{VERSION}**" in readme, (
        f"README.md does not name the shipped version {VERSION}; its "
        "header has drifted from the package"
    )


def test_the_report_names_the_corpus_its_anchor_is_drawn_from() -> None:
    """Every multiple is against a corpus of three languages; say which.

    `score.reference` tells a reader that 1.0x is "the median mature-OSS
    repo". The corpus behind that median is 40 repositories of Python,
    TypeScript and JavaScript, and this project parses seven languages —
    so Java, C, C++, C# and Fortran are scored against medians measured
    on none of their code. LAPACK reports declarations at 7.18x that
    anchor and fortran-lang/stdlib at 1.10x; the first number is true of
    LAPACK against mature OSS web code and is not a statement about
    typical Fortran, because no typical Fortran is in the comparison set.

    The rubric stays uniform, which is the promise (P2). The corpus is
    not uniform across languages, which is a limit, and a limit that
    travels only in `docs/standard.md` does not reach the person reading
    the number.
    """
    import json
    from pathlib import Path as _Path

    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    corpus = json.loads(
        (ROOT / "tools" / "calibration" / "corpus.json").read_text(encoding="utf-8")
    )
    languages = {(repo.get("language") or "").lower() for repo in corpus["repos"]}
    assert languages <= {"python", "typescript", "javascript"}, (
        f"the corpus now spans {sorted(languages)}; the disclosure in "
        "score.reference and docs/standard.md must name what it actually holds"
    )

    report = build_report(_Path("."), load_config("maintainability-agent.json"))
    reference = report["score"]["reference"]
    assert reference["corpus_languages"] == ["Python", "TypeScript", "JavaScript"]
    assert "docs/standard.md" in reference["corpus_note"]

    standard = _read(ROOT / "docs" / "standard.md")
    assert "What the anchor does not cover" in standard, (
        "the standard must state which languages the corpus omits"
    )


def test_the_readme_language_table_lists_every_parsed_language() -> None:
    """The claim a reader scans first must match the parser.

    `docs/language-support.md` is already held to `DECLARATION_SUFFIXES`
    in both directions. The README carries its own shorter table, which
    is what most people actually read, and nothing tied it to anything —
    so a language could ship parsed, documented in `docs/`, and missing
    from the front page.
    """
    import re

    from maintainability_audit.declarations import DECLARATION_SUFFIXES

    readme = _read(ROOT / "README.md")
    table = readme.split("## Language support", maxsplit=1)[1].split(
        "## What it produces", maxsplit=1
    )[0]
    named = {
        suffix
        for row in table.splitlines() if row.startswith("| ")
        for suffix in re.findall(r"`(\.[A-Za-z][A-Za-z0-9]*)`", row)
    }
    missing = sorted(DECLARATION_SUFFIXES - named)
    assert not missing, (
        f"the README language table does not name {missing}, which the "
        "parser reads; the front page under-claims what ships"
    )


WORDS = {"five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def _language_groups(table: str) -> set[str]:
    """Distinct languages in the README table, as the sentence counts them.

    The table has one row per *reading*, the sentence one entry per
    *language*, so two normalisations are applied and both are visible
    here rather than hidden in a number:

    - Fortran has two rows, free-form and fixed-form, and is one language.
      Grouping on the text before the first comma collapses them.
    - `TypeScript (semantic)` is not a scanner row at all — it is the
      optional `tsc` analysis — so it is not a parsed language and is
      excluded.

    The section holds more than one table — the analyzer coverage table
    follows the scanner one — so only the first contiguous block of rows is
    read. Taking the whole section counted `C / C++ / C#` as a language.
    """
    rows: list[str] = []
    for line in table.splitlines():
        if line.startswith("|"):
            rows.append(line)
        elif rows:
            break

    groups = set()
    for row in rows:
        if row.startswith("| Language") or set(row) <= set("| -"):
            continue
        cell = row.split("|")[1].strip()
        label = cell.split("(")[0].split(",")[0].strip()
        if not label or label == "TypeScript":
            continue
        groups.add(label)
    return groups


def test_the_readme_language_count_matches_its_own_table() -> None:
    """The prose above the table drifted because only the table was pinned.

    It read "**Seven** languages are parsed as of 1.5.0" naming free-form
    Fortran and stopping there, while the table three lines below already
    carried fixed-form Fortran from 1.6.0 and HTML. The front page
    under-claimed what shipped for two releases, and the table guard could
    not catch it because the table was right the whole time.

    Counting is what catches it. A first attempt checked the sentence for
    *internal* consistency — that "as of" was not older than the newest
    version it named — and the falsifier gate correctly rejected it: at the
    base commit that sentence was self-consistent (1.5.0 ≥ 1.4) and simply
    incomplete, so the guard passed without the fix and defended nothing.
    The defect was an omission, and only a count sees an omission.

    Covers existing behaviour: 1.8.2 already corrected the sentence, so this
    guard cannot fail against a base that is by then correct. It exists to
    stop the omission returning, and the count is what would have caught the
    1.8.1 README, which said seven while its table listed eight.
    """
    import re

    readme = _read(ROOT / "README.md")
    table = readme.split("## Language support", maxsplit=1)[1].split(
        "## What it produces", maxsplit=1
    )[0]

    sentence = re.search(r"(\w+) languages are parsed as of \*\*([0-9.]+)\*\*", readme)
    assert sentence, (
        "the README no longer carries the 'N languages are parsed as of' "
        "sentence this guard exists to pin"
    )
    claimed = WORDS.get(sentence.group(1).lower())
    assert claimed, f"unrecognised count word {sentence.group(1)!r} in the README sentence"

    groups = _language_groups(table)
    assert claimed == len(groups), (
        f"the README says {sentence.group(1).lower()} ({claimed}) languages are "
        f"parsed, but its own table lists {len(groups)}: {sorted(groups)}"
    )
