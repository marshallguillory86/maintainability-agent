"""P1's child boundary: not isolation — disclosure, and the report says it.

**This file arrived as a Codex contract demanding network isolation** —
that `_runner` wrap every analyzer in `sandbox-exec`, `unshare`, `bwrap`
or `firejail`, and that the spawned argv carry the boundary.

That half is **refused**, and the refusal is Marshall's call recorded
here rather than a silent deletion. `docs/product-intent.md` already
lists among the things this tool does not promise: *"That third-party
tools cannot use the network, or that a run is kernel-air-gapped. This
agent does not transmit the audited source; it does not sandbox
children."* A test demanding the opposite is not an unmet contract — it
contradicts a documented non-goal, and satisfying it would have made the
product assert something the intent page denies.

The reason is narrower than "we cannot control them", because an OS
sandbox can: the analyzers are **not ours**, tool acquisition through
`analyzers.acquire_tools` is a shipped opt-in that *needs* the network,
and a blanket deny would change which tools run and therefore what the
evidence says. A scanner that constrains the toolchain it is measuring
is reporting on itself.

**The other half was a real gap and is fixed.** The intent page said it;
the report did not. That is a P8 failure rather than a P1 one — the
promise was correctly scoped all along, and the run relying on that
scoping never disclosed it to the person reading the output.

Covers existing behaviour: the two pins below hold decisions rather than
defend fixes, and say so individually.
"""

from __future__ import annotations

import re
from pathlib import Path

from maintainability_audit._coverage_notes import coverage_notes

ROOT = Path(__file__).resolve().parents[1]

RUNNER = ROOT / "src" / "maintainability_audit" / "_runner.py"
INTENT = ROOT / "docs" / "product-intent.md"

SANDBOX_WRAPPERS = ("sandbox-exec", "unshare", "--unshare-net", "firejail", "bwrap")


def _coverage(**overrides: object) -> dict:
    base = {
        "tools_contributed": 3,
        "concepts_single_source": [],
        "dimensions_declined": [],
        "concepts_unexamined": [],
    }
    base.update(overrides)
    return base


def test_the_report_discloses_that_children_are_not_isolated() -> None:
    """The gap that was real: intent said it, the report did not."""
    rendered = "\n".join(coverage_notes(_coverage()))

    assert "not network-isolated" in rendered, (
        f"coverage hid that children ran unsandboxed:\n{rendered}"
    )
    assert "does not sandbox what it spawns" in rendered, (
        "the note must say what this tool does not do, not merely that a "
        f"boundary is absent:\n{rendered}"
    )


def test_the_disclosure_does_not_claim_an_air_gap() -> None:
    """Overclaiming here would be worse than the silence it replaced."""
    rendered = "\n".join(coverage_notes(_coverage())).lower()

    assert "air-gap is not" in rendered, (
        "the note must deny the stronger reading a reader would otherwise take"
    )
    for overclaim in ("fully isolated", "cannot reach the network", "air-gapped"):
        assert overclaim not in rendered, f"the note claims too much: {overclaim!r}"


def test_the_disclosure_reaches_the_html_skin_too() -> None:
    """One note, both skins — the parity `_html_report_sections` now holds.

    Asserted through the HTML renderer rather than by reading the
    Markdown twice: the note is new, and a note that existed in one skin
    only is the defect that section was just restructured to prevent
    (ADR 011).
    """
    from maintainability_audit._html_report_sections import _coverage_notes_html

    html = "\n".join(_coverage_notes_html(_coverage()))

    assert "not network-isolated" in html, f"the HTML skin omitted the note:\n{html}"
    assert "`" not in html, "markdown syntax reached the HTML report"


