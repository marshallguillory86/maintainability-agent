"""P1's child boundary: not isolation — disclosure, and the report says it.

**This file arrived as a contract demanding network isolation** — that
`_runner` wrap every analyzer in `sandbox-exec`, `unshare`, `bwrap` or
`firejail`, and that the spawned argv carry the boundary. Two of its
four tests asserted that directly.

That half is **refused**, and the refusal is Marshall's call recorded
here rather than a silent deletion. `docs/product-intent.md` already
lists among the things this tool does not promise: *"That third-party
tools cannot use the network, or that a run is kernel-air-gapped. This
agent does not transmit the audited source; it does not sandbox
children."* A test demanding the opposite is not an unmet contract — it
contradicts a documented non-goal, and implementing it would have made
the product quietly assert something the intent page denies.

The reason is narrower than "we can't control them", because an OS
sandbox can: the analyzers are **not ours**, tool acquisition through
`analyzers.acquire_tools` is a shipped opt-in that *needs* the network,
and a blanket deny would change which tools run and therefore what the
evidence says. A scanner that constrains the toolchain it is measuring
is reporting on itself.

**The other half was a real gap and is fixed.** The intent page said it;
the report did not. That is a P8 failure rather than a P1 one — the
promise was correctly scoped all along, and the run relying on that
scoping never disclosed it to the person reading the output. The
coverage section now carries the note, once, when children actually ran.

The original contract wanted that disclosure in every tool's `detail`
row. It lives in the section prose instead: one sentence stating the
rule, not the same sentence on all forty rows.
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

    If a sandbox wrapper is ever genuinely wanted, this test is the place
    the decision gets reopened — deliberately, with the product-intent
    non-goal amended in the same change. It failing is not a bug to route
    around; it means the two halves have drifted apart again.
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


def test_both_skins_carry_every_coverage_note() -> None:
    """ADR 011: the skins render one report dict and never disagree.

    The HTML report carried **none** of these notes — including "Nothing
    examined", which `_coverage_notes` calls the point of the whole
    section — because the notes were built as Markdown strings inside the
    Markdown formatter. The child-boundary disclosure would have landed
    in exactly one skin for the same reason.

    Asserted over every note the records produce, so a fifth note added
    later cannot reach one skin only.
    """
    from maintainability_audit._coverage_notes import (
        coverage_note_records,
        coverage_notes,
        coverage_notes_html,
    )

    coverage = {
        "tools_contributed": 2,
        "concepts_single_source": ["complexity"],
        "concepts_unexamined": ["types"],
        "dimensions_declined": [
            {"dimension": "declarations", "measured_by": "built-ins",
             "reason": "lizard supplies no cognitive complexity"},
        ],
    }
    records = coverage_note_records(coverage)
    assert len(records) == 4, f"expected all four notes, got {len(records)}"

    # Compared on stripped text: one skin writes a dimension name in
    # backticks and the other in <code>, which is the two formatters
    # doing their job rather than a difference in what was said.
    markdown = "\n".join(coverage_notes(coverage)).replace("`", "")
    html = re.sub(r"<[^>]+>", "", "\n".join(coverage_notes_html(coverage)))

    for note in records:
        bare = note.title.replace("`", "")
        assert bare in markdown, f"markdown is missing {bare!r}"
        assert bare in html, f"html is missing {bare!r}"
        assert note.body.replace("`", "") in markdown, f"markdown lost {bare!r}'s body"
        assert note.body.replace("`", "") in html, f"html lost {bare!r}'s body"


def test_the_html_notes_do_not_leak_markdown_syntax() -> None:
    """A backtick reaching the page is one skin's syntax as another's text."""
    from maintainability_audit._coverage_notes import coverage_notes_html

    html = "\n".join(coverage_notes_html({
        "tools_contributed": 1,
        "concepts_unexamined": ["types"],
        "concepts_single_source": [],
        "dimensions_declined": [
            {"dimension": "declarations", "measured_by": "built-ins",
             "reason": "a reason"},
        ],
    }))

    assert "`" not in html, f"markdown backticks reached the HTML report:\n{html}"
    assert "<code>analyzers.depth</code>" in html, (
        "a configuration key in the prose must be marked up, not escaped flat"
    )


def test_the_html_notes_escape_before_marking_up() -> None:
    """Escaping after the code-span substitution would emit live markup."""
    from maintainability_audit._coverage_notes import coverage_notes_html

    html = "\n".join(coverage_notes_html({
        "tools_contributed": 0,
        "concepts_unexamined": ["<script>alert(1)</script>"],
        "concepts_single_source": [],
        "dimensions_declined": [],
    }))

    assert "<script>" not in html, f"unescaped markup reached the page:\n{html}"
    assert "&lt;script&gt;" in html
