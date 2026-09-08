"""Which declarations the analyzer tier may score — the D137 seam.

Split out of `_pressures.py` when that module crossed the 500-line gate
this tool enforces on everyone else. The seam is real rather than
arithmetic: everything here answers one question — *may this declaration
be scored by an analyzer reading at all?* — and nothing else answers it.

That question has been got wrong five times. `test_analyzer_bridge`
records the first four, each a ratio published before the comparison
could be trusted. The fifth, D137, was this: the completeness check took
a union of concepts across the whole repository while the units it gated
were scored one at a time, so a C repository holding a single `setup.py`
had its C declarations scored on two criteria of three. Keeping the
decision in one module, returning the population rather than a verdict,
is what stops a sixth from arriving by scoping the check differently
from the thing it gates.
"""
from __future__ import annotations

import posixpath
from collections import defaultdict
from pathlib import PurePosixPath

from ._metrics_types import KNOWN_SOURCE_SUFFIXES, Measurement

# The concepts the `declarations` dimension needs, and the rubric
# thresholds that decide a breach. All three, because `function_status`
# fails a declaration on **lines OR complexity OR cognitive complexity**
# — a bridge counting only complexity measures something narrower and
# cannot be compared against it. Three ratios were quoted from that
# mistake before a test comparing every criterion caught it.
DECLARATION_CRITERIA: tuple[tuple[str, str, str], ...] = (
    ("cyclomatic_complexity", "warn_complexity", "max_complexity"),
    ("declaration_lines", "warn_function_lines", "max_function_lines"),
    ("cognitive_complexity", "warn_cognitive_complexity", "max_cognitive_complexity"),
)

# Dimensions an analyzer can supply at all. `file_size` needs per-file
# line counts no permissively-licensed tool in the pool reports, and
# `risk` and `gates` are configured policy with no external equivalent.
ANALYZER_DIMENSIONS: tuple[str, ...] = ("declarations",)


def declaration_concepts_missing(covered: set[str]) -> tuple[str, ...]:
    """Criteria the analyzers did not supply, in rubric order.

    The fallback this decides is correct and used to be silent, which P8
    forbids: the reader saw a declarations rate with nothing saying what
    produced it. It is not a rare path either. lizard reports cyclomatic
    complexity and declaration lines and no cognitive complexity, so a
    JavaScript repository with lizard installed and nothing else takes
    this branch on *every* run -- by construction, and an audit had to
    point out that the page justifying JavaScript support credited the
    analyzer pool for work the built-in scanner was doing.
    """
    return tuple(
        concept for concept, _warn, _fail in DECLARATION_CRITERIA
        if concept not in covered
    )


def _unit_languages(measurements: list[Measurement]) -> dict[str, str]:
    """Each unit's language, by the suffix of the file it was read from.

    Units whose suffix names no language this project knows are left out
    rather than pooled under one unknown bucket. The gate below asks
    whether a *language* is missing a criterion, and a question about a
    language cannot be asked of a file whose language was never
    established — pooling them would let `pmd`'s XML readings, which
    carry no declaration lines, fail the check for a Java repository
    that is otherwise completely measured.
    """
    languages: dict[str, str] = {}
    for measurement in measurements:
        path = measurement.path or measurement.unit
        suffix = PurePosixPath(path).suffix
        language = KNOWN_SOURCE_SUFFIXES.get(suffix)
        if language:
            languages[measurement.unit] = language
    return languages


def _concepts_by_language(
    per_unit: dict[str, dict[str, float]], unit_languages: dict[str, str]
) -> dict[str, set[str]]:
    """What the analyzers measured, gathered per language."""
    covered: dict[str, set[str]] = defaultdict(set)
    for unit, values in per_unit.items():
        language = unit_languages.get(unit)
        if language:
            covered[language].update(values)
    return dict(covered)


