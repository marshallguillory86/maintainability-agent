"""Composing the runnable analyzer set from the repository itself — D15.

The policy pool (`_catalog`) answers "what may run here". This module
answers the question D15 actually asked: which of those tools can
produce evidence about THIS repository, given its language inventory
and the requested concerns. A tool whose integration reads no language
present — and which has no artifacts to read either — is deselected
before any probe or spawn, and returned as stated evidence rather than
silently dropped.

Split from `_analysis` when that file crossed the repository's own size
limit, and the split is load-bearing: selection returns *facts*, the
analysis layer turns them into coverage rows, so deciding never depends
on recording.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._generic import declared_adapter
from ._tool_adapters import adapter_for


@dataclass(frozen=True)
class Selected:
    """One tool the inventory and concerns actually chose to run."""

    tool: dict[str, Any]
    adapter: Any
    reads: tuple[str, ...]


@dataclass(frozen=True)
class Deselected:
    """One tool the inventory decided against, with the reason.

    A fact, not a coverage row: selection states what it decided and
    `_analysis` records it. Keeping row construction there is what lets
    selection sit below the analysis layer without a cycle.
    """

    slug: str
    detail: str
    concepts: tuple[str, ...]
    languages: tuple[str, ...]


def select_runnable(
    pool: list[dict[str, Any]], root: Path, inventory: Any,
    excludes: Sequence[str] = (), class_dirs: tuple[str, ...] = (),
) -> tuple[list[Selected], list[Deselected]]:
    """Compose the runnable set from the tree, not from policy alone (D15).

    The policy pool answers "what may run here"; this answers "what
    can produce evidence about THIS repository". A tool whose
    integration reads no language the tree contains — and which has no
    artifacts to read either — is deselected before any probe or
    spawn, and returned as stated evidence rather than silently
    dropped. That ordering is the whole of D15: selection consults the
    inventory, instead of resolving the pool whole and marking the
    mismatches inapplicable afterwards.

    Artifact-read tools are gated by their artifacts, not by source
    languages: a tree holding `.class` files reaches SpotBugs whatever
    its sources speak.
    """
    runnable: list[Selected] = []
    deselected: list[Deselected] = []
    for tool in pool:
        adapter = adapter_for(tool["slug"]) or declared_adapter(tool["slug"])
        reads = tuple(
            str(name).lower()
            for name in (getattr(adapter, "languages", ()) or tool.get("languages") or ())
        )
        if adapter is not None and hasattr(adapter, "class_dirs"):
            # analyzers.class_dirs for the adapter that reads compiled
            # output (ADR 012). Assigned on EVERY run — including back
            # to empty — because the registry holds one instance per
            # process and configured dirs must not leak between audits.
            # Before the gate below: that gate consults has_targets.
            adapter.class_dirs = class_dirs
        finds_targets = getattr(adapter, "has_targets", None) if adapter else None
        has_artifacts = finds_targets is not None and finds_targets(root, excludes)
        if inventory.applicable(reads) or has_artifacts:
            runnable.append(Selected(tool=tool, adapter=adapter, reads=reads))
            continue
        present = ", ".join(sorted(inventory.languages)) or "no recognised source"
        deselected.append(Deselected(
            slug=tool["slug"],
            detail=(
                f"reads {', '.join(reads[:4])}; this tree is "
                f"{present}, so it had nothing to examine"
            ),
            concepts=tuple(tool["measures"]),
            languages=reads,
        ))
    return runnable, deselected
