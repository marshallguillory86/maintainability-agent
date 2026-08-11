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
from math import isinf, isnan
from typing import Any

# The report structure this module understands. Owned by
# ``report.build_report``, which stamps it; see docs/report-contract.md
# for the compatibility policy. Deliberately not the baseline file's
# ``version``, which numbers a different artifact.
REPORT_SCHEMA_VERSION = 1

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


def _validated_value(name: str, value: Any, provenance: str) -> float | int | bool:
    """Reject values a scanner could not have produced.

    An audit found the boundary accepting ``files_scanned=True``,
    ``files_scanned=1.5`` and ``has_readme=7`` — all normalized and
    scored without complaint — because one generic numeric check served
    every field. A validation boundary that accepts impossible evidence
    is a boundary in name only, so counts and flags are now checked as
    what they are.
    """
    if name in FLAG_FIELDS:
        if not isinstance(value, bool):
            raise EvidenceValidationError(f"{provenance}: expected true or false, got {value!r}")
        return value
    if isinstance(value, bool):
        raise EvidenceValidationError(f"{provenance}: expected a count, got the boolean {value!r}")
    if not isinstance(value, (int, float)) or isnan(value) or isinf(value):
        raise EvidenceValidationError(f"{provenance}: expected a number, got {value!r}")
    if value < 0:
        raise EvidenceValidationError(f"{provenance}: counts cannot be negative, got {value!r}")
    if float(value) != int(value):
        raise EvidenceValidationError(f"{provenance}: counts are whole, got {value!r}")
    return value


def _check_relations(
    states: dict[str, EvidenceState],
    subsets: tuple[tuple[str, str], ...],
    sums: tuple[tuple[tuple[str, ...], str], ...],
    prefix: str,
) -> None:
    """Reject counts that contradict what the producer guarantees.

    Cross-field validation, which the boundary originally had none of
    and then had only for the pairs an audit named. A subset larger than
    its set, or statuses summing past their population, describes a
    repository the scanner could not have produced.

    Only ``Measured`` values participate: an unknown constrains nothing,
    and must not be treated as zero to manufacture a violation.
    """
    for part_name, whole_name in subsets:
        part, whole = states[part_name], states[whole_name]
        if isinstance(part, Measured) and isinstance(whole, Measured) and part.value > whole.value:
            raise EvidenceValidationError(
                f"{prefix}.{part_name} ({part.value}) exceeds "
                f"{prefix}.{whole_name} ({whole.value}): a subset cannot be larger than its set"
            )
    for part_names, whole_name in sums:
        parts = [states[name] for name in part_names]
        whole = states[whole_name]
        if not isinstance(whole, Measured) or not all(isinstance(part, Measured) for part in parts):
            continue
        total = sum(part.value for part in parts)
        if total > whole.value:
            raise EvidenceValidationError(
                f"{prefix}: {' + '.join(part_names)} ({total}) exceeds "
                f"{prefix}.{whole_name} ({whole.value}): each member of a population has one status"
            )


def _state(source: dict[str, Any], name: str, prefix: str, missing_reason: str) -> EvidenceState:
    """One field's state: present and valid, or Unknown with a reason.

    The whole point of the boundary. ``name not in source`` is the only
    place in the system allowed to decide what an absent key means, and
    it decides ``Unknown`` — never zero.
    """
    provenance = f"{prefix}.{name}"
    if name not in source:
        return Unknown(missing_reason, provenance)
    value = source[name]
    if value is None:
        return Unknown(f"{provenance} is null in the report", provenance)
    return Measured(_validated_value(name, value, provenance), provenance)


def _states_for(cls: type, source: dict[str, Any], prefix: str, missing_reason: str) -> dict[str, EvidenceState]:
    return {field.name: _state(source, field.name, prefix, missing_reason) for field in fields(cls)}


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceValidationError(f"{name}: expected an object, got {type(value).__name__}")
    return value


def _check_schema_version(report: dict[str, Any]) -> int:
    version = report.get(SCHEMA_VERSION_KEY)
    if version is None:
        raise UnsupportedReportSchema(
            f"report carries no {SCHEMA_VERSION_KEY}; unversioned reports predate the typed "
            "evidence model and are not rescored by any consumer (docs/report-contract.md)"
        )
    if version != REPORT_SCHEMA_VERSION:
        raise UnsupportedReportSchema(
            f"unsupported {SCHEMA_VERSION_KEY} {version!r}; this build normalizes "
            f"version {REPORT_SCHEMA_VERSION} only"
        )
    return version


NO_HISTORY = "report carries no history block: shallow clone, or not a git repository"
HISTORY_FIELD_ABSENT = "history block present but this count was not recorded"
SUMMARY_FIELD_ABSENT = "summary does not carry this count"
NO_SETTLED_FILES = "no file has three or more commits, so ownership concentration has no population"


def _normalize_history(report: dict[str, Any]) -> HistoryEvidence:
    """History evidence, distinguishing 'no history' from 'not recorded'.

    Two audit findings live in this function's contract. A shallow clone
    must not read as a quiet repository, and a history block missing one
    nested count must neither become a measured zero nor raise
    ``KeyError`` on direct indexing — both of which the raw-dictionary
    scorer did at different times.
    """
    raw = report.get("history")
    if raw is None:
        absent = {field.name: Unknown(NO_HISTORY, f"history.{field.name}") for field in fields(HistoryEvidence)}
        return HistoryEvidence(**absent)
    section = _require_mapping(raw, "history")
    states = _states_for(HistoryEvidence, section, "history", HISTORY_FIELD_ABSENT)
    _check_relations(states, HISTORY_SUBSETS, HISTORY_SUMS, "history")
    settled = states["multi_commit_files"]
    owners = states["single_author_files"]
    if isinstance(settled, Measured) and not settled.value and isinstance(owners, Measured):
        # Looked, and there is nothing to measure — distinct from
        # "could not look", and the existing scorer already declines to
        # penalize it. NotApplicable records which of the two it is.
        #
        # Only when the count was actually recorded. An absent field
        # stays Unknown even though the population is empty: deleting
        # evidence must never resolve it into a *better-defined* state
        # than leaving it in, or concealment buys clarity.
        states["single_author_files"] = NotApplicable(NO_SETTLED_FILES, "history.single_author_files")
    return HistoryEvidence(**states)


def normalize_report_evidence(report: dict[str, Any]) -> NormalizedEvidence:
    """Validate a report and lift its scoring inputs into typed states.

    The single boundary ADR 001 calls for: every raw-dictionary
    accommodation belongs here, so that scoring — once migrated — never
    sees a bare ``dict`` again. Raises :class:`EvidenceValidationError`
    (or :class:`UnsupportedReportSchema`) rather than returning a
    partially trustworthy model.

    ``build_report`` stamps the schema version this validates, and
    ``score_report`` calls this before touching anything.
    """
    _require_mapping(report, "report")
    version = _check_schema_version(report)
    summary = _require_mapping(report.get("summary", {}), "summary") if "summary" in report else None
    if summary is None:
        raise EvidenceValidationError("report has no summary: nothing to score")
    history = _normalize_history(report)
    summary_states = _states_for(SummaryEvidence, summary, "summary", SUMMARY_FIELD_ABSENT)
    _check_relations(summary_states, SUMMARY_SUBSETS, SUMMARY_SUMS, "summary")
    return NormalizedEvidence(
        schema_version=version,
        summary=SummaryEvidence(**summary_states),
        history=history,
    )