def test_nothing_is_disclosed_when_no_child_ran() -> None:
    """No children spawned is nothing to disclose, not a quieter disclosure.

    Covers existing behaviour: at the base there was no disclosure at
    all, so this passed vacuously. It is a bound on the new note rather
    than a falsifier for it — the note must not fire on a run that
    spawned nothing — and it is only meaningful now that the note exists.
    """
    rendered = "\n".join(coverage_notes(_coverage(tools_contributed=0)))

    assert "network-isolated" not in rendered, (
        f"a run that spawned nothing described a child boundary:\n{rendered}"
    )


def test_the_runner_does_not_wrap_children() -> None:
    """The refused half, pinned so it cannot arrive by accident.

    Covers existing behaviour: the runner has never wrapped children, so
    this passes at the base by construction. That is what a pin is — it
    defends a decision against a future change, not a fix against a past
    one, and the falsifier standard is right that those are different.

    If a sandbox wrapper is ever genuinely wanted, this test is where the
    decision gets reopened — deliberately, with the product-intent
    non-goal amended in the same change.
    """
    runner = RUNNER.read_text(encoding="utf-8")
    found = [token for token in SANDBOX_WRAPPERS if token in runner]

    assert not found, (
        f"_runner wraps children in {found}, which contradicts the "
        "product-intent non-goal. Amend the intent page in the same change "
        "or drop the wrapper."
    )


def test_product_intent_matches_the_runner_sandbox_state() -> None:
    """The live P1 sentence flips only when a real wrapper ships.

    Covers existing behaviour: it passed at the base and must keep
    passing. Kept verbatim from the original contract because it is the
    one assertion that holds the code and the promise to each other, and
    it holds under either resolution — which is exactly what makes it
    worth having and exactly why it falsifies nothing.
    """
    runner = RUNNER.read_text(encoding="utf-8")
    intent = INTENT.read_text(encoding="utf-8")
    runner_has_wrap = any(token in runner for token in SANDBOX_WRAPPERS)
    intent_says_unsandboxed = bool(re.search(
        r"does not sandbox children|children are not network-sandboxed",
        intent,
        re.I,
    ))

    assert runner_has_wrap != intent_says_unsandboxed, (
        "product intent and _runner disagree about whether analyzer children "
        "receive network isolation"
    )


def test_a_delegated_producer_change_breaks_the_series() -> None:
    """A pillar this tool did not measure still moves when its producer does.

    `secure-code-agent` changed its normalizer twice in one day without
    touching the pillar document's schema: same shape, same fields, a
    different condition for the same repository. MA stores that condition
    in its history like any other, and the comparability gate could not
    see the change — so the trend joined straight across it.

    That is `_scan_history`'s opening defect arriving through a tool we
    delegate to rather than one we run: *"a wrong snapshot is obviously a
    snapshot, while a wrong trend looks like knowledge."*
    """
    from maintainability_audit._scan_history import (
        COMPARABILITY_FIELDS,
        ScanRecord,
        segments,
    )

    assert "delegated_producers" in COMPARABILITY_FIELDS, (
        "the producer's version must break a series; it is the only thing "
        "this tool can see that moves when their scoring does"
    )

    def record(producer: str) -> ScanRecord:
        return ScanRecord(
            recorded_at="2026-09-11T00:00:00Z", commit="c", branch="main",
            scope="full", rubric_version="3.3.0", calibration=1.0,
            thresholds_digest="d", analyzers=(), scored_languages=(),
            estimate=4.0, pillars={"security": 3.4},
            delegated_producers=(producer,),
        )

    same = segments([record("security:secure-code-agent 0.9.0"),
                     record("security:secure-code-agent 0.9.0")])
    assert len(same) == 1, "an unchanged producer must not split a series"

    moved = segments([record("security:secure-code-agent 0.9.0"),
                      record("security:secure-code-agent 0.10.0")])
    assert len(moved) == 2, (
        "a producer version change joined two incomparable scores into one series"
    )
    assert "producer" in moved[1].break_reason, (
        f"the break must name what changed; said: {moved[1].break_reason!r}"
    )
