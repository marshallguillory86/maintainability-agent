"""Guards on the setup questions that already held (D213).

Covers existing behaviour: every assertion here passes at D213's base,
and one of them passes for a reason that *is* the finding.

`test_a_rate_the_contract_does_not_enumerate_is_accepted` submits 130
against a published `options: [90]`, and it worked before this change —
because the **validator** already accepted any number while the
**published question** offered one. That asymmetry was the defect. The
test therefore cannot falsify the fix, and it is exactly the property a
future change must not lose: the rates still have to arrive as floats,
or the economic bounds stay pending forever, which is D193's own
instance.

The refusals are here for the same reason. Dropping the enumeration
could have dropped the validation with it, and `"ninety"` carried into
money is worse than a menu of one; a real menu still refusing
`depth: "nuclear"` is the branch this change touched on its way past.

Kept out of the cited file so its citation stays evidence for D213.
"""

from __future__ import annotations

import pytest
from test_a_published_question_offers_what_it_accepts import _every_question

from maintainability_audit._mcp_setup import (
    coerce_submitted_answers,
    economics_bound_questions,
)
from maintainability_audit._setup_errors import SetupRequired


def test_the_population_is_not_empty() -> None:
    """Clause two: no questions would make every sweep below vacuous."""
    questions = _every_question()

    assert questions, "no published questions at all"
    assert any(q.get("type") == "number" for q in questions), (
        "no numeric question, so the distinction this entry draws is untested"
    )


def test_a_numeric_question_publishes_no_enumeration() -> None:
    """The two markers cannot both be present without contradicting.

    `type: number` says any number; an `options` list says choose one of
    these. A question carrying both tells the two doors different
    things, which is the defect with an extra step.
    """
    for question in _every_question():
        if question.get("type") == "number":
            assert not question.get("options"), (
                f"{question['name']} is numeric and also enumerates "
                f"{question['options']}"
            )


@pytest.mark.parametrize("submitted", ["130", "165", "275", "42.5"])
def test_a_rate_the_contract_does_not_enumerate_is_accepted(submitted: str) -> None:
    """The operator's own case, and the arithmetic that follows it.

    Read back as a float, because the bounds are money and a string
    that never converted is what left the economic context pending
    forever in D193.
    """
    rates = economics_bound_questions()
    answers = {question["name"]: submitted for question in rates}

    coerced = coerce_submitted_answers(answers)

    for question in rates:
        value = coerced[question["name"]]
        assert isinstance(value, float), f"{question['name']} is {value!r}"
        assert value == float(submitted)


def test_a_rate_that_is_not_a_number_is_still_refused() -> None:
    """The check must not have become a pass-through.

    Dropping the enumeration could have dropped the validation with it,
    which would accept `"ninety"` and carry it into the estimate.
    """
    name = economics_bound_questions()[0]["name"]

    with pytest.raises(SetupRequired):
        coerce_submitted_answers({name: "ninety"})


def test_an_enumerated_question_still_refuses_what_it_does_not_offer() -> None:
    """The other half: real menus keep their menu.

    `depth: "nuclear"` persisting a default and reporting success is
    D193's own instance, and this change touched the branch that
    refuses it.
    """
    enumerated = next(
        question for question in _every_question()
        if len(question.get("options") or []) > 1
    )

    with pytest.raises(SetupRequired):
        coerce_submitted_answers({enumerated["name"]: "nuclear"})
