"""From D97, every entry states what its mutation broke.

Clause three of the falsifier standard cannot be checked mechanically:
nothing can tell whether a mutated member sits inside the sample a test
names. So it is required to be written instead. An author who has to say
which member they broke, and why it is outside what the test names,
cannot make the substitution without noticing.
"""

from __future__ import annotations

import re
from pathlib import Path

REGISTER = (
    Path(__file__).resolve().parents[1]
    / "docs" / "defect-register-chat-surface.md"
)

#: The first entry that must state what its mutation broke. Entries below
#: it predate the convention and are honestly silent rather than
#: dishonestly filled in.
MUTATION_FROM = 97


def _entries() -> list[tuple[int, str]]:
    text = REGISTER.read_text(encoding="utf-8")
    parts = re.split(r"\n### (D\d+) — ", text)
    return [
        (int(parts[i][1:]), parts[i + 1])
        for i in range(1, len(parts), 2)
    ]


def test_entries_from_the_cutoff_state_what_their_mutation_broke() -> None:
    """Clause three, made impossible to skip in silence.

    Thirty entries in this register are the same defect: a check written
    from the instance that motivated it rather than from the claim it
    defends. Mutation testing was being done throughout and did not
    catch a single one, because the mutation was drawn from the same
    sample as the assertion -- confirming the sample, saying nothing
    about the claim.

    Every time an audit broke one of these, it mutated a member the test
    did not name. That is the move, and this is the line that makes an
    author perform it deliberately.
    """
    subject = [(number, body) for number, body in _entries() if number >= MUTATION_FROM]
    # Clause two, applied to this check's own population. Without it the
    # test passes over an empty list at any commit predating the cutoff
    # -- which `tools/prove_falsifiers.py` caught by running it against
    # the base, where no entry reaches D97 and it asserted nothing.
    assert subject, (
        f"no entry reaches D{MUTATION_FROM}, so this asserts over nothing "
        "and the mutation requirement is unenforced"
    )
    missing = [f"D{number}" for number, body in subject if "*Mutation:*" not in body]
    assert not missing, (
        f"entries at or after D{MUTATION_FROM} that do not say what their "
        f"mutation broke: {missing}. State the member you broke and why it "
        "sits outside what the closing test names"
    )


def test_the_mutation_requirement_is_documented_above_the_entries() -> None:
    """A rule enforced by a test and written nowhere is a trap."""
    text = REGISTER.read_text(encoding="utf-8")
    preamble = text.split("## Entries")[0]
    assert "*Mutation:*" in preamble and "outside the sample" in preamble, (
        "the mutation clause is enforced below but not explained above it"
    )
    assert f"D{MUTATION_FROM}" in preamble, (
        "the cutoff this test enforces is not stated in the register"
    )
