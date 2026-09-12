"""The demo tree still produces the work order its README promises.

Grok's audit, item 5: *"Self-audit says 'prefer leaving this repo alone.'
That is honest and a terrible demo. A tiny fixture with two real findings
and two prompts a stranger can paste into Claude would sell the thesis in
one minute."*

`examples/demo` is that fixture, and this is what stops it rotting. A
demo that quietly stops finding anything is worse than no demo: the
README goes on describing four items while the tool reports none, and
nobody notices until a stranger runs it.

The comparison is against a checked-in file rather than a property,
because the point of the demo is the *exact text* a reader is promised.
Regenerate it with `tools/regen_demo_prompt.py` when a renderer change
legitimately moves the output, and read the diff before committing it --
that diff is the blast radius of the change on every work order this tool
produces.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "demo"
GOLDEN = DEMO / "expected-prompt.md"


@pytest.fixture(autouse=True)
def _shipped_floors(real_population_floors):
    """Every test here runs at the floors a stranger's install actually has.

    `conftest._lift_population_floors` zeroes the population floors for
    the suite, so a two-file tree gets scored under pytest and not
    anywhere else. Without this the golden file would have been generated
    against a scored demo and compared against a scored demo, while every
    real run of `examples/demo` printed `Not scored` and a different
    `Worth` column -- a test agreeing with itself about behaviour no user
    ever sees.

    It is also the demo's whole point: the README explains the withheld
    score as the tool working, and that explanation is only true at the
    shipped floors.
    """
    return real_population_floors


def _demo_report() -> dict:
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    return build_report(DEMO, load_config(DEMO / "maintainability-agent.json"))


def _rendered() -> str:
    from maintainability_audit._work_order_view import work_order_markdown

    report = _demo_report()
    return "\n".join(
        work_order_markdown(report["work_order"], complete=True, root_label=".")
    ) + "\n"


def test_the_demo_tree_still_produces_a_work_order() -> None:
    """The failure this file exists for: a demo that finds nothing."""
    report = _demo_report()
    assert report["work_order"], (
        "examples/demo produced no work order at all. Its README promises "
        "four items; a stranger following it would conclude the tool does "
        "nothing. Either the fixture was repaired or a scanner regressed."
    )


def test_the_demo_shows_more_than_one_kind_of_problem() -> None:
    """One class repeated is the D159 shape, and it does not sell anything.

    A demo whose every row is the same finding demonstrates a rule, not a
    product. Grok asked for two real findings; the fixture carries three
    classes so this has a margin before it stops being a demo.
    """
    classes = {item["finding_class"] for item in _demo_report()["work_order"]}
    assert len(classes) >= 2, (
        f"the demo collapsed to a single finding class ({classes}); it no "
        "longer shows that the work order orders *kinds* of work"
    )


def test_the_demo_work_order_matches_the_checked_in_text() -> None:
    """What the README promises is what the tool prints.

    Root is normalised to `.` so the comparison is about the work order
    and not about where the repository happens to be checked out.
    """
    assert GOLDEN.exists(), f"{GOLDEN} is missing; regenerate it"
    expected = GOLDEN.read_text(encoding="utf-8")
    actual = _rendered()

    assert actual == expected, (
        "the demo work order no longer matches examples/demo/"
        "expected-prompt.md.\n\nIf a renderer change moved this "
        "deliberately, regenerate with tools/regen_demo_prompt.py and read "
        "the diff -- it is the blast radius of your change on every work "
        "order this tool produces.\n\n"
        f"expected {len(expected.splitlines())} lines, "
        f"got {len(actual.splitlines())}"
    )


def test_the_demo_readme_does_not_promise_more_than_the_tool_finds() -> None:
    """The README states a count; the count has to be true.

    A hand-written number in a README beside a generated artefact is the
    pairing that rots first, and the rot is invisible -- the README keeps
    reading correctly right up until someone checks.
    """
    import re

    readme = (DEMO / "README.md").read_text(encoding="utf-8")
    report = _demo_report()

    stated = re.search(
        r"(\w+) finding classes, (\w+) items", readme, re.I
    )
    assert stated, (
        "examples/demo/README.md no longer states its finding-class and "
        "item counts in the form this test reads, so nothing checks them"
    )
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
    classes = {item["finding_class"] for item in report["work_order"]}

    assert words[stated.group(1).lower()] == len(classes), (
        f"the README claims {stated.group(1)} finding classes; the tool "
        f"reports {len(classes)}: {sorted(classes)}"
    )
    assert words[stated.group(2).lower()] == len(report["work_order"]), (
        f"the README claims {stated.group(2)} items; the tool reports "
        f"{len(report['work_order'])}"
    )


@pytest.mark.parametrize("promise", [
    "72 lines, complexity 27",
    "billing.py:14",
    "invoices.py:15",
])
def test_the_demo_readme_quotes_real_output(promise: str) -> None:
    """Every specific the README quotes is one the tool actually produces.

    Covers existing behaviour for the README half -- it was written to
    match a real run -- but the pairing is new and this is what holds it.
    The numbers are the persuasive part of that page; a stale one is the
    first thing a sceptical reader checks.
    """
    readme = (DEMO / "README.md").read_text(encoding="utf-8")
    assert promise in readme, f"the demo README stopped quoting {promise!r}"


def test_the_demo_prompt_stays_readable() -> None:
    """A demo that takes ten minutes to read demonstrates the wrong thing.

    Marshall's rule: a prompt is a paragraph or two, not a program. The
    demo is where that is most visible, because it is the first work
    order most readers will ever see.
    """
    rendered = _rendered()
    assert len(rendered.splitlines()) < 120, (
        f"the demo work order grew to {len(rendered.splitlines())} lines; "
        "the README promises it reads in under a minute"
    )
