# Extending the calibration corpus to eight languages

**Genre: empirical.** Every number here is reproducible from checked-in
pinned inputs: `tools/calibration/corpus.json` names the repositories and
the commits, `tools/calibration/measurements.json` holds the readings, and
`tools/calibration/measure.py --check` re-derives the constants from them.

## The question

Every score this tool reports is a multiple of a corpus median. Through
1.10.1 that corpus was **40 repositories of Python, TypeScript and
JavaScript**, while the scanner parsed **eight** languages. Java, C, C++, C#
and Fortran were scored against medians measured on none of their code.

The motivating observation was a single number: audited against the old
anchor, **LAPACK reported declarations at 7.18x the median**, and
fortran-lang/stdlib at 1.10x. The first is a true statement about LAPACK
relative to mature open-source *web* code, and not a statement about
Fortran, because no Fortran was in the comparison set.

## Method

**Selection is mechanical and unchanged**: `language:X stars:>N
created:<2021-01-01 pushed:>2026-01-01`, under an 800 MB size cap, filtered
by a name-marker list for curricula and link collections, then verified by
cloning each candidate and requiring ≥20 source files and ≥100
declarations. Only the language list changed.

**One deliberate exception.** The star bar is per language, because 3,000
stars is not the same statement in every ecosystem. Fortran has **zero**
repositories above it; its most-starred serious projects sit between
roughly 900 and 1,900 (LAPACK, WRF, Elmer, stdlib, CP2K). A single
threshold would have measured popularity rather than maturity and excluded
the language outright, so Fortran entered at 500. The thresholds are
recorded in `corpus.json` under `selection.min_stars`.

**The original 40 rows are unchanged and still pinned** to the commits they
were measured at. Adding languages is the only variable, so the constants
moved because of the languages and not because the corpus was re-rolled.

**One member was replaced after selection.** `CPlusPlusThings` is a C++
teaching repository; the marker list gained `"things"` so that category is
excluded mechanically rather than by veto. It was found by its measurements
(declarations 0.0078 against a 0.1005 reference) rather than by its name —
the outcome-triggered discovery a mechanical corpus exists to prevent, and
recorded here for the same reason `33-js-concepts` was. Re-running
selection with the new marker changed exactly one member; `googletest` took
its place.

## The corpus

112 repositories, all measured `--with-analyzers`:

| Language | Repositories | Star threshold |
|---|---|---|
| C++ | 16 | 3,000 |
| C | 16 | 3,000 |
| TypeScript | 15 | 3,000 |
| C# | 15 | 3,000 |
| Java | 14 | 3,000 |
| Python | 13 | 3,000 |
| JavaScript | 12 | 3,000 |
| Fortran | 11 | **500** |

## What the constants did

| Dimension | 1.x | 2.0 | Move |
|---|---|---|---|
| `file_size` | 0.0858 | 0.0952 | +11% |
| `declarations` | 0.1005 | 0.0908 | −10% |
| `duplication` | 0.28 | 0.3222 | +15% |
| `risk` | 0.0737 | 0.0826 | +12% |
| `gates` | 0.05 | 0.05 | — |
| **`CALIBRATION_C`** | **5.8843** | **8.7161** | **+48%** |

`CALIBRATION_C` is fitted by bisection so the corpus median *rolls up* to
4.0 through the full rubric — aspects, then categories, then the overall —
not through a closed-form curve. `measure.py --check` re-derives all six
values from the stored measurements and reports no drift.

## The result that contradicted the motivation

**`declarations` fell.** The number that motivated this work implied the
opposite, and the per-language medians explain why. Each cell is that
language's median reading as a multiple of the new reference:

| Language | file_size | declarations | duplication | risk | n |
|---|---|---|---|---|---|
| Fortran | 2.36x | **3.90x** | **4.30x** | 1.02x | 11 |
| C | 2.34x | 2.07x | 1.19x | **2.42x** | 16 |
| C++ | 1.33x | 0.93x | 1.08x | 2.04x | 16 |
| Python | 1.01x | 0.78x | 0.49x | 1.75x | 13 |
| JavaScript | 0.79x | 0.96x | 1.28x | 0.31x | 12 |
| TypeScript | 0.73x | 1.08x | 0.78x | 0.98x | 15 |
| C# | 0.72x | 0.92x | 0.88x | 0.52x | 15 |
| Java | 0.65x | 0.41x | 0.69x | 0.58x | 14 |
| **All 112** | 1.00x | 1.01x | 1.00x | 1.00x | 112 |

**"Systems code" was the wrong unit of analysis.** C (2.07x) and Fortran
(3.90x) do carry denser declarations, exactly as LAPACK suggested. Java
(0.41x), C# (0.92x) and C++ (0.93x) carry fewer — and there are 45 of those
against 27 of the first, so the aggregate median fell. The languages do not
behave as a bloc, and one dramatic repository predicted the direction of
the whole corpus incorrectly.

Two further readings worth stating:

- **Fortran is the outlier language, not just LAPACK.** At 3.90x
  declarations and 4.30x duplication it is furthest from every other
  member. LAPACK's 7.18x was extreme even against Fortran's own median,
  so the old anchor overstated LAPACK twice over: once for not holding
  Fortran, and once for LAPACK being unusual within it.
- **Risk is where C separates.** 2.42x against a corpus median of 1.00x,
  with C++ at 2.04x. That dimension is a regex policy over patterns like
  unbounded string handling, so this is close to a definitional result
  rather than a discovery — worth stating so nobody reads it as one.

## What this does not establish

- **It is not a quality ranking of languages.** These are medians of
  structural readings over a small, deliberately non-random sample of
  popular open-source projects. Fortran at 3.90x declarations describes
  eleven numerical codebases, not Fortran.
- **The samples are small and uneven.** Eleven Fortran repositories against
  sixteen C++ ones, and a different star threshold for one of them.
- **Mature open source is not enterprise-internal code**, which remains the
  frame's standing limit and is unchanged by this work.
- **Nothing here says a score predicts anything.** The rubric remains a
  standard, not a predictor; see [studies](studies.md) for what has and has
  not been tested.

## Reproducing it

```bash
# Re-derive the constants from the pinned corpus; writes nothing.
python3 tools/calibration/measure.py --check --with-analyzers --reuse \
  --cache-dir /path/to/cache

# Re-measure from scratch (roughly 90 minutes, ~7 GB of clones).
python3 tools/calibration/measure.py --with-analyzers \
  --cache-dir /path/to/cache
```

`--reuse` reuses a stored row only when its pinned commit, analyzer
population and **scanner fingerprint** all still match, and measures the
rest — so adding a ninth language costs its own repositories rather than
all 112. The fingerprint is a digest of the modules that can change a
measurement, not the release number: keying on the version re-measured 112
repositories for a documentation release and would have said nothing if the
scanner changed within one version.

A corpus measured on two different versions of one analyzer is not a
corpus, so a run that would mix them refuses to fit constants and names the
tool.
