"""Repeated-block detection and configurable risk-pattern matching.

Extracted from ``metrics.py`` (2026-08-06). Both scanners here re-read
whole files and answer corpus-level questions — "does this block appear
elsewhere", "does any line match a configured pattern" — as opposed to
the per-file measurements ``metrics`` takes.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any

from ._metrics_types import RiskFinding
from .metrics import read_lines  # noqa: F401  (re-exported for callers)
from .source import SourceIndex, index_or_new


def normalize_for_dup(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


_TRIVIAL_IDENT_RE = re.compile(r"^[A-Za-z_][\w]*,?$")
_TRIVIAL_KWARG_RE = re.compile(r"^[A-Za-z_][\w]*\s*=\s*[A-Za-z_][\w.]*,?$")
_TRIVIAL_PUNCT_RE = re.compile(r"^[\s()\[\]{},;:]+$")


def _is_trivial_dup_line(line: str) -> bool:
    """Return True for low-information lines that should not anchor a
    duplicate-block match.

    Bare-identifier lines such as ``name,`` show up identically in
    SQL column lists and in function keyword-argument signatures. The
    shared ordering is often the architectural contract — flagging it
    as a duplicate creates noise and pressures developers to obscure
    the contract. Pure punctuation (closing brackets/parens) is
    similarly information-free.
    """
    if not line:
        return True
    if _TRIVIAL_PUNCT_RE.match(line):
        return True
    if _TRIVIAL_IDENT_RE.match(line):
        return True
    return bool(_TRIVIAL_KWARG_RE.match(line))


def duplicate_blocks(
    root: Path, files: list[Path], block_size: int, index: SourceIndex | None = None
) -> list[dict[str, Any]]:
    source = index_or_new(index)
    seen: dict[tuple[str, ...], list[tuple[str, int]]] = {}
    for path in files:
        lines = [normalize_for_dup(line) for line in source.lines(path)]
        # Each useful line keeps its original 1-based source line number.
        # The index into this filtered list is not a source line: reporting
        # `idx + 1` pointed a reader at the Nth non-comment line, not line N
        # of the file, so every duplicate location was off by however many
        # comments and blanks preceded it (Grok e88b429 audit).
        useful = [
            (number, line)
            for number, line in enumerate(lines, start=1)
            if line and not line.startswith(("//", "#", "/*", "*", '"', "'"))
        ]
        rel = str(path.relative_to(root))
        for idx in range(0, max(0, len(useful) - block_size + 1)):
            block = tuple(line for _, line in useful[idx : idx + block_size])
            if len(set(block)) <= 1:
                continue
            # Skip blocks made entirely of low-information lines (bare
            # identifiers, kwarg passthroughs, pure punctuation). See
            # ``_is_trivial_dup_line`` docstring for the rationale.
            if all(_is_trivial_dup_line(item) for item in block):
                continue
            seen.setdefault(block, []).append((rel, useful[idx][0]))

    occurrences = [
        (block, sorted(set(locs)))
        for block, locs in seen.items()
        if len(set(locs)) > 1
    ]
    return _clone_groups(occurrences, block_size)


def _clone_groups(
    occurrences: list[tuple[tuple[str, ...], list[tuple[str, int]]]], block_size: int,
) -> list[dict[str, Any]]:
    """Overlapping windows of one clone collapse to a single group.

    A duplicated 200-line block appears as ~200 near-identical windows,
    each a distinct fingerprint sharing the same files at consecutive
    lines. Reported one row per window it was 861 line-items of one clone
    (bighound field test, plan-81dc6870 Class 4); reported one row per
    clone it is a single finding carrying the occurrence count and the
    span. Two windows join the same group when they share a file at lines
    within ``block_size`` — overlapping or adjacent — so genuinely
    separate clones stay separate.
    """
    parent = list(range(len(occurrences)))

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    by_file: dict[str, list[tuple[int, int]]] = {}
    for index, (_block, locs) in enumerate(occurrences):
        for rel, line in locs:
            by_file.setdefault(rel, []).append((line, index))
    for entries in by_file.values():
        entries.sort()
        for (line_a, node_a), (line_b, node_b) in zip(entries, entries[1:], strict=False):
            if line_b - line_a <= block_size:
                parent[find(node_a)] = find(node_b)

    members: dict[int, list[int]] = {}
    for index in range(len(occurrences)):
        members.setdefault(find(index), []).append(index)
    return sorted(
        (_group_finding(ids, occurrences, block_size) for ids in members.values()),
        key=lambda item: (item["count"], item["lines"]), reverse=True,
    )


def _group_finding(
    member_ids: list[int],
    occurrences: list[tuple[tuple[str, ...], list[tuple[str, int]]]],
    block_size: int,
) -> dict[str, Any]:
    """One clone group's row: how many places it repeats, how large it is,
    and a representative start in each file it touches."""
    starts: dict[str, int] = {}
    ends: dict[str, int] = {}
    fan_out = 0
    for member in member_ids:
        _block, locs = occurrences[member]
        fan_out = max(fan_out, len(locs))
        for rel, line in locs:
            starts[rel] = min(starts.get(rel, line), line)
            ends[rel] = max(ends.get(rel, line), line)
    span = max(ends[rel] - starts[rel] for rel in starts) + block_size
    return {
        "locations": sorted(f"{rel}:{starts[rel]}" for rel in starts)[:10],
        "count": fan_out,
        "lines": span,
        "sample": list(occurrences[member_ids[0]][0]),
    }


#: Two probes, short then longer, and the ordering is what bounds the
#: cost. Timing a pattern only works if the measurement returns, and
#: the audit's `(a+)+$` never finished on the thirty-one characters it
#: was reported with — 2^31 steps would not finish this week.
#:
#: Measured here: at twenty characters `(a+)+$` costs ~42 ms and
#: `(a*)*$` ~64 ms, against ~0.01 ms for a real pattern, so one cheap
#: probe catches the violent family. `(a|aa)+$` grows more slowly and
#: needs ~1.4 ms at twenty but ~9.7 ms at twenty-four. Only patterns
#: that survive the first probe reach the second, so the worst a bomb
#: can cost before being refused is the sum of the two budgets rather
#: than the second-nearly-a-second-long search on its own.
_PATTERN_PROBES = ("a" * 20 + "!", "a" * 24 + "!")

#: Three orders of magnitude above any honest pattern at those lengths,
#: and far below every bomb measured. A slow machine cannot close that.
_PATTERN_BUDGET_SECONDS = 0.005


def _compiled_within_budget(rule: dict[str, Any]) -> re.Pattern[str] | None:
    """Compile a configured pattern, and drop it if it is a bomb (D40).

    `risk_patterns` come from the audited repository and are applied to
    every source line. Python's `re` has no timeout and no step limit,
    so one nested quantifier is a denial of service against the host —
    the security policy names crafted-configuration DoS as in scope,
    which makes this a promise the code was breaking.

    Measured rather than pattern-matched. Detecting "dangerous regexes"
    syntactically means a blocklist that is both leaky and prone to
    refusing legitimate patterns; timing the pattern against a probe
    string asks the only question that matters. Refused patterns are
    skipped rather than fatal: a repository's own lint config should
    not be able to fail someone else's audit.
    """
    try:
        pattern = re.compile(rule["pattern"], re.IGNORECASE)
    except re.error:
        return None

    for probe in _PATTERN_PROBES:
        started = time.perf_counter()
        try:
            pattern.search(probe)
        except re.error:
            return None
        if time.perf_counter() - started > _PATTERN_BUDGET_SECONDS:
            return None
    return pattern


def risk_findings(
    root: Path, files: list[Path], config: dict[str, Any], index: SourceIndex | None = None
) -> list[RiskFinding]:
    source = index_or_new(index)
    findings: list[RiskFinding] = []
    for rule in config.get("risk_patterns", []):
        pattern = _compiled_within_budget(rule)
        if pattern is None:
            continue
        allowed = set(rule.get("extensions", []))
        for path in files:
            if allowed and path.suffix not in allowed:
                continue
            for idx, line in enumerate(source.lines(path), start=1):
                if pattern.search(line):
                    findings.append(
                        RiskFinding(
                            path=str(path.relative_to(root)).replace(os.sep, "/"),
                            line=idx,
                            name=rule["name"],
                            text=line.strip()[:180],
                        )
                    )
    return findings
