# Migrating from 1.x to 2.0

**Genre: reference.** What changes the number after 1.10.1, what does not,
and what you can ignore.

**One thing changes a score, and it changes every score.** The reference
corpus — the set of repositories whose medians every reported multiple is a
multiple *of* — went from 40 repositories in three languages to 112 across
all eight the scanner parses. `CALIBRATION_C` and the per-dimension
references move with it, so a repository whose code did not change will
still grade differently.

Nothing else in this release touches a score. The report schema does not
break, baselines remain valid, finding identity is unchanged, and no
threshold moved.

```bash
# 1. Same command. Scores move because the scale moved, not because
#    anything about your repository did.
maintainability-agent --root . --config maintainability-agent.json

# 2. Regenerate any baseline you gate on, so "new findings" stays a
#    statement about your code rather than about the anchor.
maintainability-agent --config maintainability-agent.json \
  --write-baseline maintainability-baseline.json

# 3. Do not compare a 1.x number to a 2.0 number as if they were the
#    same measurement. They are readings from two different instruments.
```

---

## Why the anchor changed

For five releases the tool parsed eight languages and calibrated against
three. Java, C, C++, C# and Fortran were scored against medians measured on
none of their code — and the effect was not theoretical. Audited against
the old anchor, LAPACK reported declarations at **7.18x** the median and
fortran-lang/stdlib at **1.10x**. The first figure is a true statement about
LAPACK relative to mature open-source *web* code. It is not a statement
about typical Fortran, because no typical Fortran was in the comparison
set.

The uniform rubric was never the problem — that is the promise
([P2](product-intent.md#what-it-promises)), and it is intact. The corpus
was the problem, and the fix is to extend it rather than to soften the
disclosure or to introduce per-language references, which would trade a
stated limit for a silent breach of the one-rubric promise.

## What was held constant, deliberately

The original 40 rows are **unchanged and still pinned** to the commits they
were measured at. Adding languages is the only variable, so whatever the
constants did, they did it because of the languages and not because the
corpus was re-rolled underneath them.

Selection is the same mechanical query — created before 2021, pushed since
2026, under the size cap — with one stated exception. **Fortran entered at
a 500-star threshold rather than 3,000**, because the entire Fortran
ecosystem has zero repositories above the bar the other seven use; its
most-starred serious projects sit between roughly 900 and 1,900 stars
(LAPACK, WRF, Elmer, stdlib, CP2K). Holding one number across ecosystems
would have measured popularity rather than maturity and excluded the
language outright. The per-language thresholds are recorded in
`tools/calibration/corpus.json` under `selection.min_stars`.

One member changed for a reason worth stating plainly: `CPlusPlusThings` is
a C++ teaching repository, and the marker list gained `"things"` so that
category is excluded mechanically rather than by veto. It was found by its
measurements rather than by its name, which is the outcome-triggered
discovery a mechanical corpus exists to prevent — the same disclosure
`33-js-concepts` received. Re-running selection with the new marker changed
exactly one member; `googletest` took its place.

## What moved

The constants below are derived by `tools/calibration/measure.py` from the
pinned corpus and are reproducible from it.

<!-- constants:begin -->
| Dimension | 1.x | 2.0 |
|---|---|---|
| `file_size` | 0.0858 | 0.0952 |
| `declarations` | 0.1005 | 0.0908 |
| `duplication` | 0.28 | 0.3222 |
| `risk` | 0.0737 | 0.0826 |
| `gates` | 0.05 | 0.05 |
| **`CALIBRATION_C`** | **5.8843** | **8.7161** |

`CALIBRATION_C` is fitted by bisection so the corpus median rolls up to 4.0
through the full rubric. The direction a given repository moves depends on
its own mix, because four of the five references moved as well — a
repository heavy on duplication and light on declarations does not move the
same way as its opposite.

**`declarations` fell, which the motivating evidence did not predict**, and
the per-language readings explain why: C and Fortran are heavy, Java, C# and
C++ are light, and there are more of the latter. The full breakdown, method
and limits are in [the calibration study](calibration-2.0-study.md).
<!-- constants:end -->

## What did not change

- **The report schema.** No consumer migration is required.
- **Baselines and finding identity.** A v3 baseline written by 1.x is still
  valid; regenerating it is about gating on the new scale, not about
  compatibility.
- **Thresholds and hard gates.** `--fail-on-gate` fails on the same
  conditions, and it never consumed a letter grade.
- **What is withheld.** A `--changed-only` diff is still not a repository
  grade, and a score is still withheld where the evidence cannot support
  one.

## If you pin the anchor rather than the tool

Nothing forces you onto the new scale. `CALIBRATION_C` and the references
live in `src/maintainability_audit/_calibration.py` with their previous
values recorded beside them, so an organization that has built thresholds
on the 1.x scale can hold that scale by pinning the package version. The
honest framing is that you are then measuring against an anchor that omits
five of the languages you may be scoring, which is the limit this release
exists to remove.
