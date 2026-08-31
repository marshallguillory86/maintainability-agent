"""Declared risk and effort per finding class — ADR 007 §3.

Data only. The matrix that consumes these lives in `_work_order`.
Published in `standard.md` so a team that disagrees has a number to
point at.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassWeight:
    """One finding class's declared cost of keeping and cost of fixing."""

    risk: int
    effort: int
    rationale: str
    # How a reader proves the item is done. A format string over the
    # item's own fields, so the command names the actual file.
    verification: str
    # The summary counter this class contributes to, used to recompute
    # the score with the finding removed.
    counter: str
    population: str


# Risk and effort per finding class, 1-5 each. Published in standard.md.
CLASS_RISK_EFFORT: dict[str, ClassWeight] = {
    "oversized-declaration": ClassWeight(
        risk=4, effort=2,
        rationale=(
            "a long, branching function is where defects concentrate and where "
            "every future change has to be understood first; extracting one is "
            "bounded, local work"
        ),
        verification="python -m maintainability_audit --root . --format json",
        counter="function_failures",
        population="declarations_scanned",
    ),
    "oversized-file": ClassWeight(
        risk=3, effort=3,
        rationale=(
            "a file past the limit hides its own structure, but splitting one "
            "touches every importer and is a change worth reviewing on its own"
        ),
        verification="python -m maintainability_audit --root . --format json",
        counter="file_failures",
        population="files_scanned",
    ),
    "duplicate-block": ClassWeight(
        risk=4, effort=4,
        rationale=(
            "duplicated logic means a fix applied in one place and missed in "
            "the others; deduplicating across a codebase is a design change, "
            "not a tidy-up"
        ),
        verification="python -m maintainability_audit --root . --format json",
        counter="duplicate_blocks",
        population="files_scanned",
    ),
    "near-duplicate": ClassWeight(
        risk=3, effort=4,
        rationale=(
            "near-copies drift apart silently, which is worse than exact "
            "duplication; reconciling them requires deciding which behaviour "
            "was intended"
        ),
        verification="python -m maintainability_audit --root . --format json",
        counter="near_duplicate_count",
        population="declarations_scanned",
    ),
    "dead-code": ClassWeight(
        risk=2, effort=1,
        rationale=(
            "unreachable code costs reading time and misleads a search, but "
            "deleting it is the cheapest change there is"
        ),
        verification="python -m maintainability_audit --root . --format json",
        counter="dead_code_count",
        population="declarations_scanned",
    ),
    "unpaired-hotspot": ClassWeight(
        risk=4, effort=2,
        rationale=(
            "an oversized production unit with no paired test is where "
            "changes land unguarded; adding a characterization test is "
            "bounded, local work"
        ),
        verification="python -m maintainability_audit --root . --format json",
        counter="production_function_failures",
        population="production_declarations_scanned",
    ),
    "risk-pattern": ClassWeight(
        risk=5, effort=1,
        rationale=(
            "a configured risk pattern is a rule this project chose to enforce "
            "on itself, and each hit is a single located line"
        ),
        verification="python -m maintainability_audit --root . --format json",
        counter="risk_findings",
        population="files_scanned",
    ),
    "competing-libraries": ClassWeight(
        risk=2, effort=4,
        rationale=(
            "two libraries doing one job is a decision nobody made; converging "
            "on one is a migration across every call site"
        ),
        verification="python -m maintainability_audit --root . --format json",
        counter="idiom_concern_count",
        population="files_scanned",
    ),
}
