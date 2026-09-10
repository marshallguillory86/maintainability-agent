"""Reading a report dictionary into the evidence vocabulary.

Split from `evidence` when that module reached exactly 500 lines — this
project's own `max_file_lines`, where the next line added fails the
gate.

The seam is the one the boundary already implies. `evidence` is the
**vocabulary**: `Measured`, `Unknown`, `NotApplicable`, the typed
summary and history shapes, and the reason strings that explain an
absence. It is the one module in this package that imports nothing
internal, which is what makes it a boundary a consumer can depend on
without taking a dependency on the scanner.

This module is the **reader**: it validates a report dictionary and
produces that vocabulary from it. Validation has opinions — which
relations must hold, which schema versions are supported, what an empty
history window means — and opinions are exactly what a boundary should
not carry.

The dependency runs one way, and it has to. `evidence` cannot import
this module without ceasing to be a boundary, which is why the public
name `normalize_report_evidence` moved here rather than being
re-exported from its old home: a re-export would have been an import,
and the import is the thing the boundary forbids.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields
from math import isinf, isnan
from typing import Any

from .evidence import (
    EMPTY_WINDOW,
    FLAG_FIELDS,
    HISTORY_FIELD_ABSENT,
    HISTORY_SUBSETS,
    HISTORY_SUMS,
    KNOWN_SCOPES,
    MERGES_ONLY,
    NO_HISTORY,
    NO_SCANNED_FILES_CHANGED,
    NO_SETTLED_FILES,
    PRESSURE_FIELDS,
    REPORT_SCHEMA_VERSION,
    SCHEMA_VERSION_KEY,
    SCOPE_FULL,
    SUMMARY_FIELD_ABSENT,
    SUMMARY_SUBSETS,
    SUMMARY_SUMS,
    EvidenceState,
    EvidenceValidationError,
    HistoryEvidence,
    Measured,
    NormalizedEvidence,
    NotApplicable,
    SummaryEvidence,
    Unknown,
    UnsupportedReportSchema,
)


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
    if name in PRESSURE_FIELDS:
        # Band pressures are means over [0, 1] per unit, not counts. They
        # get their own bound instead of an exemption from all bounds: a
        # pressure of 7 is as impossible as a count of 3.5.
        if value > 1:
            raise EvidenceValidationError(
                f"{provenance}: band pressures lie in [0, 1], got {value!r}"
            )
        return float(value)
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
        # Narrowed by construction rather than by `all(isinstance(...))`,
        # which tells a reader — and a type checker — nothing about the
        # list it just tested. A relation is only checkable when every
        # participant was actually measured.
        whole = states[whole_name]
        parts = [states[name] for name in part_names]
        measured = [part for part in parts if isinstance(part, Measured)]
        if not isinstance(whole, Measured) or len(measured) != len(parts):
            continue
        total = sum(part.value for part in measured)
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
            f"version {REPORT_SCHEMA_VERSION} only. Version 1 carried the compatibility "
            "score fields removed in ADR 001 stage 8 and is not migrated, because no "
            "consumer rescores a persisted report (docs/report-contract.md)"
        )
    return version


def _empty_window_reason(section: Mapping[str, Any]) -> str:
    """Which of the three empty windows this is (D66, D74).

    Neither field is a `HistoryEvidence` member, so nothing upstream
    validates them and an incoherent pair earns the least specific
    answer -- a confidently wrong reason is the defect D66 removes.
    `read` is the non-merge subset of `seen`, so it cannot exceed it,
    and `bool` is an `int` (D74).
    """
    seen = section.get("commits_in_window")
    read = section.get("commits_considered")
    coherent = (
        isinstance(seen, int) and isinstance(read, int)
        and not isinstance(seen, bool) and not isinstance(read, bool)
        and 0 <= read <= seen
    )
    if not coherent or not seen:
        return EMPTY_WINDOW
    return MERGES_ONLY if read == 0 else NO_SCANNED_FILES_CHANGED


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
    # An empty window is not a quiet repository (D56). NotApplicable,
    # not Unknown: the window *was* read, and "nothing to divide by" is
    # not "could not look".
    changed = states["files_changed"]
    if isinstance(changed, Measured) and not changed.value:
        reason = _empty_window_reason(section)
        for name in ("qualifying_hotspots", "code_coupling_pairs",
                     "multi_commit_files", "single_author_files"):
            if isinstance(states[name], Measured):
                states[name] = NotApplicable(reason, f"history.{name}")

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
        scope=_scope_of(report),
    )


def _scope_of(report: dict[str, Any]) -> str:
    """What the run examined, validated at the boundary like everything else.

    An unrecognized scope is rejected rather than defaulted to ``full``:
    defaulting would silently grant a whole-repository grade to a scan
    whose extent nobody could describe, which is the failure this field
    exists to prevent.
    """
    mode = report.get("mode", SCOPE_FULL)
    if mode not in KNOWN_SCOPES:
        raise EvidenceValidationError(
            f"unknown scan scope {mode!r}; expected one of {sorted(KNOWN_SCOPES)}"
        )
    return mode
