#!/usr/bin/env python3
"""Is the constant's change a finding, or is it resampling noise?

`CALIBRATION_C` is fitted so the corpus median rolls up to 4.0. When the
corpus changes — a defect fixed, generated code excluded — the fitted
value moves, and "should we adopt the new one" has been treated as a
judgment call. It is not one. It is three measurable questions:

1. **Is the shift distinguishable from sampling noise?** The corpus is 40
   repositories drawn from a much larger population of mature OSS. A
   different 40 would fit a different constant. Bootstrapping the corpus
   gives the sampling distribution of `c`, and if the shipped value sits
   comfortably inside it, the data does not support calling the new value
   different from the old one.

2. **Does each constant do its job?** The constant exists so the corpus
   median rolls to 4.0. Whether it still does is checkable, not arguable.

3. **Does the difference reach anybody?** Scores are published to one
   decimal. A constant that moves the median repository by 0.02 changes
   no report, whatever the third decimal says.

Answering 1 without 3 is the classic error: a difference can be reliably
detected and still be too small to act on, especially with a resampled
statistic where enough iterations will separate almost anything.

    python tools/calibration/sampling_error.py --iterations 2000
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from maintainability_audit._calibration import (  # noqa: E402
    CALIBRATION_C,
    DIMENSION_REFERENCES,
)
from maintainability_audit._derive import (  # noqa: E402
    _corpus_overall,
    derive_curve_constant,
    derive_references,
)

MEASUREMENTS = Path(__file__).with_name("measurements.json")


def _fit(sample: list[dict], references: dict[str, float]) -> float:
    return derive_curve_constant(sample, references, {})


def bootstrap(rows: list[dict], iterations: int, seed: int) -> list[float]:
    """The sampling distribution of `c` over resampled corpora.

    Resampled *with replacement* at the same size, which is what a
    bootstrap of a 40-unit sample means: each draw is a plausible
    alternative corpus this project could have selected under the same
    frame. References are re-derived per draw, because in a real
    reselection they would be.
    """
    rng = random.Random(seed)
    fitted: list[float] = []
    for index in range(iterations):
        draw = [rng.choice(rows) for _ in rows]
        fitted.append(_fit(draw, derive_references(draw)))
        if (index + 1) % 100 == 0:
            print(f"  {index + 1}/{iterations}", end="\r", flush=True, file=sys.stderr)
    return sorted(fitted)


def score_shift(rows: list[dict], references: dict[str, float],
                old: float, new: float) -> list[tuple[str, float, float]]:
    """Every repository's overall under each constant."""
    return [
        (row["repo"],
         _corpus_overall(row, references, old),
         _corpus_overall(row, references, new))
        for row in rows
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260812)
    args = parser.parse_args()

    payload = json.loads(MEASUREMENTS.read_text(encoding="utf-8"))
    rows = payload["measurements"]
    references = derive_references(rows)
    measured = _fit(rows, references)

    print(f"corpus: {len(rows)} repositories, measured {payload['measured_on']}")
    print(f"shipped constant : {CALIBRATION_C}")
    print(f"measured constant: {measured}\n")

    print(f"bootstrap: {args.iterations} resamples of {len(rows)} with replacement")
    draws = bootstrap(rows, args.iterations, args.seed)
    lower = draws[int(len(draws) * 0.025)]
    upper = draws[int(len(draws) * 0.975)]
    inside = lower <= CALIBRATION_C <= upper
    below = sum(1 for value in draws if value <= CALIBRATION_C) / len(draws)

    print(f"  median        {statistics.median(draws):.4f}")
    print(f"  95% interval  [{lower:.4f}, {upper:.4f}]  width {upper - lower:.4f}")
    print(f"  shipped {CALIBRATION_C} lies {'INSIDE' if inside else 'OUTSIDE'} that interval")
    print(f"  {below:.1%} of resampled corpora fit a constant at or below the shipped one\n")

    print("does each constant do its job (corpus median rolls to 4.0)?")
    for label, value in (("shipped", CALIBRATION_C), ("measured", measured)):
        overalls = [_corpus_overall(row, references, value) for row in rows]
        print(f"  {label:8s} c={value:<8.4f} corpus median rollup = "
              f"{statistics.median(overalls):.2f}")
    print()

    print("effect on published scores (one decimal place)")
    shifts = score_shift(rows, references, CALIBRATION_C, measured)
    deltas = sorted(abs(new - old) for _, old, new in shifts)
    changed = [(name, old, new) for name, old, new in shifts
               if round(old, 1) != round(new, 1)]
    print(f"  median |delta|  {statistics.median(deltas):.4f}")
    print(f"  max |delta|     {deltas[-1]:.4f}")
    print(f"  repositories whose published (1dp) score changes: "
          f"{len(changed)} of {len(rows)}")
    for name, old, new in changed[:10]:
        print(f"    {name:22s} {old:.2f} -> {new:.2f}   ({round(old, 1)} -> {round(new, 1)})")

    print("\nreference dimensions, shipped vs measured")
    for name, shipped in sorted(DIMENSION_REFERENCES.items()):
        now = references.get(name)
        if now is None:
            continue
        change = (now - shipped) / shipped * 100 if shipped else float("nan")
        print(f"  {name:14s} {shipped:8.4f} -> {now:8.4f}  ({change:+.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
