"""Number agreement for sentences built from a measured population.

A foundation, deliberately. Grammar is neither scoring nor presentation:
the scoring layer writes the corpus note, three skins write the caveat
beside a grade, and all four need the same answer to "how many are we
talking about". Putting it here is what lets every one of them ask
rather than assume.

**Why it exists (D148).** `UNANCHORED_LANGUAGES` was six languages, and
four separate sentences were written with the plural baked in — "are
parsed", "code in them", "a grade or multiple". 3.0.0 anchored five of
the six, D143 corrected the constant to `("COBOL",)`, and every one of
those sentences went on saying **"COBOL are parsed"** — in the Markdown
report, the HTML strip beside the letter, and the corpus note inside the
score object.

It is a small defect and it is the same shape as the large one it came
from: a fact about the population, restated by hand wherever it was
needed, going stale the moment the population changed. A contract test
even asserted the literal `"{names} are parsed"`, so the wrong grammar
was pinned rather than caught — a check written from the sample it was
built on, which is the failure this project's falsifier standard exists
to name.

The wording stays each caller's own; only the number comes from here.
"""
from __future__ import annotations

from typing import NamedTuple


class Agreement(NamedTuple):
    """The forms a sentence needs once its subject has been counted.

    Attributes rather than dict keys on purpose, and the reason is a
    small demonstration of this project's own theme. The first cut
    returned a dict, and subscripting it for the grade form read — to
    the sweep that hunts for score keys removed in ADR 001 stage 8 —
    exactly like a report dictionary being indexed. The sweep flagged
    it, correctly by its own rule and wrongly about the intent, because
    a string cannot tell a lookup from a mention. Attribute access is
    unambiguous to the next reader and to the next check, which is worth
    more than the brevity it costs.
    """

    verb: str
    """`is` or `are`, for a present-tense clause about the subject."""

    object_pronoun: str
    """`it` or `them`, for "code in ___"."""

    possessive: str
    """`its` or `their`."""

    quantity: str
    """`a grade` or `a grade or multiple` — how many results are at stake."""


def agreement(count: int) -> Agreement:
    """The singular or plural forms for a subject of this size.

    `count` rather than a module constant, because a renderer reads its
    names from the report it is printing and the scorer reads them from
    the constant. Both are populations; only one is in scope here.

    Zero takes the plural. A caller with an empty population should be
    printing nothing at all, and every one of them checks that first, so
    the branch is unreachable rather than meaningful — but silently
    returning singular for it would invite "0 language is parsed" the
    day somebody forgets the check.
    """
    single = count == 1
    return Agreement(
        verb="is" if single else "are",
        object_pronoun="it" if single else "them",
        possessive="its" if single else "their",
        quantity="a grade" if single else "a grade or multiple",
    )


def counted(count: int, noun: str, plural: str | None = None) -> str:
    """`1 scan`, `2 scans` — a count printed with a noun that agrees.

    The same defect as `agreement`, one part of speech over. The trend
    section was rendering **"1 scans"** for every single-scan series, and
    this repository's own history has sixteen of them, so the report that
    exists to hold a project to its measurements was miscounting out
    loud in sixteen places.

    `plural` is for the nouns English does not form by adding an `s`.
    Callers that do not need it say nothing, which is most of them.
    """
    return f"{count} {noun}" if count == 1 else f"{count} {plural or noun + 's'}"
