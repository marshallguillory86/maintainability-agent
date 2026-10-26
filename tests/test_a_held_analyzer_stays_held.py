"""An analyzer held back on purpose is held by both jobs that resolve the pool (#296).

lizard 1.24.3 fails with "Fail to parse file" on JavaScript that 1.24.0
reads, and exits 1 for the whole batch, so the audit records lizard as
contributing nothing. Re-pinning to it dropped lizard from 26 of the 201
corpus repositories and would have moved the calibration constant 14% on
a broken tool rather than on any code. It stays at 1.24.0.

A hold has to be honoured where the pool is resolved, or it lasts one
refresh: the manual resolve job writes the next pins, and the weekly drift
check compares against them. Both apply `constraints/held.txt`, and every
hold there says why.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELD = ROOT / "constraints" / "held.txt"
WORKFLOW = ROOT / ".github" / "workflows" / "quality-gates.yml"
RESOLVING_JOBS = ("resolve-constraints", "analyzer-drift")


def _job(name: str) -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    match = re.search(rf"^  {name}:\n(.*?)(?=^  [a-z-]+:\n|\Z)", text, re.M | re.S)
    assert match, f"no job {name}"
    return match.group(1)


def test_every_hold_names_its_reason() -> None:
    lines = HELD.read_text(encoding="utf-8").splitlines()
    pins = [i for i, line in enumerate(lines) if re.match(r"^[A-Za-z0-9_.-]+==", line)]
    assert pins, "held.txt holds nothing"
    for i in pins:
        assert i > 0 and lines[i - 1].startswith("# "), f"{lines[i]} is held without a reason"


def test_lizard_is_held_at_the_version_that_parses() -> None:
    assert "lizard==1.24.0" in HELD.read_text(encoding="utf-8").splitlines()
    assert "lizard==1.24.0" in (ROOT / "constraints" / "analyzers.txt").read_text(encoding="utf-8").splitlines()


def test_both_jobs_that_resolve_the_pool_apply_the_holds() -> None:
    for name in RESOLVING_JOBS:
        installs = [line for line in _job(name).splitlines() if "pip install" in line and "pip install --upgrade pip" not in line]
        assert installs, f"{name} installs nothing"
        assert all("constraints/held.txt" in line for line in installs), f"{name} ignores the holds: {installs}"
