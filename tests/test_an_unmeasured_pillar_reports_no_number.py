"""A pillar this tool does not measure reports nothing on either axis (D210).

Practice level is a fact about the **repository** — is a linter wired
into CI, is there a coverage gate, are ADRs maintained — and the pillar
section states it once, above the table. Every row then repeated that
one number in its own Practice column, including the rows for pillars
this tool explicitly does not measure.

So the efficiency row read `practice 4` for a pillar ADR 007 declares
out of scope, and an unmeasured security row said the same. A fact about
the repository became a claim about a pillar nobody took a reading on.

**`posture` was nulled for exactly this reason and `practice` was left
behind.** `_measured_entry`'s own comment records it: the first version
printed "efficiency — healthy" from the practice axis alone, *"a
maturity level vouching for code the tool had explicitly declared out of
scope"*. The fix nulled the derived cell and left the input, so the
number kept printing beside a dash.

A delegated pillar that **did** come back with a document is the case
that must keep a number: `secure-code-agent` measures security practice
and reports its own level, which is a real measurement of that pillar
rather than this repository's standing in for one.

The population is `PILLARS`, read from the module that declares them, so
a sixth pillar is covered the moment it exists.
"""

from __future__ import annotations

from typing import Any

from maintainability_audit._pillars import PILLARS, Scope, pillar_report
from maintainability_audit._scan_view import practice_cell

PRACTICE = {"level": 4, "summary": "CI holds a numeric quality gate", "signals": []}


def _report(delegated: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return pillar_report({"aspects": {}, "not_applicable": []}, PRACTICE, delegated)


def _unmeasured() -> list[Any]:
    """Pillars with no reading of their own: out of scope, or delegated away."""
    return [p for p in PILLARS if p.scope not in (Scope.OWNED, Scope.PARTIAL)]


def test_the_population_is_not_empty() -> None:
    """Clause two: no out-of-scope pillars would make every sweep vacuous."""
    assert _unmeasured(), "no pillar is outside this tool's own measurement"
    assert [p for p in PILLARS if p.scope in (Scope.OWNED, Scope.PARTIAL)], (
        "no in-scope pillars, so the contrast below proves nothing"
    )


def test_an_unmeasured_pillar_carries_no_practice_level() -> None:
    """Swept over every pillar outside this tool's measurement.

    Not over security alone, which is the instance the audit reported:
    efficiency had the same row for the same reason, and a check written
    from one would have left the other.
    """
    entries = {entry["pillar"]: entry for entry in _report()}
    for pillar in _unmeasured():
        entry = entries[pillar.name]

        assert entry["practice"] is None, (
            f"{pillar.name} is {pillar.scope.value} and reports practice "
            f"{entry['practice']}, which is this repository's level, not its own"
        )
        assert entry["condition"] is None, f"{pillar.name} reports a condition"


def test_no_skin_prints_a_digit_for_an_unmeasured_pillar() -> None:
    """The cell a reader sees, not only the field behind it.

    Nulling the field and leaving the renderer printing `str(None)`
    would satisfy the assertion above and put the word "None" in the
    table — which is how a reader learns the tool is broken rather than
    that the pillar was not measured.
    """
    entries = {entry["pillar"]: entry for entry in _report()}
    for pillar in _unmeasured():
        cell = practice_cell(entries[pillar.name])

        assert not any(character.isdigit() for character in cell), (
            f"{pillar.name}'s practice cell reads {cell!r}"
        )
        assert "none" not in cell.lower(), (
            f"{pillar.name}'s practice cell reads {cell!r} rather than a dash"
        )


def test_an_in_scope_pillar_still_reports_the_level() -> None:
    """The filter must not be a mute button.

    Practice is measured for the pillars this tool does own, and a fix
    that blanked the column everywhere would remove the axis ADR 007
    exists to keep beside condition.
    """
    entries = {entry["pillar"]: entry for entry in _report()}
    in_scope = [p for p in PILLARS if p.scope in (Scope.OWNED, Scope.PARTIAL)]
    for pillar in in_scope:
        entry = entries[pillar.name]

        assert entry["practice"] == PRACTICE["level"], pillar.name
        assert practice_cell(entry) == str(PRACTICE["level"]), pillar.name


def test_a_delegated_pillar_with_a_document_reports_the_producers_level() -> None:
    """The case that must keep a number, and a different one.

    `secure-code-agent` measures security practice and reports its own
    level. Blanking it would lose a real measurement, and showing this
    repository's 4 in its place is the defect one row over.
    """
    delegated = next((p for p in PILLARS if p.scope is Scope.DELEGATED), None)
    assert delegated, "no delegated pillar, so this asserts nothing"

    document = {"practice": {"level": 3, "signals": []}, "condition": 4.2,
                "posture": "healthy", "delegated_to": "secure-code-agent"}
    entry = {e["pillar"]: e for e in _report({delegated.name: document})}[delegated.name]

    assert entry["practice"] == 3, (
        "the delegated pillar lost the producer's own practice level"
    )
    assert entry["practice"] != PRACTICE["level"], (
        "the fixture cannot tell the producer's level from this repository's"
    )
    assert practice_cell(entry) == "3"
