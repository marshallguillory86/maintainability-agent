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
    """Covers existing behaviour: the ledger this repository releases from.

    A guard, not a falsifier. It asserts the register's current state,
    which was already empty before this change and is meant to stay
    that way — so it passes at any base where the rule is being kept,
    which is the point of it.

    Worth having in the ordinary suite rather than only in the release
    build: there, the tag already exists by the time anything checks.
    """
    register = REGISTER.read_text(encoding="utf-8")
    still_open = OPEN_HEADING.findall(register)
    assert not still_open, (
        f"{len(still_open)} open register entries; a release cuts from an "
        f"empty ledger: {still_open}"
    )

def _build_steps() -> list[dict[str, str]]:
    """The build job's steps, as name/if/run text.

    Split by hand rather than with a YAML parser: `PyYAML` is
    deliberately kept off the test extra — `test_declared_imports`
    refuses it, because it would pull a catalog-regeneration parser into
    every test install. A step here is the block from one `- name:` to
    the next, which is all this file needs to know.
    """
    steps: list[dict[str, str]] = []
    inside = False
    for line in _release_workflow().splitlines():
        stripped = line.strip()
        if stripped.startswith("- name:") and line.startswith("      - name:"):
            steps.append({"name": stripped[len("- name:"):].strip(), "if": "", "run": ""})
            inside = True
            continue
        if not inside or not steps:
            continue
        if line and not line.startswith("       ") and not stripped.startswith("- "):
            inside = False
            continue
        if stripped.startswith("if:"):
            steps[-1]["if"] = stripped[3:].strip()
        steps[-1]["run"] += line + "\n"
    return steps


def _ledger_steps() -> list[dict[str, str]]:
    found = [s for s in _build_steps() if "defect-register-chat-surface.md" in s["run"]]
    assert found, "no step in the release workflow reads the defect register"
    return found


def test_no_publishing_trigger_skips_the_ledger_check() -> None:
    """Every path that can publish must pass the gate, not just a tag push.

    The first cut ran only for `refs/tags/`, so `workflow_dispatch` —
    which this workflow's own header documents as the way to publish a
    chosen ref — walked past it with an open register. A gate on one of
    two publishing paths is not a gate.

    The earlier test searched the workflow text and proved the step
    *existed*, which the conditional version satisfied. A condition is
    invisible to a substring search, so this reads the step's own `if`.
    """
    assert "workflow_dispatch" in _release_workflow(), (
        "this test exists because workflow_dispatch can publish; if that "
        "trigger is gone, the reasoning here needs rechecking"
    )
    for step in _ledger_steps():
        assert not step["if"], (
            f"the ledger check is conditional on {step['if']!r}; a publishing "
            "trigger that does not match it publishes with an open register"
        )


def test_the_gate_runs_before_anything_is_built_or_published() -> None:
    """Order matters: refusing after the upload is not refusing."""
    steps = _build_steps()
    names = [s["name"] for s in steps]
    ledger = next(
        i for i, s in enumerate(steps) if "defect-register-chat-surface.md" in s["run"]
    )
    built = next(i for i, n in enumerate(names) if "Test the built package" in n)
    assert ledger < built, (
        f"the ledger check is step {ledger}, after the build at {built}"
    )
