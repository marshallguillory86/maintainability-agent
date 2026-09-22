"""What a question publishes is what it accepts (D213).

The three labor rates published `options: [90]`, `[140]`, `[210]` — a
one-item enumeration — and meant it as a type marker. The elicitation
model builder reads a non-string option list as "float field, any
value", so that door worked and any rate went through.

A host on the **data path** reads `options` as what the word says and
offers the single value. Submitting a real senior rate meant
contradicting the published contract, which is what an operator hit
entering 130/165/275 against a published 90/140/210.

One field meant two things depending on which door read it. That is the
D189/D190/D193 family — the elicitation path and the data path
disagreeing about the same setup — and this instance had the two paths
disagreeing about the *type of an answer* rather than about which
questions to ask.

`type: "number"` says what the field is; `default` stays a suggestion
rather than the only permitted answer.

The population is every published question, derived from
`published_questions` and the staged set, so a fourth question added
with a one-item enumeration is caught the same way.
"""

from __future__ import annotations

from typing import Any

from maintainability_audit._mcp_setup import (
    economics_bound_questions,
    published_questions,
)


def _every_question() -> list[dict[str, Any]]:
    """Both stages, because the rates only appear in the second."""
    # `published_questions` is keyed by name already; the staged rates
    # are a separate list because they are a second ask.
    seen: dict[str, dict[str, Any]] = dict(published_questions())
    for question in economics_bound_questions():
        seen[question["name"]] = question
    return list(seen.values())




def test_no_question_offers_a_single_choice() -> None:
    """A menu of one is not a menu, and was not meant as one.

    Swept over every published question rather than the three rates:
    the defect is the *shape*, and any future question given a
    one-item enumeration as a type hint reads the same way to a host.
    """
    offenders = [
        question["name"] for question in _every_question()
        if len(question.get("options") or []) == 1
    ]

    assert not offenders, (
        f"these publish a one-item enumeration: {offenders}. A host on the "
        "data path offers exactly that value, whatever the field meant."
    )
