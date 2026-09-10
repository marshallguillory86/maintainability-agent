"""A release cuts from an empty defect ledger, and something checks it.

The standing rule is "no release until the known-defect ledger is
empty". Until D151 nothing enforced it: `test_written_record` holds the
disposition to *describing* the open headings, which keeps the register
internally consistent and says nothing about whether a release may go
out while entries are open.

v3.1.0 was tagged at 17:13 with a defect that had been reported twice in
wrap-ups and never filed. The register read zero because the entry did
not exist; it was written three hours later as D148. A gate cannot see
an unfiled defect — that half is the corollary about filing in the same
turn, which no check can enforce — but it can refuse the ordinary case,
and a rule nothing enforces is a rule that depends on whoever is tired.

The population is the release workflow's own steps, read from the file
rather than named here, so renaming the step does not quietly delete the
gate.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "docs" / ".." / ".github" / "workflows" / "release.yml"
REGISTER = ROOT / "docs" / "defect-register-chat-surface.md"

OPEN_HEADING = re.compile(r"^### D\d+ — Open", re.MULTILINE)


def _release_workflow() -> str:
    assert RELEASE.exists(), f"{RELEASE} is missing; the release gate cannot be checked"
    return RELEASE.read_text(encoding="utf-8")


def test_the_release_workflow_reads_the_register() -> None:
    """The gate must consult the ledger, not a copy of what it said."""
    workflow = _release_workflow()
    assert "defect-register-chat-surface.md" in workflow, (
        "the release workflow does not read the defect register; "
        '"no release until the known-defect ledger is empty" is then a '
        "rule enforced by memory"
    )


def test_the_gate_matches_the_heading_the_register_actually_uses() -> None:
    """A pattern that matches nothing passes every release silently.

    This is the failure mode that matters: a grep for a heading shape
    the register does not use returns zero on a register full of open
    entries, and the release proceeds looking checked. So the pattern in
    the workflow is exercised against the real file here.
    """
    workflow = _release_workflow()
    assert "### D[0-9]+ — Open" in workflow, (
        "the release gate no longer greps for the register's open-entry "
        "heading; if the heading format changed, change both together"
    )
    # The em dash matters — the register uses one, and a hyphen would
    # match nothing while still looking like a check.
    assert "—" in workflow, "the gate's pattern lost the em dash the headings use"


def test_the_register_currently_has_no_open_entries() -> None:
    """The ledger this repository would release from, right now.

    Not a style check: this is the state the rule requires before a tag,
    and it is worth failing in the ordinary suite rather than only in a
    release build, where the tag already exists.
    """
    register = REGISTER.read_text(encoding="utf-8")
    still_open = OPEN_HEADING.findall(register)
    assert not still_open, (
        f"{len(still_open)} open register entries; a release cuts from an "
        f"empty ledger: {still_open}"
    )
