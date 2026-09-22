"""The complete-condition case stays unannotated (D206).

Covers existing behaviour: this passes at D206's base, where a pillar
whose aspects were all measured also printed no coverage note — because
nothing printed one at all.

It is here because the disclosure D206 added has an obvious wrong
version: annotate every row. That passes every assertion in
`test_the_condition_says_what_it_measured`, and it teaches a reader to
skip the sentence, which costs the disclosure exactly the thing it was
added for. A pillar whose aspects were all measured is already described
by its declared aspect list.

Kept out of the cited file so its citations stay evidence for D206
rather than being diluted by an assertion that proves nothing it
shipped.
"""

from __future__ import annotations

from test_the_condition_says_what_it_measured import _all_aspects, _entry, _in_scope

from maintainability_audit._scan_view import pillar_cells


def test_a_fully_measured_condition_says_nothing_extra() -> None:
    """The note is disclosure, not decoration.

    A pillar whose aspects were all measured is already described by its
    declared aspect list, and a coverage sentence on every row is how a
    reader learns to skip the row.
    """
    full = _all_aspects()
    for pillar in _in_scope():
        _, reading = pillar_cells(_entry(pillar.name, full, []))

        assert f"of {len(pillar.aspects)} aspects" not in reading, (
            f"{pillar.name} annotates a complete condition: {reading!r}"
        )
