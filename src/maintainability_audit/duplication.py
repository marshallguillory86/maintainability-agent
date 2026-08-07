"""Repeated-block detection and configurable risk-pattern matching.

Extracted from ``metrics.py`` (2026-08-06). Both scanners here re-read
whole files and answer corpus-level questions — "does this block appear
elsewhere", "does any line match a configured pattern" — as opposed to
the per-file measurements ``metrics`` takes.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from ._metrics_types import RiskFinding
from .metrics import read_lines


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


def duplicate_blocks(root: Path, files: list[Path], block_size: int) -> list[dict[str, Any]]:
    seen: dict[tuple[str, ...], list[str]] = {}
    for path in files:
        lines = [normalize_for_dup(line) for line in read_lines(path)]
        useful = [line for line in lines if line and not line.startswith(("//", "#", "/*", "*", '"', "'"))]
        for idx in range(0, max(0, len(useful) - block_size + 1)):
            block = tuple(useful[idx : idx + block_size])
            if len(set(block)) <= 1:
                continue
            # Skip blocks made entirely of low-information lines (bare
            # identifiers, kwarg passthroughs, pure punctuation). See
            # ``_is_trivial_dup_line`` docstring for the rationale.
            if all(_is_trivial_dup_line(item) for item in block):
                continue
            seen.setdefault(block, []).append(f"{path.relative_to(root)}:{idx + 1}")

    dupes = []
    for block, locations in seen.items():
        unique_locations = sorted(set(locations))
        if len(unique_locations) > 1:
            dupes.append({"locations": unique_locations[:10], "count": len(unique_locations), "sample": list(block)})
    return sorted(dupes, key=lambda item: item["count"], reverse=True)


def risk_findings(root: Path, files: list[Path], config: dict[str, Any]) -> list[RiskFinding]:
    findings: list[RiskFinding] = []
    for rule in config.get("risk_patterns", []):
        pattern = re.compile(rule["pattern"], re.IGNORECASE)
        allowed = set(rule.get("extensions", []))
        for path in files:
            if allowed and path.suffix not in allowed:
                continue
            for idx, line in enumerate(read_lines(path), start=1):
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
