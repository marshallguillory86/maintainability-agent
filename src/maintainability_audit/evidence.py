"""Typed evidence states and the one normalization boundary.

Stage 2-3 of [ADR 001](../../docs/adr-001-evidence-and-verification.md).
**Scoring does not consume this yet** — the scorer still reads raw
dictionaries, and this module runs beside it. What exists here is the
model and the boundary, not the migration.

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
from math import isnan
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
    history_present: bool


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


def _validated_number(value: Any, provenance: str) -> float | int | bool:
    if isinstance(value, bool):
        return value
    if not isinstance(value, (int, float)) or isnan(value):  # NaN is not a measurement
        raise EvidenceValidationError(f"{provenance}: expected a number, got {value!r}")
    if value < 0:
        raise EvidenceValidationError(f"{provenance}: counts cannot be negative, got {value!r}")
    return value


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
    return Measured(_validated_number(value, provenance), provenance)


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


def _normalize_history(report: dict[str, Any]) -> tuple[HistoryEvidence, bool]:
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
        return HistoryEvidence(**absent), False
    section = _require_mapping(raw, "history")
    states = _states_for(HistoryEvidence, section, "history", HISTORY_FIELD_ABSENT)
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
    return HistoryEvidence(**states), True


def normalize_report_evidence(report: dict[str, Any]) -> NormalizedEvidence:
    """Validate a report and lift its scoring inputs into typed states.

    The single boundary ADR 001 calls for: every raw-dictionary
    accommodation belongs here, so that scoring — once migrated — never
    sees a bare ``dict`` again. Raises :class:`EvidenceValidationError`
    (or :class:`UnsupportedReportSchema`) rather than returning a
    partially trustworthy model.

    Not yet wired into scoring. ``build_report`` stamps the schema
    version this validates; the scorer still reads the raw dictionaries
    beside it, and moving it across is the next ADR stage.
    """
    _require_mapping(report, "report")
    version = _check_schema_version(report)
    summary = _require_mapping(report.get("summary", {}), "summary") if "summary" in report else None
    if summary is None:
        raise EvidenceValidationError("report has no summary: nothing to score")
    history, present = _normalize_history(report)
    return NormalizedEvidence(
        schema_version=version,
        summary=SummaryEvidence(**_states_for(SummaryEvidence, summary, "summary", SUMMARY_FIELD_ABSENT)),
        history=history,
        history_present=present,
    )
