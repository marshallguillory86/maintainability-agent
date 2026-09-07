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
