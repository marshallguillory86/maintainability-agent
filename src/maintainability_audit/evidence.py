"""Typed evidence states and the one normalization boundary.

[ADR 001](../../docs/adr-001-evidence-and-verification.md); implementation
status is tracked in ``docs/decisions.md`` and deliberately not restated
here, because five copies of it went stale the first time.

``score_report`` normalizes at its entry, so every scoring layer below
consumes these types rather than raw dictionaries.

The problem it exists to solve: a missing dictionary key currently means
five different things (measured zero, could not measure, does not
apply, an older report, a malformed one), and the scorer decides which
one by reaching for ``get(name, 0)``. Six audit rounds fixed individual
fields; the states themselves were never made distinguishable. Here they
are three explicit types, and a value that was never established cannot
be confused with a value that was established as zero.

``Measured(0)`` means the scanner looked and found none. ``Unknown``
means it could not establish a value. ``NotApplicable`` means the
measurement has no meaningful population in this repository — a repo
where no file has three commits yet has no ownership concentration to
report, which is a different statement from "ownership is unknown".
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, fields
from typing import Any

# The report structure this module understands. Owned by
# ``report.build_report``, which stamps it. Deliberately not the
# baseline file's ``version``, which numbers a different artifact.
#
# **docs/report-contract.md is the compatibility policy** — what each
# version changed, why version 1 is not migrated, and which consumers
# that decision was checked against. It is not restated here: this
# module is a leaf that imports nothing first-party, so its 500-line
# budget is permanent, and a paragraph duplicated from a page it already
# links is the cheapest thing in it to lose.
REPORT_SCHEMA_VERSION = 3

# What a run examined. ``full`` is the whole tree; anything else is a
# subset and cannot carry a whole-repository grade (ADR 005).
SCOPE_FULL = "full"
SCOPE_CHANGED = "changed-only"
SCOPE_SUBSET = "subset"
KNOWN_SCOPES = frozenset({SCOPE_FULL, SCOPE_CHANGED, SCOPE_SUBSET})

SCHEMA_VERSION_KEY = "schema_version"


class EvidenceValidationError(ValueError):
    """A report cannot be normalized into the typed evidence model."""


class UnsupportedReportSchema(EvidenceValidationError):
    """The report's schema version is absent or not supported."""


@dataclass(frozen=True)
class Measured:
    """A value the scanner established. ``Measured(0)`` is a finding."""

    value: float | int | bool
    provenance: str


@dataclass(frozen=True)
class Unknown:
    """No value could be established, and why."""

    reason: str
    provenance: str


@dataclass(frozen=True)
class NotApplicable:
    """The measurement has no population here, and why."""

    reason: str
    provenance: str


EvidenceState = Measured | Unknown | NotApplicable


@dataclass(frozen=True)
class SummaryEvidence:
    """Every scoring input currently drawn from ``report["summary"]``.

    The field list is the contract: ``_pressures`` and ``_aspects`` read
    exactly these keys today (populations, finding counts, the
    production-only split, test presence, and the documentation flags).
    """

    files_scanned: EvidenceState
    declarations_scanned: EvidenceState
    file_warnings: EvidenceState
    file_failures: EvidenceState
    function_warnings: EvidenceState
    function_failures: EvidenceState
    duplicate_blocks: EvidenceState
    risk_findings: EvidenceState
    hard_gate_failures: EvidenceState
    production_files_scanned: EvidenceState
    production_declarations_scanned: EvidenceState
    production_file_warnings: EvidenceState
    production_file_failures: EvidenceState
    production_function_warnings: EvidenceState
    production_function_failures: EvidenceState
    production_hard_gate_failures: EvidenceState
    test_file_count: EvidenceState
    dead_code_count: EvidenceState
    near_duplicate_count: EvidenceState
    idiom_concern_count: EvidenceState
    # The share of the repository the score describes. Typed like every
    # other input so "we do not know what we failed to read" cannot be
    # silently read as "we read everything".
    unread_source_files: EvidenceState
    read_source_files: EvidenceState
    # Files opened for length, duplication and risk that no declaration
    # parser understands. Typed like the rest so "we do not know" cannot
    # read as "there were none".
    undetected_declaration_files: EvidenceState
    # Band-matrix pressures (ADR 008, 3.2): per-unit measurements mapped
    # through `_bands` at scan time, because the counts above cannot tell
    # complexity 16 from 45. Unknown on reports written before the wiring;
    # `_pressures` falls back to the count rate there, stated at the site.
    declaration_band_pressure: EvidenceState
    production_declaration_band_pressure: EvidenceState
    file_band_pressure: EvidenceState
    production_file_band_pressure: EvidenceState
    has_readme: EvidenceState
    has_changelog: EvidenceState
    has_docs_dir: EvidenceState


@dataclass(frozen=True)
class HistoryEvidence:
    """Every scoring input currently drawn from ``report["history"]``.

    Always present as a structure, even when the report carries no
    history at all: absence is recorded as ``Unknown`` on each field
    rather than as a missing object, so a caller cannot reach a history
    number without passing through a state that says whether it exists.
    """

    files_changed: EvidenceState
    qualifying_hotspots: EvidenceState
    code_coupling_pairs: EvidenceState
    multi_commit_files: EvidenceState
    single_author_files: EvidenceState


