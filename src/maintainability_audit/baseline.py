from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._identity import finding_fingerprints

__all__ = ["finding_fingerprints", "load_baseline", "write_baseline"]

# Baselines written before identity used path, name and same-name ordinal
# embedded line numbers, so every fingerprint in them can be invalidated by
# an unrelated insertion. They are not migratable: the old strings do not
# carry what a new one needs. `load_baseline` detects them and says so
# rather than silently treating every finding as new.
BASELINE_VERSION = 2


class StaleBaseline(ValueError):
    """A baseline written under the line-coupled identity scheme."""


def load_baseline(path: str | None) -> set[str]:
    if not path:
        return set()
    baseline_path = Path(path)
    if not baseline_path.exists():
        return set()
    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    version = data.get("version", 1)
    if version != BASELINE_VERSION:
        # Failing closed matters more than convenience here. Loading a v1
        # baseline would suppress nothing, so every pre-existing finding would
        # surface as new and `--fail-on-new` would fail the build with no
        # explanation the reader could act on.
        raise StaleBaseline(
            f"{path} is baseline version {version}; this release writes version "
            f"{BASELINE_VERSION}. Finding identity is now path, name and "
            "same-name ordinal; old fingerprints cannot be converted. "
            "Regenerate with --write-baseline."
        )
    return set(data.get("findings", []))


def write_baseline(path: str, report: dict[str, Any]) -> None:
    # No score snapshot. Nothing ever read it back — `load_baseline`
    # takes the fingerprint list alone — and writing one would freeze an
    # obsolete report contract into every new baseline for no consumer.
    # Version 2: identity is path, name and ordinal, so a v1 file's
    # fingerprints mean something different and the loader rejects them.
    data = {
        "version": BASELINE_VERSION,
        "root": report["root"],
        "findings": sorted(finding_fingerprints(report)),
    }
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