def _languages_missing_a_criterion(
    per_unit: dict[str, dict[str, float]], unit_languages: dict[str, str]
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Languages the analyzers did not measure on all three criteria.

    One incomplete language disqualifies the whole reading, because the
    value returned here replaces the built-in `declarations` pressure for
    the entire repository — there is no seam to hand back a blend. Making
    that seam is a larger change: the built-in path carries one aggregate
    `declaration_band_pressure`, not a per-language one, so a genuine
    per-language blend needs per-language aggregates plumbed through the
    summary. Recorded rather than attempted here, because the honest
    intermediate is to fall back for the repository when any language it
    would speak for is incomplete, which is strictly more correct than
    speaking for all of them on the strength of one.
    """
    return tuple(
        (language, missing)
        for language, concepts in sorted(
            _concepts_by_language(per_unit, unit_languages).items())
        if (missing := declaration_concepts_missing(concepts))
    )


def complete_from_built_ins(
    per_unit: dict[str, dict[str, float]],
    unit_locations: dict[str, tuple[str, int]],
    built_in: dict[tuple[str, int], dict[str, float]],
) -> dict[str, dict[str, float]]:
    """Fill criteria an analyzer did not measure from the built-in reading.

    **Per concept, not per dimension.** The rule above asks whether a
    language carries all three criteria; this is what lets a language
    answer yes when no single tier measures all three. `lizard` reports
    cyclomatic complexity and declaration lines for sixteen languages and
    cognitive complexity for none; the built-in scanners report all three
    for fourteen. Neither tier is complete alone, and the union of them,
    per declaration, is.

    Without this the analyzer tier can drive `declarations` for **Python
    and nothing else** — measured, not inferred: of the 112 corpus
    repositories, zero satisfied the criterion set without `complexipy`,
    which reads Python only. PMD is the sole other wired tool that speaks
    cognitive complexity, and it emits *violations above a threshold*
    rather than a reading per declaration, so it can never supply a rate
    over a population.

    The join is `(path, start_line)`, and it is exact rather than
    approximate: measured on this package, all 1,008 declarations lizard
    reports match a built-in declaration at the same start line — 100% of
    lizard's population, 92% of the built-in's, the difference being
    declarations lizard does not count as functions.

    Mixing tiers inside one unit is the point rather than a compromise.
    The comparability the criterion set protects is that every
    declaration was *eligible* to fail on all three, not that one
    instrument measured all three; ADR 006 already makes the analyzer
    primary for what it measures, and the bands both tiers are scored
    through come from the same thresholds.
    """
    completed: dict[str, dict[str, float]] = {}
    for unit, values in per_unit.items():
        missing = declaration_concepts_missing(set(values))
        location = unit_locations.get(unit)
        fallback = built_in.get(location) if location else None
        if not missing or not fallback:
            completed[unit] = values
            continue
        filled = dict(values)
        for concept in missing:
            if concept in fallback:
                filled[concept] = fallback[concept]
        completed[unit] = filled
    return completed


def built_in_readings(
    metrics: object, root: str = ""
) -> dict[tuple[str, int], dict[str, float]]:
    """The scanner's three criteria per declaration, keyed for the join.

    Lives beside the join rather than at the call site so both halves of
    it share one path vocabulary. They did not, once, and the merge
    shipped inert with the whole suite green.
    """
    return {
        (canonical_path(root, metric.path), metric.start_line): {
            "cyclomatic_complexity": float(metric.complexity),
            "declaration_lines": float(metric.lines),
            "cognitive_complexity": float(metric.cognitive),
        }
        for metric in metrics  # type: ignore[attr-defined]
    }


def canonical_path(root: str, path: str) -> str:
    """One spelling for a file, so two tiers can be joined on it.

    Three vocabularies meet at this join and no two agree: `lizard`
    reports `./src/x.py`, `complexipy` reports the absolute path, and the
    built-in scanner reports `src/x.py` relative to the scanned root.
    Keying the join on any of them as given matches nothing, which is not
    a hypothetical — it is how this merge shipped inert the first time,
    with the whole suite green, because every test built both sides from
    the same string.
    """
    text = path.replace("\\", "/")
    if root and text.startswith(root):
        text = text[len(root):]
    return posixpath.normpath(text).lstrip("./") or text


def unit_locations(
    measurements: list[Measurement], root: str = ""
) -> dict[str, tuple[str, int]]:
    """Where each unit starts, for the join above.

    A measurement with no line cannot be joined and is simply absent
    here: `complexipy` reports no start line, and needs none, because it
    supplies the one concept the built-in tier would have been asked for.
    """
    located: dict[str, tuple[str, int]] = {}
    for measurement in measurements:
        path = measurement.path or ""
        if path and measurement.line is not None:
            located[measurement.unit] = (
                canonical_path(root, path), int(measurement.line))
    return located


def _scored_units(
    per_unit: dict[str, dict[str, float]], unit_languages: dict[str, str]
) -> dict[str, dict[str, float]] | None:
    """The declarations the analyzer tier may score, or `None` for none.

    **The one place eligibility is decided.** The rule it enforces is a
    single sentence, and it is the sentence this bridge exists to keep
    true: *every declaration contributing to the analyzer reading was
    eligible to fail on all three criteria the built-in path fails on.*
    A unit is eligible when its own language was measured on cyclomatic
    complexity, declaration lines and cognitive complexity — not when
    some other language in the repository was.

    Returning the population rather than a verdict is the point. Four
    earlier fixes to this bridge each corrected a formula and left the
    eligibility question living somewhere else, and D137 was the fifth:
    the check took a union across the repository while the units it
    gated were scored one at a time, so a C repository holding one
    `setup.py` had its C declarations scored on two criteria of three.
    A caller cannot now score a set this function did not hand back, so
    the two cannot be scoped differently again.

    The verdict is all-or-nothing for the repository because the value
    the caller produces replaces the built-in `declarations` pressure for
    the whole of it; there is no seam to hand back a blend. Handing back
    only the eligible units would trade a wrong-criteria reading for a
    wrong-population one — a confident rate describing the 2% of a C
    codebase that happens to be Python. A genuine per-language blend
    needs per-language aggregates plumbed through the summary evidence,
    which the built-in path does not carry today.
    """
    incomplete = _languages_missing_a_criterion(per_unit, unit_languages)
    if incomplete:
        return None
    return per_unit
