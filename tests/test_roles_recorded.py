"""From D90, every entry records who did which part.

Marshall's question, 2026-08-26: does a falsifier written by a different
agent than the one that wrote the code produce fewer defects? Eleven
entries in this register are findings about an inadequate *check* rather
than about the product, and eight of them fall in the stretch where one
agent wrote the code, the tests, and the audit prompts.

That is suggestive and it is not evidence, because nothing recorded who
wrote what. The register cannot answer a question about its own
production without the data, so from D90 it collects it.

Deliberately **not** backfilled. Reconstructing authorship from memory
would put invented data into the one document whose value is that its
claims are checkable, and the analysis it fed would be worth less than
no analysis at all.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REGISTER = (
    Path(__file__).resolve().parents[1]
    / "docs" / "defect-register-chat-surface.md"
)

#: The first entry that must carry roles. Entries below this predate the
#: convention and are honestly silent rather than dishonestly filled in.
ROLES_FROM = 90

FIELDS = ("found", "prompt", "fix", "test", "run")
KNOWN_AGENTS = frozenset({
    "claude", "codex", "grok", "marshall", "ci", "none",
    "local", "mutation", "unknown",
})
ROLES_RE = re.compile(r"^\*Roles:\*\s+(.+)$", re.M)


def _entries() -> list[tuple[int, str]]:
    text = REGISTER.read_text(encoding="utf-8")
    parts = re.split(r"\n### (D\d+) — ", text)
    return [
        (int(parts[i][1:]), parts[i + 1])
        for i in range(1, len(parts), 2)
    ]


def test_the_register_still_has_entries_to_check() -> None:
    """A parser that silently matches nothing proves nothing."""
    found = _entries()
    assert len(found) > 80, f"only {len(found)} entries parsed; has the heading changed?"


def test_entries_from_the_cutoff_record_their_roles() -> None:
    """Who wrote the code, the check, and the prompt that found it."""
    missing = [
        f"D{number}" for number, body in _entries()
        if number >= ROLES_FROM and not ROLES_RE.search(body)
    ]
    assert not missing, (
        f"entries at or after D{ROLES_FROM} with no *Roles:* line: {missing}. "
        "The register collects this so a question about how it is produced "
        "can be answered with data rather than with recollection"
    )


@pytest.mark.parametrize("field", FIELDS)
def test_every_recorded_role_names_every_field(field: str) -> None:
    """A partial record is the shape that makes an analysis wrong."""
    offenders = []
    for number, body in _entries():
        match = ROLES_RE.search(body)
        if match is None:
            continue
        recorded = dict(
            pair.split("=", 1) for pair in match.group(1).split()
            if "=" in pair
        )
        if field not in recorded:
            offenders.append(f"D{number}")
    assert not offenders, f"{offenders} record no {field!r}"


def test_recorded_roles_name_agents_this_project_knows() -> None:
    """A typo'd agent name is a silently dropped row in the analysis."""
    unknown: list[str] = []
    for number, body in _entries():
        match = ROLES_RE.search(body)
        if match is None:
            continue
        for pair in match.group(1).split():
            if "=" not in pair:
                continue
            _key, value = pair.split("=", 1)
            unknown += [
                f"D{number}:{item}" for item in value.split("+")
                if item not in KNOWN_AGENTS
            ]
    assert not unknown, (
        f"role values this project does not recognise: {unknown}. "
        f"Known: {sorted(KNOWN_AGENTS)}"
    )


def test_the_convention_is_documented_where_a_writer_will_meet_it() -> None:
    """A rule enforced by a test and written nowhere is a trap."""
    text = REGISTER.read_text(encoding="utf-8")
    assert "*Roles:*" in text.split("## Entries")[0], (
        "the roles convention is enforced below but not explained above it"
    )
    assert f"D{ROLES_FROM}" in text.split("## Entries")[0], (
        "the cutoff this test enforces is not stated in the register"
    )


#: The first entry that must state what its mutation broke. Clause three
#: of the falsifier standard cannot be checked mechanically -- nothing
#: can tell whether a mutated member sits inside the sample a test names
#: -- so it is required to be written instead. An author who has to say
#: which member they broke, and why it is outside what the test names,
#: cannot make the substitution without noticing.
MUTATION_FROM = 97


def test_entries_from_the_cutoff_state_what_their_mutation_broke() -> None:
    """Clause three, made impossible to skip in silence.

    Thirty entries in this register are the same defect: a check written
    from the instance that motivated it rather than from the claim it
    defends. Mutation testing was being done throughout and did not
    catch a single one, because the mutation was drawn from the same
    sample as the assertion -- confirming the sample, saying nothing
    about the claim.

    Every time an auditor broke one of these, they mutated a member the
    test did not name. That is the move, and this is the line that makes
    an author perform it deliberately.
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
