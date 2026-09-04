"""Did any dimension get worse than the last comparable scan?

The third mechanism behind the attestation. `--fail-on-new` already catches
a finding that clears and returns, using structured identity so a rename is
not a new finding. What nothing caught is the slower failure: a change that
improves one dimension while quietly regressing another. Both scans are
green by every existing gate, the overall estimate can even rise, and the
thing that got worse is never named.

**The comparison is only honest inside one segment.** History is already
split wherever the instrument changed — a different calibration constant, a
different analyzer population — because two scans taken with different
instruments cannot be subtracted. `_scan_history.segments` owns that rule,
and this module refuses rather than reaching across a break. A ratchet that
compared a 1.x score to a 2.0 score would have reported every repository on
earth as catastrophically regressed on the day the corpus was extended, and
it would have been the ratchet that was wrong.

So there are three outcomes, not two: **held**, **regressed**, and **not
comparable**. The third is not a pass. It says the question could not be
asked, which is what a reader needs in order to know they are not being
reassured by silence.
"""

from __future__ import annotations

from typing import Any

from ._scan_history import ScanRecord, segments

#: Scores are reported to one decimal, so a difference below this is the
#: rounding boundary rather than a movement. Named rather than inlined
#: because it is a judgment: too tight and every scan trips on noise, too
#: loose and a real slide hides under the threshold.
TOLERANCE = 0.05


def _series(record: ScanRecord, field: str) -> dict[str, float]:
    values = getattr(record, field, None) or {}
    return {
        name: float(value) for name, value in values.items()
        if isinstance(value, (int, float))
    }


def _regressions(
    previous: ScanRecord, current: ScanRecord, field: str
) -> list[dict[str, Any]]:
    """Names that dropped, with the size of the drop."""
    before, after = _series(previous, field), _series(current, field)
    found = []
    for name, was in sorted(before.items()):
        # A name the current scan does not carry is not a regression: the
        # aspect became unmeasurable, which the evidence model already
        # reports as `Unknown` rather than as a zero. Scoring it as a drop
        # to nothing would turn withheld evidence into a failure, which is
        # the exact inversion P3 forbids.
        if name not in after:
            continue
        now = after[name]
        if was - now > TOLERANCE:
            found.append({
                "name": name, "was": round(was, 2),
                "now": round(now, 2), "drop": round(was - now, 2),
            })
    return found


def dimension_ratchet(records: list[ScanRecord]) -> dict[str, Any]:
    """Compare the newest scan with the previous comparable one.

    `comparable` is the load-bearing field. False means the two scans sit
    either side of an instrument change, or there is no earlier scan at
    all — in both cases the question was not asked, and a caller must not
    read that as "nothing regressed".
    """
    if len(records) < 2:
        return {
            "comparable": False,
            "reason": "no earlier scan to compare against",
            "regressed": [],
        }

    latest = segments(records)[-1]
    if len(latest.records) < 2:
        return {
            "comparable": False,
            "reason": (
                latest.break_reason
                or "the previous scan was taken with a different instrument"
            ),
            "regressed": [],
        }

    previous, current = latest.records[-2], latest.records[-1]
    categories = _regressions(previous, current, "categories")
    aspects = _regressions(previous, current, "aspects")

    return {
        "comparable": True,
        "against": getattr(previous, "commit", None),
        "categories": categories,
        "aspects": aspects,
        # Categories only. An aspect can move while the category holding it
        # holds, and failing on every aspect wobble makes the gate noise.
        # Aspects are reported so a reader can see what moved underneath.
        "regressed": categories,
        "held": not categories,
    }
