"""Every CI job that installs the dev extras installs them under the pool's pins.

`lizard` is both a dev extra (`lizard>=1.17`) and a pinned analyzer
(`constraints/analyzers.txt`), and `tests/test_grammar_constructs.py` checks
the scanner against it, declaring the constructs where the two are known to
differ. A job that installed the dev extras without the pins took lizard
1.24.1, which counts Rust match arms as the scanner does, so the declared
divergence vanished and the test failed — on macOS, and then in the release
job, which refused to publish 4.3.1. One oracle, one version, every job.

The jobs are read from the workflow files, not listed here, so a job added
later is held to the same rule.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
CONSTRAINTS = "constraints/analyzers.txt"


def _jobs(text: str) -> dict[str, str]:
    """Each job's body under `jobs:`, keyed by its id."""
    body = text.split("\njobs:\n", 1)[1]
    parts = re.split(r"^  ([A-Za-z0-9_-]+):\s*$", body, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


def test_the_workflows_have_jobs_that_install_the_dev_extras() -> None:
    found = [job for wf in WORKFLOWS for job, body in _jobs(wf.read_text(encoding="utf-8")).items()
             if re.search(r"pip install[^\n]*\.\[dev\]", body)]
    assert len(found) >= 5, found


def test_every_job_installing_the_dev_extras_applies_the_pins() -> None:
    unpinned = [f"{wf.name}:{job}" for wf in WORKFLOWS
                for job, body in _jobs(wf.read_text(encoding="utf-8")).items()
                if re.search(r"pip install[^\n]*\.\[dev\]", body) and CONSTRAINTS not in body]
    assert unpinned == [], f"these jobs test against an unpinned lizard: {unpinned}"
