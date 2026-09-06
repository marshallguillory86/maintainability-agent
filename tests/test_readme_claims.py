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

import re
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
    """Every multiple is against a corpus; the report must say which one.

    `score.reference` tells a reader that 1.0x is "the median mature-OSS
    repo". For five releases the corpus behind that median was 40
    repositories of Python, TypeScript and JavaScript while the scanner
    parsed eight languages, so Java, C, C++, C# and Fortran were scored
    against medians measured on none of their code — LAPACK reported
    declarations at 7.18x that anchor, a true statement about LAPACK
    against mature OSS web code and not a statement about typical Fortran,
    because no typical Fortran was in the comparison set.

    2.0.0 extended the corpus instead of the caveat. The assertion below is
    deliberately *derived* rather than named: a hardcoded language list
    fails the moment the corpus changes and says nothing about what should
    replace it, whereas holding the shipped disclosure to the corpus file
    catches drift in both directions — a language named but not held, or
    held but not named.

    The rubric stays uniform, which is the promise (P2). What limits remain
    are stated in `docs/standard.md`, and the note travels in every report
    so they reach the person reading the number.
    """
    import json
    from pathlib import Path as _Path

    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    corpus = json.loads(
        (ROOT / "tools" / "calibration" / "corpus.json").read_text(encoding="utf-8")
    )
    languages = {(repo.get("language") or "").lower() for repo in corpus["repos"]}

    report = build_report(_Path("."), load_config("maintainability-agent.json"))
    reference = report["score"]["reference"]

    # Derived from the corpus rather than hardcoded. The previous version
    # asserted the three original languages by name, so it failed the moment
    # the corpus was extended and told nobody *what* to say instead. Holding
    # the disclosure to the file it describes means the report cannot name a
    # language the corpus lacks, or omit one it holds, in either direction.
    spelled = {"cpp": "c++", "csharp": "c#"}
    disclosed = {spelled.get(name, name) for name in
                 (value.lower() for value in reference["corpus_languages"])}
    held = {spelled.get(name, name) for name in languages}
    assert disclosed == held, (
        f"score.reference names {sorted(disclosed)} but the corpus holds "
        f"{sorted(held)}; the disclosure travels with every number and must "
        "match the anchor it describes"
    )
    assert str(len(corpus["repos"])) in reference["corpus_note"], (
        f"the corpus holds {len(corpus['repos'])} repositories and the note "
        "shipped in every report does not say so"
    )
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


# Extended through fifteen when Go took the count past ten. A word
# missing from here reads as "unrecognised count", which is the guard
# refusing to check rather than the sentence being wrong.
WORDS = {"five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
         "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
         "fourteen": 14, "fifteen": 15}


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


def test_no_readme_image_is_repository_relative() -> None:
    """D110: PyPI renders this file, and drops relative image paths.

    `pyproject.toml` sets ``readme = "README.md"``, so the README *is*
    the PyPI long_description. GitHub resolves a repository-relative
    image path; PyPI does not, and silently drops the tag. The live page
    was checked and contained no image at all — the cover had never been
    seen by anyone who found the package on its own distribution page.

    An absolute raw URL renders on both. This is asserted rather than
    remembered, because the failure is invisible from inside the
    repository: every image looks right on GitHub while none of them
    reach PyPI.
    """
    import re

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    relative = [
        target for target in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme)
        if not target.startswith(("http://", "https://", "data:"))
    ]
    assert not relative, (
        "these README images are repository-relative and will not render on "
        f"PyPI: {relative}. Use the absolute raw.githubusercontent.com URL."
    )


#: The fleet reading: that this tool joins several repositories'
#: histories to report how one transformation fared across an org. It is
#: a roadmap item and it is not built. It was also invented twice before
#: it was ever decided, so what these patterns defend is not the idea —
#: Marshall has since accepted it as a future item — but the difference
#: between an idea and a shipped feature.
#: Every gap is `\s+`, never a literal space. Prose wraps: at the base
#: this guard is proven against, the seed phrase reads "across\nservices",
#: and a pattern written with a space matched nothing there — so the test
#: passed without the fix and defended nothing. The falsifier gate caught
#: exactly that, which is the second thing it has caught this week.
_FLEET = (
    re.compile(r"codemod[^.]{0,40}\bacross\s+services\b", re.I),
    re.compile(r"\b(forty|many|dozens\s+of)\s+services\b", re.I),
    re.compile(r"cross-repositor\w+\s+(transformation|comparison|history)", re.I),
    re.compile(r"transformation[^.]{0,60}\bacross\s+repositories\b", re.I),
)