@dataclass(frozen=True)
class NormalizedEvidence:
    """The typed model scoring will eventually consume."""

    schema_version: int
    summary: SummaryEvidence
    history: HistoryEvidence
    # What the scan looked at. The scale is calibrated over whole
    # repositories, so a diff is not a small repository -- it is a
    # different kind of thing, and scoring it on this scale is a
    # category error rather than a precision problem. Carried through the
    # boundary so the scorer never reads the raw report to learn it.
    scope: str = SCOPE_FULL


def walk_evidence(node: Any, prefix: str = "") -> Iterator[tuple[str, EvidenceState]]:
    """Every evidence state in the model, with its dotted path.

    Recursive over the dataclasses rather than over a hand-maintained
    list of names, so a field added to the model later is walked the day
    it is added. Property tests use this to vary states without a
    fixture author having to remember to extend anything.
    """
    if isinstance(node, (Measured, Unknown, NotApplicable)):
        yield prefix, node
        return
    if not hasattr(type(node), "__dataclass_fields__"):
        return
    for field in fields(node):
        child = getattr(node, field.name)
        yield from walk_evidence(child, f"{prefix}.{field.name}" if prefix else field.name)


# Fields that are true/false, not quantities. Everything else in the
# model is a count of things the scanner saw.
FLAG_FIELDS = frozenset({"has_readme", "has_changelog", "has_docs_dir"})

# Band-matrix pressures: fractional by nature (mean band pressure over a
# population), unlike every count around them.
PRESSURE_FIELDS = frozenset({
    "declaration_band_pressure", "production_declaration_band_pressure",
    "file_band_pressure", "production_file_band_pressure",
})

# Relationships the *producer* guarantees, enumerated from where it
# guarantees them rather than from whichever violation an audit
# happened to demonstrate. ``report.report_summary`` gives every file
# and every declaration exactly one status, so warnings and failures
# partition their population; ``history.history_section`` draws
# hotspots and settled files from the churn set.
#
# Two audits closed "the demonstrated examples" here and called the
# class closed. This table *is* the class: every relation is checked,
# and ``test_every_declared_invariant_is_enforced`` iterates the table
# so a relation added below is exercised the day it is added.
#
# Deliberately absent: ``code_coupling_pairs`` is a count of *pairs*
# and can legitimately exceed ``files_changed``.

# part <= whole
SUMMARY_SUBSETS: tuple[tuple[str, str], ...] = (
    ("production_files_scanned", "files_scanned"),
    ("production_declarations_scanned", "declarations_scanned"),
    ("production_file_failures", "file_failures"),
    ("production_file_warnings", "file_warnings"),
    ("production_function_failures", "function_failures"),
    ("production_function_warnings", "function_warnings"),
    ("production_hard_gate_failures", "hard_gate_failures"),
    ("test_file_count", "files_scanned"),
    # Each status count individually, not only as a sum. The sum
    # relation below skips when either sibling is Unknown, so an audit
    # found `files_scanned=5, file_failures=6` accepted whenever
    # `file_warnings` was absent: a known count cannot exceed a known
    # population regardless of what is unknown beside it. The sum is an
    # additional constraint, never a replacement for these.
    ("file_failures", "files_scanned"),
    ("file_warnings", "files_scanned"),
    ("function_failures", "declarations_scanned"),
    ("function_warnings", "declarations_scanned"),
    ("production_file_failures", "production_files_scanned"),
    ("production_file_warnings", "production_files_scanned"),
    ("production_function_failures", "production_declarations_scanned"),
    ("production_function_warnings", "production_declarations_scanned"),
    ("dead_code_count", "declarations_scanned"),
    ("near_duplicate_count", "declarations_scanned"),
)

# sum(parts) <= whole — one status per member of the population
SUMMARY_SUMS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("file_failures", "file_warnings"), "files_scanned"),
    (("function_failures", "function_warnings"), "declarations_scanned"),
    (("production_file_failures", "production_file_warnings"), "production_files_scanned"),
    (
        ("production_function_failures", "production_function_warnings"),
        "production_declarations_scanned",
    ),
)

HISTORY_SUBSETS: tuple[tuple[str, str], ...] = (
    ("single_author_files", "multi_commit_files"),
    ("qualifying_hotspots", "files_changed"),
    ("multi_commit_files", "files_changed"),
)

HISTORY_SUMS: tuple[tuple[tuple[str, ...], str], ...] = ()


NO_HISTORY = "report carries no history block: shallow clone, or not a git repository"
HISTORY_FIELD_ABSENT = "history block present but this count was not recorded"
SUMMARY_FIELD_ABSENT = "summary does not carry this count"
NO_SETTLED_FILES = "no file has three or more commits, so ownership concentration has no population"
# The three ways a window produces no churn, told apart because telling
# the other two that the window was empty is false (D66). Inline rather
# than in a module of their own: `evidence` imports nothing first-party.
_NO_POP = ", so every history rate has no population to divide by"
EMPTY_WINDOW = "no commit falls inside the history window" + _NO_POP
MERGES_ONLY = ("every commit in the history window is a merge, and a merge's "
               "numstat re-reports churn already counted on the branch" + _NO_POP)
NO_SCANNED_FILES_CHANGED = ("commits landed inside the history window but "
                            "touched no file this audit scans" + _NO_POP)
