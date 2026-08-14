#!/usr/bin/env python3
"""Decide what may honestly be claimed from ``cohorts.json``.

Measuring two cohorts is the easy half. The hard half is not fooling
yourself with the result, and this project has already published one
finding that did not survive its own control — 0.6.0 reported
near-duplication as the signal separating AI-written from human-written
code, on a comparison of six young applications against twelve mature
libraries.

So the claim has to clear three bars, in order:

1. **Do the cohorts differ at all?** Mann-Whitney on the medians, because
   both tails are heavy enough that means would be theatre.
2. **Does size predict the metric?** Reported as a rank correlation
   beside every p-value. Any metric that rises with codebase size will
   separate two cohorts of different sizes for arithmetic reasons.
3. **Does the difference survive equal sizes?** Both cohorts are
   restricted to the overlap of their declaration ranges and retested. A
   difference that evaporates here was about size.

Five metrics are tested at once. That does not license waving away every
sub-0.05 result as chance — the expected chance yield of five tests at
alpha = 0.05 is a quarter of a test, and two landed under it here. What
it does mean is that no single row settles anything: the size
correlation column and the banded re-test are where those two rows get
their actual explanation. Read the whole table, not the best row.

    python3 tools/calibration/analyze_cohorts.py tools/calibration/cohorts.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from measure_cohorts import METRICS, mann_whitney  # noqa: E402

COHORTS = Path(__file__).with_name("cohorts.json")


def rank(values: list[float]) -> list[float]:
    """Ranks with ties averaged, matching the rank-sum test's convention."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(order):
        stop = index
        while stop + 1 < len(order) and values[order[stop + 1]] == values[order[index]]:
            stop += 1
        shared = (index + stop) / 2 + 1
        for position in range(index, stop + 1):
            ranks[order[position]] = shared
        index = stop + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float:
    """Rank correlation, so one enormous repository cannot set the answer."""
    ranked_x, ranked_y = rank(xs), rank(ys)
    count = len(xs)
    mean_x, mean_y = sum(ranked_x) / count, sum(ranked_y) / count
    covariance = sum((a - mean_x) * (b - mean_y) for a, b in zip(ranked_x, ranked_y, strict=True))
    spread = (
        sum((a - mean_x) ** 2 for a in ranked_x) * sum((b - mean_y) ** 2 for b in ranked_y)
    ) ** 0.5
    return covariance / spread if spread else 0.0


def size_band(treatment: list[dict], control: list[dict]) -> tuple[list[dict], list[dict], int, int]:
    """Both cohorts restricted to the declaration range they share."""
    low = max(min(r["declarations"] for r in treatment), min(r["declarations"] for r in control))
    high = min(max(r["declarations"] for r in treatment), max(r["declarations"] for r in control))
    keep = lambda group: [r for r in group if low <= r["declarations"] <= high]  # noqa: E731
    return keep(treatment), keep(control), low, high


def table(rows: list[tuple[str, ...]], headers: tuple[str, ...], width: int = 11) -> None:
    print("".join(h.ljust(26) if i == 0 else h.rjust(width) for i, h in enumerate(headers)))
    print("-" * (26 + width * (len(headers) - 1)))
    for row in rows:
        print("".join(c.ljust(26) if i == 0 else c.rjust(width) for i, c in enumerate(row)))


def _full_rows(treatment: list[dict], control: list[dict], mature: list[dict]) -> list[tuple[str, ...]]:
    pooled = treatment + control
    rows = []
    for metric in METRICS:
        test = mann_whitney([r[metric] for r in treatment], [r[metric] for r in control])
        rows.append((
            metric,
            f"{median(r[metric] for r in treatment):.4f}",
            f"{median(r[metric] for r in control):.4f}",
            f"{median(r[metric] for r in mature):.4f}" if mature else "-",
            f"{test['p']:.3f}" if test else "n/a",
            f"{spearman([r['declarations'] for r in pooled], [r[metric] for r in pooled]):.2f}",
        ))
    return rows


def _banded_rows(treatment: list[dict], control: list[dict]) -> list[tuple[str, ...]]:
    rows = []
    for metric in METRICS:
        test = mann_whitney([r[metric] for r in treatment], [r[metric] for r in control])
        rows.append((
            metric,
            f"{median(r[metric] for r in treatment):.4f}",
            f"{median(r[metric] for r in control):.4f}",
            f"{test['p']:.3f}" if test else "n too small",
        ))
    return rows


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else COHORTS
    data = json.loads(path.read_text(encoding="utf-8"))
    cohorts = data["cohorts"]
    treatment, control = cohorts["ai"]["repos"], cohorts["human"]["repos"]
    mature = cohorts.get("mature-oss", {}).get("repos", [])

    print(f"n: ai={len(treatment)} human={len(control)} mature-oss={len(mature)}\n")
    table(_full_rows(treatment, control, mature), ("metric", "ai", "human", "mature", "p", "size r"))

    banded_treatment, banded_control, low, high = size_band(treatment, control)
    print(
        f"\nsize-banded to {low}-{high} declarations: "
        f"ai n={len(banded_treatment)} human n={len(banded_control)}"
    )
    table(_banded_rows(banded_treatment, banded_control), ("metric", "ai", "human", "p"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
