"""Guards on the withholding filter that already held (D207).

Covers existing behaviour: all three pass at D207's base.

A run that withholds nothing listed everything before this change,
because nothing was ever filtered — and that is exactly why it has to be
asserted now. The obvious wrong version of this fix is a filter that is
really a mute button, and such a filter passes the entry's own
falsifier, which only ever asks whether withheld targets are absent.

The escalation clause for risk findings was fixed by the audit of
`e88b429`, so asserting it again cannot falsify this entry. It is held
because D207 rewrote the code path that enforces it, and a fix that
quietly dropped the older clause while adding the newer one would look
identical from the falsifier's side.

The fixture guard is here rather than inline for the same reason: a
report that lost a finding class would pass every assertion while saying
nothing about that class, which is the mechanism that let this defect
survive one fix.

Kept out of the cited file so its citation stays evidence for D207.
"""

from __future__ import annotations

from test_the_prompt_does_not_take_back_what_it_withheld import (
    CLASSES,
    _identity_of,
    _report,
    _withheld,
)

from maintainability_audit._prompt_sections import prompt_focus_sections


def test_the_population_is_every_class_the_focus_sections_render() -> None:
    """A guard against the fixture quietly shrinking.

    A report missing a class would pass every assertion in the cited
    file while saying nothing about that class — which is exactly how
    this defect survived one fix.
    """
    report = _report()
    withheld = _withheld(report)

    assert len(withheld) == len(CLASSES), (
        f"fixture withholds {len(withheld)} of {len(CLASSES)} classes"
    )
    for _, key, _finding in CLASSES:
        assert report.get(key), f"fixture carries no {key} finding"


def test_a_report_that_withholds_nothing_still_lists_everything() -> None:
    """The filter must not be a mute button.

    Withholding is the exception; a run with no Major Projects and no
    escalations has to produce the same focus lists it always did, or
    this fix trades a contradiction for an empty prompt.
    """
    report = _report()
    report["work_order"] = [
        {**item, "band": "quick-win"} for item in report["work_order"]
    ]
    text = "\n".join(prompt_focus_sections(report))

    for _, key, _finding in CLASSES:
        assert report[key], key
    for path in ("dup.py", "near.py", "dead.py", "idiom.py", "risk.py"):
        assert path in text, f"{path} vanished from a prompt that withheld nothing"


def test_an_escalated_return_is_withheld_from_every_class_that_can_carry_one() -> None:
    """The older clause, over every class the data model lets it reach.

    Escalation is keyed on a fingerprint, and only some finding classes
    have one: `_items_from_counted` says risk patterns are "the one
    class here the report gives a stable identity to", and hotspots and
    large files get theirs from `declaration_identities` and
    `file_fingerprint`. Duplicate blocks, near-duplicates, dead code and
    competing libraries cannot be escalated at all, because nothing can
    name the same one twice across runs — they are reached by the Major
    Project clause, which is location-keyed.

    So the population is the classes whose work-order item carries a
    fingerprint, derived by asking the items rather than by listing
    classes here.
    """
    report = _report()
    identified = [
        (item, _identity_of(report, item))
        for item in report["work_order"]
    ]
    identified = [(item, ident) for item, ident in identified if ident]

    assert identified, "no class in the fixture carries an identity to escalate"

    for item, ident in identified:
        item["band"] = "quick-win"
        item["fingerprint"] = ident
    report["design_review_candidates"] = [{"fingerprint": ident} for _, ident in identified]

    text = "\n".join(prompt_focus_sections(report))

    offenders = [item["path"] for item, _ in identified if item["path"] in text]
    assert not offenders, (
        f"escalated findings listed as work: {sorted(set(offenders))}\n\n{text}"
    )
