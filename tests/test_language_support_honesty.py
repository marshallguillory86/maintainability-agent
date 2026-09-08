"""The language-support lead may not out-claim its own verification — D139.

`docs/language-support.md` says two things about how a language's branch
set is arrived at. Seventy lines apart, they disagreed for two releases:
the lead said every language's set is *derived from its own grammar*,
and the verification section said only Python's is and the rest are sets
somebody wrote down.

D129 closed by correcting the section. A reader of the table never
reaches the section, so the sentence that reaches them kept over-claiming
— which is the shape this register keeps finding, a correction applied
where it was reported rather than where it is read.

The check has to survive the obvious way of satisfying it, which is why
it is written from both ends: deleting the honest paragraph must not make
the page pass. So the page must **say** the distinction, and must not
say the thing the distinction contradicts.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PAGE = Path(__file__).resolve().parents[1] / "docs" / "language-support.md"

#: The claim D129 retired. Any spelling of "every language's set comes
#: from its grammar" is the defect; the words are matched loosely so a
#: rewording does not walk out from under the test.
OVERCLAIM = re.compile(
    r"each language'?s?\s+branch\s+set\s+is\s+derived\s+from\s+\*{0,2}its\s+own\s+grammar",
    re.IGNORECASE,
)


@pytest.fixture
def page() -> str:
    text = PAGE.read_text(encoding="utf-8")
    assert text.strip(), f"{PAGE} is empty, so every check here would pass over nothing"
    return text


def test_the_lead_does_not_claim_every_language_is_derived_from_its_grammar(
    page: str,
) -> None:
    """The sentence D129 named, in the place a reader actually reaches."""
    found = OVERCLAIM.search(page)

    assert not found, (
        "the language-support lead still says every language's branch set is "
        f"derived from its own grammar: {found.group(0)!r}. Only Python's is "
        "— `ast` implements the grammar and CI enumerates from it. Every "
        "other language's set was written from the same knowledge as the "
        "scanner it checks, which is what D125-D129 cost."
    )


def test_the_page_states_the_distinction_rather_than_merely_omitting_it(
    page: str,
) -> None:
    """Covers existing behaviour: the honest paragraph shipped with D129,
    so this passes at the base. It guards the fix rather than proving it,
    and the falsifier beside it is the one that fails without the change.

    It exists because the cheapest fix for that test is to say nothing at
    all — which is the same defect facing the other way, a page that
    under-claims by silence. The distinction has to be *stated*, and
    deleting the paragraph to satisfy a check that only forbids a
    sentence must not work. Demonstrated: removing it fails this test.
    """
    says_python_is_derived = re.search(
        r"python'?s?\s+(branch set|coverage)\s+is\s+derived\s+from\s+"
        r"(the|its own)\s+grammar",
        page, re.IGNORECASE,
    )
    says_the_rest_are_sets = re.search(
        r"(every other language|the rest)[^.]{0,80}\bset\b", page, re.IGNORECASE,
    )

    assert says_python_is_derived, (
        "the page no longer says Python's set is derived from the grammar, "
        "so a reader cannot tell which language the enumeration covers"
    )
    assert says_the_rest_are_sets, (
        "the page no longer says the other languages' sets are sets rather "
        "than grammar enumerations. Omitting it passes the over-claim check "
        "by saying nothing, which is the same defect facing the other way"
    )


def test_the_lizard_sweep_is_not_described_as_a_grammar(page: str) -> None:
    """2.11.1's token sweep is a second opinion, not a specification.

    `test_grammar_token_coverage` asks the pinned `lizard` which tokens it
    counts as decisions. That is an independent implementation's keyword
    list — better than the author's memory, and still not the language's
    grammar. The page has to keep those two apart, because calling the
    sweep a grammar enumeration would re-open D139 with extra steps.
    """
    assert re.search(r"lizard", page, re.IGNORECASE), (
        "the page does not mention the lizard sweep at all, so a reader "
        "cannot tell what the non-Python check actually is"
    )
    assert re.search(
        r"lizard[^.]{0,120}(keyword list|second implementation|not a grammar|"
        r"rather than a grammar)",
        page, re.IGNORECASE | re.DOTALL,
    ), (
        "the page mentions lizard without saying it is a second "
        "implementation's keyword list rather than a grammar enumeration"
    )
