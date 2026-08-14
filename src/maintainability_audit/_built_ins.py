"""The built-in detectors, recorded as the source tier they are — ADR 006 §2.

They were demoted when the external analyzer pool arrived, not deleted:
they are the only source when nothing is installed, and four of them
reach concepts no adapter in the pool emits at all. What they were not,
until this module existed, was *visible* — the coverage section listed
the analyzers and silently omitted half of what examined the code, which
is the same reporting defect the section was written to prevent.

Everything here is about placing them in the record honestly: what each
one covers, which external tools overlap it, and how many units it
actually examined.
"""
from __future__ import annotations

from typing import Any

# What the built-in detectors measure, and where each stands once the
# external analyzers arrive. Demoted to a fallback tier rather than
# deleted (ADR 006 §2): every measurement they produce is single-source
# and carries the weaker evidence strength that implies, but "weaker" is
# not "absent", and four of these have no adapter emitting their concept
# at all — `test_no_built_in_claims_to_be_unique_when_an_adapter_exists`
# holds that claim to the registry so it cannot rot when adapters land.
BUILT_IN_SOURCES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("file-size", ("file_lines",),
     "per-file line counts; no adapter emits file_lines"),
    ("declaration-size", ("declaration_lines", "cyclomatic_complexity",
                          "cognitive_complexity"),
     "lizard and complexipy cover these; the only source when neither runs"),
    ("duplicate-blocks", ("duplication",),
     "jscpd covers this; the only source when Node is unavailable"),
    ("near-duplicates", ("duplication",),
     "token-shingle near-matches, which jscpd's exact-block scan misses"),
    ("dead-code", ("dead-code",), "vulture, ruff and eslint cover this"),
    ("risk-patterns", ("risk",),
     "regex policy from this repository's own config; nothing external "
     "can hold a project-specific rule"),
    ("competing-libraries", ("idioms",),
     "two libraries doing one job; no adapter emits idioms"),
    ("history", ("churn", "coupling", "ownership"),
     "git history; no adapter emits churn, coupling or ownership"),
)


# Where each built-in row's numbers come from in the assembled report:
# slug -> (population key, finding keys). The population is what the
# detector examined; the findings are what it reported. Both are read
# from the summary the scorer itself consumes, so the coverage table
# cannot drift from the numbers the score was computed on.
BUILT_IN_COUNTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "file-size": ("files_scanned", ("file_failures", "file_warnings")),
    "declaration-size": ("declarations_scanned",
                         ("function_failures", "function_warnings")),
    "duplicate-blocks": ("files_scanned", ("duplicate_blocks",)),
    "near-duplicates": ("declarations_scanned", ("near_duplicate_count",)),
    "dead-code": ("declarations_scanned", ("dead_code_count",)),
    "risk-patterns": ("files_scanned", ("risk_findings",)),
    "competing-libraries": ("files_scanned", ("idiom_concern_count",)),
}


def _count_one_built_in(
    entry: dict[str, Any], summary: dict[str, Any], history: dict[str, Any] | None
) -> str | None:
    """One built-in row's population and findings.

    Returns the outcome the row now belongs under, or ``None`` to leave
    it where it is. The caller has to move it: the document groups rows
    *by* outcome, so writing the field without regrouping changes nothing
    a reader sees.
    """
    if entry["tool"] == "history":
        # `history_section` returns None on a shallow clone. "No history
        # available" and "no churn" are opposite findings, so say which.
        if not history:
            entry["outcome"] = "no-history"
            entry["detail"] = (
                "no git history in this tree; churn, coupling and ownership "
                "are unmeasured rather than absent"
            )
            return "no-history"
        # Population is the files that changed in the window, not every
        # file in the tree: a file with no commits is outside what churn
        # can speak to at all.
        entry["measurements"] = int(history.get("files_changed", 0))
        entry["findings"] = (
            int(history.get("qualifying_hotspots", 0))
            + int(history.get("code_coupling_pairs", 0))
        )
        return None
    population, finding_keys = BUILT_IN_COUNTS[entry["tool"]]
    entry["measurements"] = int(summary.get(population, 0))
    entry["findings"] = sum(int(summary.get(key, 0)) for key in finding_keys)
    return None


def record_built_in_counts(coverage: dict[str, Any], report: dict[str, Any]) -> None:
    """Fill in what each built-in detector examined and reported.

    Called after assembly because that is the first point where both the
    counts and the history section exist. Until this ran, every built-in
    row displayed `0 measurements, 0 findings` — the absence-as-value
    defect showing up in the very table written to prevent it.

    Mutates `coverage` in place; it is the document that ships.
    """
    summary = report.get("summary") or {}
    history = report.get("history")
    grouped = coverage.get("by_outcome", {})
    moves: list[tuple[str, str, dict[str, Any]]] = []
    for outcome, entries in grouped.items():
        for entry in entries:
            if entry.get("tier") != "built-in":
                continue
            moved_to = _count_one_built_in(entry, summary, history)
            if moved_to and moved_to != outcome:
                moves.append((outcome, moved_to, entry))

    # Applied after the sweep rather than during it, because mutating the
    # groups being iterated is how the next reader of this function
    # introduces a silent skip.
    for source, destination, entry in moves:
        grouped[source].remove(entry)
        grouped.setdefault(destination, []).append(entry)
    for outcome in [name for name, entries in grouped.items() if not entries]:
        del grouped[outcome]