#: Surfaces a reader draws *current capability* from. The roadmap is
#: deliberately absent: it is the one place the unbuilt version belongs,
#: and it is checked separately for saying so.
_CAPABILITY_SURFACES = (
    "README.md", "docs/product-intent.md", "docs/architecture.md",
    "docs/target-architecture.md", "docs/cli.md",
    "src/maintainability_audit/_run_comparison.py",
)

#: The roadmap entry must keep saying it has not shipped. An unbuilt item
#: that stops marking itself unbuilt is how a plan becomes a claim.
_UNBUILT_MARKERS = ("not built", "not scheduled")


def _is_quoted(text: str, start: int) -> bool:
    """Whether the match at `start` is being *mentioned* rather than made.

    The fourth time this project has needed this rule. D108: a
    suppression marker quoted in a docstring was read as a directive.
    D111: the falsifier gate's escape phrase, quoted in prose explaining
    it, exempted the test doing the explaining. And a guard over intent
    has the same problem twice over — a non-goal must name the claim to
    reject it, and the docstring that corrects the old wording must quote
    the old wording.

    Worth noticing as a class: every rule this project writes over English
    eventually meets a sentence *about* the thing it forbids. The rule is
    always the same, so it is written the same way each time — quoted
    means mentioned.
    """
    line_start = text.rfind("\n", 0, start) + 1
    before = text[line_start:start]
    return before[-1:] in {"`", "'", '"'} or before.count('"') % 2 == 1


def test_no_surface_presents_cross_repository_comparison_as_shipped() -> None:
    """A roadmap item must not read as a capability.

    `--transformation` compares runs within one repository. The fleet
    version is wanted and unbuilt, so the only surface entitled to
    describe it is the roadmap, which says so.

    This exists because the fleet version was written into the roadmap as
    though decided, rejected, deleted, and then re-derived hours later
    into a summary that was saved as a work list. The deletion left
    nothing behind while the text that seeded it stayed: this module's
    own feature described its use case as "a codemod applied across
    services", which reads as a fleet.
    """
    offenders = []
    for name in _CAPABILITY_SURFACES:
        text = (ROOT / name).read_text(encoding="utf-8")
        for pattern in _FLEET:
            for match in pattern.finditer(text):
                if _is_quoted(text, match.start()):
                    continue
                offenders.append(f"{name}: {match.group(0)!r}")
    assert not offenders, (
        "cross-repository transformation comparison is a roadmap item and is "
        "not built; these surfaces describe it where a reader takes current "
        "capability:\n  " + "\n  ".join(offenders)
    )


def test_the_roadmap_keeps_the_fleet_item_marked_unbuilt() -> None:
    """The guard above needs its reason kept, and the reason is the roadmap.

    Without an entry that says what this is and why it is not built, a
    later reader deletes the check as unexplained — or re-derives the
    feature from the single-repository one, which has now happened twice.
    """
    roadmap = (ROOT / "docs" / "roadmap.md").read_text(encoding="utf-8")
    heading = "Cross-repository transformation comparison"
    assert heading in roadmap, (
        "the roadmap no longer carries the fleet item the guard explains"
    )
    entry = roadmap.split(heading, 1)[1].split("\n## ", 1)[0].lower()
    assert any(marker in entry for marker in _UNBUILT_MARKERS), (
        f"the fleet roadmap entry no longer marks itself unbuilt "
        f"(one of {_UNBUILT_MARKERS}), so a plan now reads as a claim"
    )
    assert "comparability_fields" in entry, (
        "the entry no longer names what makes the fleet version hard — "
        "that scans from different repositories come from different "
        "instruments — so the next reader will price it as a join"
    )
