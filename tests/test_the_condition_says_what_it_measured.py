"""A pillar's condition names what produced it (D206).

`_condition` is the mean of the aspects that carried a number. That is
the only honest arithmetic — a `None` is not a zero and inventing one
would be worse — and it is not the whole story, because dropping an
aspect is not the same as it having scored well.

Measured, maintainability's seven aspects with one bad one average
**4.43**. Withhold that one aspect and the same pillar reads **5.0**,
and until this change both printed as a bare number beside the same
declared list of seven. That is P3's shape — *withholding evidence
cannot improve the reported grade*, falsified by any input whose removal
raises the reported field — and P8's — *every report states what
examined it*, falsified by a reported value with no attributable source.

**The overall grade is already defended and the condition was not.**
`_grade_on_the_floor` prices unknowns at 0 and bands from the floor, so
concealment is monotonically unprofitable there. Flooring a pillar's
condition would be wrong: [ADR 007](../docs/adr-007-pillars-and-practice.md)
defines it as the mean of measured aspects, and a delegated pillar's
condition arrives already computed by the tool that owns it, so
flooring one side would make the two incomparable in the same column.
Disclosure is the defence.

The population is `PILLARS` — every in-scope pillar and its own declared
aspects, read from the module that defines them — never a list typed
here, so a sixth pillar or a re-cut aspect set is covered the moment it
exists.
"""

from __future__ import annotations

from typing import Any

from maintainability_audit._pillars import PILLARS, Scope, pillar_report
from maintainability_audit._scan_view import pillar_cells

PRACTICE = {"level": 4}


def _in_scope() -> list[Any]:
    return [p for p in PILLARS if p.scope in (Scope.OWNED, Scope.PARTIAL)]


def _all_aspects() -> dict[str, float]:
    """Every in-scope aspect, scored, derived from the pillar definitions."""
    return {name: 5.0 for pillar in _in_scope() for name in pillar.aspects}


def _entry(pillar_name: str, scores: dict[str, Any], not_applicable: list[str]) -> dict:
    report = pillar_report(
        {"aspects": scores, "not_applicable": not_applicable}, PRACTICE
    )
    return next(entry for entry in report if entry["pillar"] == pillar_name)
def test_every_partial_condition_says_how_many_aspects_made_it() -> None:
    """Swept over every in-scope pillar and every one of its aspects.

    Not the one instance that motivated this: withholding *any* single
    aspect of *any* in-scope pillar must change what the reading says,
    and the mutation that matters is an aspect the test does not name.
    """
    full = _all_aspects()
    # Clause two: an empty pillar set passes every assertion below.
    assert _in_scope() and full, "no in-scope aspects, so this sweeps nothing"
    checked = 0
    for pillar in _in_scope():
        for withheld in pillar.aspects:
            scores = {k: v for k, v in full.items() if k != withheld}
            entry = _entry(pillar.name, scores, [])
            _, reading = pillar_cells(entry)
            total = len(pillar.aspects)

            assert f"from {total - 1} of {total} aspects" in reading, (
                f"{pillar.name} withholding {withheld} reads {reading!r}, which "
                f"never says the condition came from {total - 1} of {total}"
            )
            assert withheld in reading, (
                f"{pillar.name} does not name {withheld} as unmeasured: {reading!r}"
            )
            checked += 1

    assert checked == sum(len(p.aspects) for p in _in_scope())
def test_missing_evidence_and_a_resolved_absence_read_differently() -> None:
    """"Could not measure" and "nothing to measure" are opposite claims.

    Collapsing them is how an unknown reads as clean, which is the
    distinction `_evidence_rules` has always made for the grade and the
    report kept only the consequence of.
    """
    full = _all_aspects()
    assert _in_scope() and full, "no in-scope aspects, so this sweeps nothing"
    for pillar in _in_scope():
        withheld = pillar.aspects[0]
        scores = {k: v for k, v in full.items() if k != withheld}
        _, unknown = pillar_cells(_entry(pillar.name, scores, []))
        _, resolved = pillar_cells(_entry(pillar.name, scores, [withheld]))

        assert "not measured:" in unknown, unknown
        assert "nothing to measure:" in resolved, resolved
        assert unknown != resolved, (
            f"{pillar.name} reads identically whether {withheld} was missing "
            "evidence or had no population to measure"
        )


def test_withholding_the_worst_aspect_raises_the_number_and_says_so() -> None:
    """The P3 instance, kept as the worked example.

    The rise is real and stays: the mean of what was measured is the
    honest arithmetic. What must never happen again is the rise being
    silent.
    """
    pillar = next(p for p in _in_scope() if len(p.aspects) > 1)
    full = {name: 5.0 for name in pillar.aspects}
    worst = pillar.aspects[0]
    full[worst] = 1.0

    complete = _entry(pillar.name, full, [])
    withheld = _entry(pillar.name, {k: v for k, v in full.items() if k != worst}, [])

    assert withheld["condition"] > complete["condition"], (
        "the worked example no longer demonstrates the rise this defends against"
    )
    assert "of" in pillar_cells(withheld)[1] and worst in pillar_cells(withheld)[1]
    assert pillar_cells(complete)[1] != pillar_cells(withheld)[1]
