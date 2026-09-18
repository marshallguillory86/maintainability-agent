"""The delegate config asserts which scanners must have run (D184).

secure-code-agent withholds the security grade when no scanner set was
asserted — "grade withheld: no gates.require_scanners is declared, so no
scanner set was asserted to have run". This repository's delegate config
declared `fail_on_severity`, `fail_on_category`, `fail_on_new` and
`max_unsuppressed` and never that, so the pillar could reach complete
coverage and still report a posture of `unverified` rather than a grade.

The two halves have to stay together: naming a scanner here that the gate job
does not install turns coverage from complete into a hard failure, which is
the loud version of the same mistake.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "secure-code-agent.json"
QUALITY_GATES = ROOT / ".github" / "workflows" / "quality-gates.yml"


def _gates() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))["gates"]


def test_the_delegate_config_asserts_a_scanner_set() -> None:
    required = _gates().get("require_scanners")
    assert required, (
        "secure-code-agent.json declares no gates.require_scanners, so the delegate "
        "asserts no scanner set and withholds the security grade however complete "
        "its coverage is"
    )


def test_the_job_that_runs_the_gate_installs_the_scanners_it_requires() -> None:
    """The asserted scanners must exist on the runner that asserts them.

    The gate job installs the delegate with its `required-scanners` extra for
    this reason. Without it the runner has none of them, every required
    scanner reports `unavailable`, and coverage becomes FAILED — the gate
    fails on the absence of a tool rather than on anything about the code.
    """
    text = QUALITY_GATES.read_text(encoding="utf-8")
    gate_jobs = [
        body
        for body in re.split(r"^  [A-Za-z0-9_-]+:\s*$", text, flags=re.MULTILINE)
        if re.search(r"^\s+secure-code-agent \\\s*$", body, flags=re.MULTILINE)
    ]
    assert gate_jobs, "no job runs secure-code-agent; the security pillar is never measured"
    for body in gate_jobs:
        assert "secure-code-agent[required-scanners]==" in body, (
            "the job that runs the security gate installs secure-code-agent without its "
            "required-scanners extra, so the scanners gates.require_scanners names are "
            "absent and coverage fails on missing tools"
        )
