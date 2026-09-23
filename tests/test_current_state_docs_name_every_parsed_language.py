"""The documents that describe what is parsed *today* keep up with the parser.

Kotlin shipped in 3.8.0 with the README, the language-support page and
the roadmap's table updated — and the help index still said "the fourteen
parsed languages", and the architecture document's list of what
`DECLARATION_SUFFIXES` gates still stopped at Ruby. Both are statements
about the present, and both went stale the day a language was added,
which is D168's lesson ("a count written as prose goes stale the first
time a language is added") in two more places.

The README's own languages line is already held to the language-support
table by `test_claimed_languages`. This holds the other two current-state
statements to the same sources: the count to the one the report itself
derives, and the list to the table that claims each language.

Historical prose is deliberately out of scope. The roadmap and the
register quote old counts on purpose, to say what was true when; a rule
over every number-word in the tree would fail on history.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

WORDS = {
    10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
    15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
    19: "nineteen", 20: "twenty",
}


def _parsed_count() -> int:
    """The count the report prints — "across N of the M languages"."""
    from maintainability_audit.scoring import _reference_block

    block = _reference_block()
    return len(block["corpus_languages"]) + len(block["unanchored_languages"])


def _claimed_languages() -> set[str]:
    """Each language the language-support table claims, by its lead name."""
    page = (DOCS / "language-support.md").read_text(encoding="utf-8")
    section = page.split("## How each language is measured", 1)[1]
    section = section.split("**This table is the claim", 1)[0]
    claimed = set()
    for line in section.splitlines():
        cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
        if len(cells) != 3:
            continue
        name = cells[0].split("(")[0].split(",")[0].split("/")[0].strip()
        if name[:1].isalpha() and name not in {"Language", "Anything else"}:
            claimed.add(name)
    assert len(claimed) >= 10, f"the measurement table did not parse: {claimed}"
    return claimed


def test_the_help_index_states_the_parsed_count() -> None:
    count = _parsed_count()
    assert count in WORDS, f"{count} languages; extend WORDS rather than skip"
    index = (DOCS / "help" / "README.md").read_text(encoding="utf-8").lower()

    assert f"{WORDS[count]} parsed languages" in index, (
        f"docs/help/README.md does not say '{WORDS[count]} parsed languages', "
        f"and the report derives {count}"
    )


def test_the_architecture_list_names_every_claimed_language() -> None:
    text = (DOCS / "architecture.md").read_text(encoding="utf-8")
    marker = "Declaration extraction is gated on `DECLARATION_SUFFIXES`"
    assert marker in text, "the gating sentence moved; this guard reads nothing"
    line = text.split(marker, 1)[1].split("\n", 1)[0]

    missing = sorted(
        name for name in _claimed_languages()
        if not re.search(rf"(?<!\w){re.escape(name)}(?!\w)", line)
    )

    assert not missing, (
        f"docs/architecture.md's DECLARATION_SUFFIXES list omits {missing}, "
        "which docs/language-support.md claims is parsed"
    )
