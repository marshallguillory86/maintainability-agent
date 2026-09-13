"""The economic reorder never lifts a lower band above a higher one (D170).

ADR 007 §3 rule 5: Fill-Ins never appear above Quick Wins. ADR 004: the work
order reorders by exposure. `reorder_by_exposure` sorted on exposure alone,
so a Fill-In on a file that changes often led a Quick Win on a stable one.
Decided 2026-09-13: exposure orders items within a band; band stays primary.

The population is every ordered pair of bands, derived from the `Band`
enum — the declaration ADR 007 §3's matrix is read from — never a typed
list. Each pair is set up the hard way round: the lower band sits on the
hottest file with recurrence, the higher band on a file that never changed.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any


def _item(band: str, path: str, fingerprint: str) -> dict[str, Any]:
    return {"band": band, "path": path, "fingerprint": fingerprint,
            "title": f"{band} in {path}", "severity": 1.0, "risk": 1, "effort": 1,
            "class_delta": 0.0}


def test_no_exposure_lifts_a_lower_band_above_a_higher_one() -> None:
    from maintainability_audit._economics import reorder_by_exposure
    from maintainability_audit._work_order import Band

    bands = [band.value for band in Band]
    assert len(bands) >= 2, "the band matrix has fewer than two cells; nothing to order"
    pairs = list(combinations(bands, 2))  # declaration order: first outranks second
    assert pairs, "no band pairs derived"
    inverted = []
    for higher, lower in pairs:
        report = {
            "work_order": [
                _item(higher, "src/stable.py", "fp-higher"),
                _item(lower, "src/hot.py", "fp-lower"),
            ],
            "history": {"hotspots": [{"file": "src/hot.py", "commits": 500}]},
            "design_review_candidates": [{"fingerprint": "fp-lower", "returns": 9}],
        }
        reorder_by_exposure(report)
        order = [item["band"] for item in report["work_order"]]
        if order != [higher, lower]:
            inverted.append((higher, lower, order))
    assert not inverted, f"exposure placed a lower band first: {inverted}"


def test_exposure_still_orders_items_inside_one_band() -> None:
    """ADR 004 is kept, not retired: within a band the more-exposed item leads.

    Covers existing behaviour: exposure already led within a band before
    D170; this guards that making band primary did not switch exposure off.
    """
    from maintainability_audit._economics import reorder_by_exposure
    from maintainability_audit._work_order import Band

    for band in (band.value for band in Band):
        report = {
            "work_order": [_item(band, "src/stable.py", "a"), _item(band, "src/hot.py", "b")],
            "history": {"hotspots": [{"file": "src/hot.py", "commits": 50}]},
            "design_review_candidates": [],
        }
        reorder_by_exposure(report)
        assert [item["path"] for item in report["work_order"]] == ["src/hot.py", "src/stable.py"], band
