from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ._finding_match import Identity, identities_from_report, rename_map, unmatched
from ._identity import finding_fingerprints

__all__ = [
    "finding_fingerprints",
    "findings_not_in_baseline",
    "load_baseline",
    "load_baseline_identities",
    "write_baseline",
]

# v1 embedded line numbers, so an unrelated insertion invalidated every
# fingerprint. v2 fixed the labels but stored only strings, so `git mv`
# and same-name reorder still surfaced untouched findings as new — the
# string cannot carry the body digest or the structure a matcher needs.
# v3 stores structured identity records plus the commit they were taken
# at, which is what `findings_not_in_baseline` matches against. Neither
# old version is migratable: the old strings do not carry what a new
# record needs. `load_baseline` detects them and says so rather than
# silently treating every finding as new.
BASELINE_VERSION = 3


class StaleBaseline(ValueError):
    """A baseline written under an older identity scheme."""


def _read(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    baseline_path = Path(path)
    if not baseline_path.exists():
        return None
    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    version = data.get("version", 1)
    if version != BASELINE_VERSION:
        # Failing closed matters more than convenience here. Loading an old
        # baseline would suppress nothing, so every pre-existing finding would
        # surface as new and `--fail-on-new` would fail the build with no
        # explanation the reader could act on.
        raise StaleBaseline(
            f"{path} is baseline version {version}; this release writes version "
            f"{BASELINE_VERSION}. Findings are now stored as structured identity "
            "records (kind, path, name, ordinal, body digest); old entries "
            "cannot be converted. Regenerate with --write-baseline."
        )
    return data


def load_baseline(path: str | None) -> set[str]:
    """The baseline's fingerprint labels, for string consumers.

    Honest but not the gate: the gate matches structured identities via
    `findings_not_in_baseline`, because a label set cannot survive
    `git mv` or a same-name reorder.
    """
    data = _read(path)
    return set(data.get("findings", [])) if data else set()


def load_baseline_identities(path: str | None) -> frozenset[Identity]:
    """The baseline's findings as identities, structured where stored.

    A label in `findings` with no structured record — a hand-written or
    hand-extended baseline — still suppresses its exact label: it
    becomes a degenerate identity that can match nothing but that
    string, which is all a bare label can honestly support.
    """
    data = _read(path)
    if not data:
        return frozenset()
    identities = {Identity(**record) for record in data.get("identities", [])}
    covered = {identity.fingerprint for identity in identities}
    identities.update(
        Identity(kind="label", path="", name="", ordinal=0, body_digest="",
                 fingerprint=label)
        for label in data.get("findings", []) if label not in covered
    )
    return frozenset(identities)


def baseline_commit(path: str | None) -> str:
    data = _read(path)
    return str(data.get("commit") or "") if data else ""


def findings_not_in_baseline(
    report: dict[str, Any], baseline_path: str | None, root: Path,
) -> frozenset[Identity]:
    """Current findings the baseline does not account for.

    Rename evidence comes from git itself, between the commit the
    baseline was written at and the commit under audit — so `git mv`
    alone cannot make an old finding read as new, while a copy with no
    recorded rename still does.
    """
    current = identities_from_report(report)
    known = load_baseline_identities(baseline_path)
    renames = rename_map(root, baseline_commit(baseline_path), report.get("git_commit") or "")
    return unmatched(current, known, renames)


def write_baseline(path: str, report: dict[str, Any]) -> None:
    # `findings` (labels) is kept beside the structured records: charts
    # and human diffs read strings, and the two views are derived from
    # one population so they cannot disagree.
    identities = sorted(identities_from_report(report), key=lambda i: i.fingerprint)
    data = {
        "version": BASELINE_VERSION,
        "root": report["root"],
        "commit": report.get("git_commit") or "",
        "findings": [identity.fingerprint for identity in identities],
        "identities": [asdict(identity) for identity in identities],
    }
    # Staged and bounded (D34). `baseline_path` is a caller argument on
    # the primary surface, and the previous write truncated whatever the
    # name pointed at — including source, in a tool that promises never
    # to write source.
    from ._safe_write import write_bounded

    # Bounded to the chosen directory, not to the repository: a CLI
    # caller may legitimately keep baselines outside the tree, and that
    # contract predates this fix. What the writer removes is redirection
    # — a symlink at the name, or a hardlink whose inode would be
    # truncated in place. Refusing to clobber *source* is a different
    # question, decided where the path arrives from a model rather than
    # a person: see `_baseline_workflow` (D34).
    target = Path(path)
    write_bounded(
        target.parent, target,
        json.dumps(data, indent=2, sort_keys=True) + "\n",
    )
