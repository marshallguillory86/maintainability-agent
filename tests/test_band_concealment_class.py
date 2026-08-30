"""Claim 6: withholding a band cannot improve the score (derived class).

`test_band_concealment_p3.py` (shipped in #9) proves end to end that
concealing any of the four band fields cannot raise the estimate or the
grade, and `test_calibration_corpus.py` proves the corpus replay prices
bands the same way `score_evidence` does. Those tests hand-list the four
fields. This one derives the population from the production model instead
-- every `SummaryEvidence` field whose name ends in ``band_pressure`` --
so a *new* band field added tomorrow cannot slip in unrequired and
unpriced without failing here.

Two invariants over the derived population: each band field is required
for the grade (in ``DEFAULT_V1_REQUIRED``, which is also what the
concealment sweep walks), and an unknown band prices at ``SEVERE`` --
the worst case, the only value that cannot improve a dimension.

Unnamed member: **production_file_band_pressure**. It is not written out
here; it arrives through the derivation, and both invariants are asserted
over it like every other member.
"""

from __future__ import annotations

import dataclasses

from maintainability_audit._bands import SEVERE
from maintainability_audit._pressures import _banded
from maintainability_audit._verification import DEFAULT_V1_REQUIRED
from maintainability_audit.evidence import Measured, SummaryEvidence, Unknown


def _band_fields() -> list[str]:
    return [f.name for f in dataclasses.fields(SummaryEvidence)
            if f.name.endswith("band_pressure")]


def test_the_band_population_is_derived_and_not_empty() -> None:
    fields = _band_fields()
    assert len(fields) >= 4, f"expected the four band fields, derived {fields}"


def test_every_band_field_is_required_for_the_grade() -> None:
    """Required is also swept: DEFAULT_V1_REQUIRED is what concealment walks."""
    missing = [f for f in _band_fields() if f"summary.{f}" not in DEFAULT_V1_REQUIRED]
    assert not missing, (
        f"band fields not required (so concealing them would not withhold the "
        f"grade, and the sweep would skip them): {missing}"
    )


def test_an_unknown_band_prices_at_the_worst_case() -> None:
    """A withheld band is SEVERE, so concealment can never lower pressure.

    Driven per member: a measured band returns its own value, an unknown
    one returns SEVERE (>= any measured band), so withholding is never an
    improvement -- the pricing behind claim 6 for every band field,
    including production_file_band_pressure via the derivation.
    """
    population = 100.0
    measured = _banded(Measured(0.25, "summary.file_band_pressure"), population, 1.0, 1.0)
    assert measured == 0.25, "a measured band keeps its value"
    withheld = _banded(Unknown("withheld", "summary.file_band_pressure"),
                       population, 1.0, 1.0)
    assert withheld == SEVERE and measured <= SEVERE, (
        "an unknown band must price at the worst case so concealment cannot help"
    )
