#!/usr/bin/env python3
"""Fail once the calibration corpus is older than its age limit.

The calibration describes the code of the moment it was measured. 180
repositories pinned at commits is the right way to make it reproducible, and
it is still a snapshot — the one number in this project that silently stops
being true. `CORPUS_MEASURED` records the moment; this check turns its age
into a signal. Run weekly by `.github/workflows/maintenance.yml`, where a
failure opens a standing issue rather than a red run nobody reads.

It does not block a release: an urgent fix must not wait on a recalibration.
It asks for a decision — re-measure the corpus, or consciously re-affirm it by
raising the limit with a reason.

Usage: python3 tools/check_corpus_age.py [max_days]      # default 365
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

#: How old the corpus may get before the weekly check asks for a decision.
#: A product choice, set 2026-09-24 as a default: one year.
MAX_DAYS = 365


def verdict(measured: str, today: dt.date, max_days: int = MAX_DAYS) -> str | None:
    """What is wrong with a corpus measured on `measured`, as of `today`."""
    age = (today - dt.date.fromisoformat(measured)).days
    if age <= max_days:
        return None
    return (
        f"The calibration corpus was measured on {measured}, {age} days ago, past the "
        f"{max_days}-day limit. Recalibrate (tools/calibration/) or re-affirm it by raising "
        "MAX_DAYS in tools/check_corpus_age.py with the reason the old corpus still holds."
    )


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from maintainability_audit._calibration import CORPUS_MEASURED

    limit = int(argv[1]) if len(argv) > 1 else MAX_DAYS
    complaint = verdict(CORPUS_MEASURED, dt.date.today(), limit)
    if complaint:
        print(complaint)
        return 1
    print(f"calibration corpus measured {CORPUS_MEASURED}: within {limit} days")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
