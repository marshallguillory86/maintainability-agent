"""The presentation question stays answerable at every door (D201).

Covers existing behaviour: all three assertions pass at D201's base,
and that is the property. They read the population from
`PRESENTATIONS`, so at the base they held over three words and here
they hold over four — a check that adapts to the set cannot falsify a
change to the set, and pretending otherwise is what the falsifier
standard above this file exists to stop.

They are worth having anyway, because the failure they describe is the
one D201 half was: an option recited to a user that the code behind it
does not accept. The terminal prompt and the tuple are two strings, the
tuple and the parser are two contracts, and a fifth presentation added
to one of them and not the others fails here rather than in a user's
terminal.

Kept out of `test_every_built_presentation_is_offered` so that file's
citations stay evidence for D201 rather than being diluted by
assertions that prove nothing it shipped.
"""

from __future__ import annotations

import argparse

from maintainability_audit._arguments import add_arguments
from maintainability_audit._catalog import PRESENTATIONS
from maintainability_audit._first_run import ask_presentation


def _format_choices() -> set[str]:
    """Every value `--format` accepts, read off the parser itself."""
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    actions = [
        action
        for action in parser._actions  # noqa: SLF001 - the only accessor
        if action.dest == "format"
    ]
    assert len(actions) == 1, "the parser has no single --format action"
    return set(actions[0].choices or ())


def test_nothing_offered_is_refused_by_the_door_it_is_offered_on() -> None:
    """The other direction: an option the question offers must be answerable.

    `chat` is deliberately not an argparse choice — it is what you get
    with no format flag — so it is excluded by name, and that exclusion
    is the only hand-written member in this file.
    """
    accepted = _format_choices() | {"chat"}
    unanswerable = sorted(set(PRESENTATIONS) - accepted)

    assert not unanswerable, (
        f"the question offers {unanswerable}, which no door accepts"
    )


def test_the_terminal_accepts_the_answer_it_now_offers(monkeypatch) -> None:
    """Typing every offered word returns that word, not the chat fallback.

    At this change's base, typing `json` fell through the membership
    test, printed "'json' is not one of (...)" and returned `chat` — the
    exact shape of an offered option that does not work, had it been
    offered.
    """
    for presentation in PRESENTATIONS:
        monkeypatch.setattr("builtins.input", lambda _prompt, word=presentation: word)

        assert ask_presentation() == presentation


def test_the_terminal_question_names_every_option(monkeypatch) -> None:
    """The prompt string is what a person reads; the tuple is not."""
    seen: list[str] = []
    monkeypatch.setattr("builtins.input", lambda prompt: seen.append(prompt) or "")

    ask_presentation()

    assert seen, "the question was never asked"
    for presentation in PRESENTATIONS:
        assert presentation in seen[0], (
            f"the terminal prompt never names {presentation}: {seen[0]!r}"
        )
