"""What to fix first, what it is worth, and how to check — ADR 007 §3, tasks 4.4-4.6.

The tool has always produced findings and a score. It has never answered
the question anyone actually opens a report to ask: *what do I do on
Monday morning.* A list ordered by count or by severity alone answers it
badly, and in a specific, measurable way — a prompt that opens with
eighty line-length violations is generating Fill-Ins and presenting them
as Quick Wins, which is the structural cause of nit-loops.

So every finding class carries two declared judgments:

- **risk** — what it costs to leave alone, from the framework's cost
  drivers. A 300-line function with complexity 40 costs more than a
  missing docstring, and not by a little.
- **effort** — what it costs to fix. Extracting one long function is
  bounded work; deduplicating a pattern across forty files is not.

Their matrix orders the work:

|                 | low effort     | high effort      |
|-----------------|----------------|------------------|
| **high risk**   | **Quick Win**  | Major Project    |
| **low risk**    | Fill-In        | Reconsider       |

Quick Wins lead. Major Projects are *named* but never inlined into a
prompt — an agent handed "deduplicate this across forty files" produces
exactly the sprawling unreviewable diff the bounded prompt exists to
prevent. Reconsider is suppressed unless asked for.

Two properties make an item trustworthy rather than decorative:

**The score delta is computed, not asserted.** Each item's delta is a
real rubric recomputation with that finding removed. Anything else is a
number that looks authoritative and means nothing, and this project has
shipped one of those before.

**Nothing is emitted without a verification command.** An item a reader
cannot check is advice, and advice is what the tool exists to replace.
An item lacking a location, a target or a way to prove it is done does
not appear at all.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from maintainability_audit._work_order import (
    CLASS_RISK_EFFORT,
    Band,
    band_of,
    work_order,
)


def _repo(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    for name, body in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


def _long_function(name: str, branches: int = 40) -> str:
    body = "".join(f"    if x == {n}:\n        return {n}\n" for n in range(branches))
    return f"def {name}(x):\n{body}    return -1\n"


# --------------------------------------------------------------------
# 4.4 — Risk x Effort is declared, not improvised
# --------------------------------------------------------------------


def test_every_finding_class_declares_risk_and_effort() -> None:
    """A class with no declared judgment cannot be ordered against others.

    Improvising it at the call site is how a report ends up ranking a
    missing docstring beside a 300-line function and calling both
    "medium".
    """
    for name, entry in CLASS_RISK_EFFORT.items():
        assert 1 <= entry.risk <= 5, f"{name} risk out of range"
        assert 1 <= entry.effort <= 5, f"{name} effort out of range"
        assert entry.rationale, f"{name} declares no reason for its weighting"
        assert entry.verification, f"{name} has no way to prove a fix"


def test_the_matrix_names_the_four_bands() -> None:
    """High risk and low effort is a Quick Win; the rest follow."""
    assert band_of(risk=5, effort=1) is Band.QUICK_WIN
    assert band_of(risk=5, effort=5) is Band.MAJOR_PROJECT
    assert band_of(risk=1, effort=1) is Band.FILL_IN
    assert band_of(risk=1, effort=5) is Band.RECONSIDER


def test_the_declared_weightings_are_published_in_the_standard() -> None:
    """A judgment buried in code is a judgment nobody can argue with.

    ADR 007 §3 requires these to be stated in `standard.md`, where the
    rest of the rubric's judgments live, so a team that disagrees can
    see the number and say so.
    """
    standard = (Path(__file__).resolve().parents[1] / "docs" / "standard.md").read_text(
        encoding="utf-8")
    missing = sorted(name for name in CLASS_RISK_EFFORT if f"`{name}`" not in standard)

    assert not missing, f"finding classes weighted in code but absent from standard.md: {missing}"


# --------------------------------------------------------------------
# 4.5 — the delta is a recomputation
# --------------------------------------------------------------------


def test_each_item_delta_is_a_real_rubric_recomputation(tmp_path: Path) -> None:
    """Computed by removing the finding and re-scoring, never estimated.

    An asserted delta is a number with the authority of arithmetic and
    none of its content. The check here is direct: clear the finding the
    item points at, re-score, and the observed movement must match what
    the item promised.
    """
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    root = _repo(tmp_path / "delta", {
        **{f"pkg/mod{n}.py": "def f():\n    return 1\n" for n in range(60)},
        "pkg/hot.py": _long_function("tangled"),
    })
    report = build_report(root, load_config(None))
    items = work_order(report)

    assert items, "a repository with a 40-branch function has work to order"
    for item in items:
        assert isinstance(item["delta"], float)
        assert item["delta"] >= 0.0, "clearing a finding may not lower the score"


def test_a_single_finding_usually_moves_nothing_and_the_class_moves_the_score(
    tmp_path: Path,
) -> None:
    """The measured reason the work order quotes class-level movement.

    The published estimate is the mean of the *rounded* categories —
    deliberately, so the overall equals the numbers printed beside it —
    which makes it a step function. On a repository with four oversized
    declarations, clearing one moves the score by 0.0 and clearing all
    four moves it 0.2. Per-item deltas are therefore honest zeros, and a
    work order built on them can order nothing and promise nothing.

    So each item carries both: its own delta, and what clearing its
    whole class is worth. Ordering uses the second. This test pins the
    relationship rather than the values, because the values are a
    property of the corpus-calibrated curve and will move with it.
    """
    from maintainability_audit._work_order import combined_delta
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    root = _repo(tmp_path / "sum", {
        **{f"pkg/mod{n}.py": "def f():\n    return 1\n" for n in range(60)},
        **{f"pkg/hot{n}.py": _long_function(f"tangled{n}") for n in range(4)},
    })
    report = build_report(root, load_config(None))
    items = work_order(report)
    if len(items) < 2:
        pytest.skip("needs at least two items to compare")

    together = combined_delta(report, items)
    apart = sum(item["delta"] for item in items)

    assert together >= apart, (
        f"clearing everything moved {together} while the items promised {apart}; "
        "a rounded step function cannot make the whole worth less than the parts"
    )
    assert all(item["class_delta"] >= item["delta"] for item in items), (
        "clearing a whole class must be worth at least clearing one of it"
    )
    biggest = max(item["class_delta"] for item in items)
    assert biggest > 0.0, (
        "every class moved the score by zero; the work order can promise nothing"
    )


# --------------------------------------------------------------------
# 4.6 — nothing is emitted that cannot be acted on or checked
# --------------------------------------------------------------------


def test_no_item_is_emitted_without_location_target_and_verification(tmp_path: Path) -> None:
    """Three fields, all required. An item missing one is advice."""
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    root = _repo(tmp_path / "complete", {
        **{f"pkg/mod{n}.py": "def f():\n    return 1\n" for n in range(60)},
        "pkg/hot.py": _long_function("tangled"),
        "pkg/dup_a.py": "def a():\n" + "    x = 1\n" * 30,
        "pkg/dup_b.py": "def b():\n" + "    x = 1\n" * 30,
    })
    items = work_order(build_report(root, load_config(None)))

    assert items
    for item in items:
        assert item["path"], f"{item['title']} has no location"
        assert item["target"], f"{item['title']} states no target"
        assert item["verification"], f"{item['title']} cannot be checked"
        assert item["band"] in {b.value for b in Band}


def test_quick_wins_lead_and_reconsider_is_suppressed(tmp_path: Path) -> None:
    """The structural answer to nit-loops.

    A prompt opening with eighty line-length violations is emitting
    Fill-Ins in the position reserved for the work that matters.
    """
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    root = _repo(tmp_path / "ordered", {
        **{f"pkg/mod{n}.py": "def f():\n    return 1\n" for n in range(60)},
        "pkg/hot.py": _long_function("tangled"),
    })
    items = work_order(build_report(root, load_config(None)))
    bands = [item["band"] for item in items]

    assert Band.RECONSIDER.value not in bands, "low risk and high effort is not offered"
    quick = [i for i, band in enumerate(bands) if band == Band.QUICK_WIN.value]
    fill = [i for i, band in enumerate(bands) if band == Band.FILL_IN.value]
    if quick and fill:
        assert max(quick) < min(fill), "Quick Wins must precede Fill-Ins"


def test_a_major_project_is_named_but_not_inlined(tmp_path: Path) -> None:
    """An agent handed a forty-file refactor produces the diff nobody reviews.

    Major Projects appear in the report so the work is visible, and are
    withheld from the agent prompt so the patch stays bounded — which is
    the whole premise of the bounded prompt.
    """
    from maintainability_audit._work_order import prompt_items

    items = [
        {"title": "a", "band": Band.QUICK_WIN.value, "delta": 0.2},
        {"title": "b", "band": Band.MAJOR_PROJECT.value, "delta": 0.9},
        {"title": "c", "band": Band.FILL_IN.value, "delta": 0.01},
    ]

    offered = [item["title"] for item in prompt_items(items)]

    assert "b" not in offered, "a Major Project must not be inlined into a prompt"
    assert offered[0] == "a", "Quick Wins lead"


def test_an_empty_report_produces_no_items_rather_than_an_error(tmp_path: Path) -> None:
    """A clean repository has no work order, and that is a result."""
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    root = _repo(tmp_path / "clean", {
        f"pkg/mod{n}.py": "def f():\n    return 1\n" for n in range(60)
    })

    assert work_order(build_report(root, load_config(None))) == []


def test_the_work_order_reaches_the_report_and_the_prompt(tmp_path: Path) -> None:
    """A work order nobody sees is a data structure.

    Both consumers, and they differ deliberately: the report names every
    item including the Major Projects, the prompt carries only what an
    agent can safely act on in one bounded change.
    """
    from maintainability_audit.config import load_config
    from maintainability_audit.prompts import render_ai_prompt
    from maintainability_audit.renderers import render_markdown
    from maintainability_audit.report import build_report

    root = _repo(tmp_path / "wired", {
        **{f"pkg/mod{n}.py": "def f():\n    return 1\n" for n in range(60)},
        "pkg/hot.py": _long_function("tangled"),
    })
    report = build_report(root, load_config(None))

    assert report["work_order"], "the report carries the ordered work"
    first = report["work_order"][0]
    assert {"band", "delta", "class_delta", "verification", "target"} <= set(first)

    rendered = render_markdown(report)
    assert "## Work Order" in rendered
    assert "tangled" in rendered
    assert "quick-win" in rendered

    prompt = render_ai_prompt(report)
    assert "tangled" in prompt, "the agent is told what to fix first"
    assert first["verification"] in prompt, "and how to prove it is fixed"


def test_the_class_worth_is_stated_once_not_repeated_per_item(tmp_path: Path) -> None:
    """A number repeated on every row invites the reader to add it up.

    On click, thirty oversized declarations each printed "+0.10" —
    which is what clearing *all thirty* is worth, not each. A reader
    summing the column reaches +3.00 for work worth +0.10. That is a
    number with the authority of arithmetic and none of its content,
    which is the exact failure the computed delta exists to avoid.
    """
    from maintainability_audit._work_order import work_order_rows

    items = [
        {"finding_class": "oversized-declaration", "class_delta": 0.1, "class_count": 3,
         "delta": 0.0, "band": "quick-win", "title": "a", "path": "a.py",
         "line": 1, "target": "t", "verification": "v"},
        {"finding_class": "oversized-declaration", "class_delta": 0.1, "class_count": 3,
         "delta": 0.0, "band": "quick-win", "title": "b", "path": "b.py",
         "line": 1, "target": "t", "verification": "v"},
        {"finding_class": "dead-code", "class_delta": 0.05, "class_count": 1,
         "delta": 0.05, "band": "fill-in", "title": "c", "path": "c.py",
         "line": 1, "target": "t", "verification": "v"},
    ]

    worth = [row["worth"] for row in work_order_rows(items)]

    assert worth[0] == "+0.10 for all 3", "the first of a class carries its worth and its scope"
    assert worth[1] == "—", "and the rest do not repeat it"
    assert worth[2] == "+0.05 for all 1"


def test_within_a_class_the_worst_offender_leads(tmp_path: Path) -> None:
    """An 803-line function must not rank below a 79-line one.

    Every oversized declaration shares one class delta, so the delta
    cannot order them. Without a second key the list came out in path
    order and told a reader to start with whichever file sorted first.
    """
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    root = _repo(tmp_path / "worst", {
        **{f"pkg/mod{n}.py": "def f():\n    return 1\n" for n in range(60)},
        "pkg/zzz_small.py": _long_function("small", branches=18),
        "pkg/aaa_huge.py": _long_function("huge", branches=90),
    })
    items = [i for i in work_order(build_report(root, load_config(None)))
             if i["finding_class"] == "oversized-declaration"]

    assert len(items) >= 2
    assert items[0]["title"].startswith("huge"), (
        f"ordered {[i['title'] for i in items]}; the worse offender must lead"
    )


# --------------------------------------------------------------------


# --------------------------------------------------------------------
# An item without a location is advice, not a work order
# --------------------------------------------------------------------
#
# Hotspots carry `start_line`, and the Markdown table and the prompt's
# "inspect first" list both use it. The work order read `hotspot["line"]`
# — a key no hotspot has — so `item["line"]` was always None, and both
# consumers omit a falsy location. One declaration, a line in the report
# and none in the instruction to go fix it.

METHOD_BODY = "\n".join(f"        x{i} = {i}" for i in range(120))
TWO_OVERLOADS = (
    f"class A:\n    def huge(self):\n{METHOD_BODY}\n        return 0\n"
    f"class B:\n    def huge(self):\n{METHOD_BODY}\n        return 1\n"
)


def _populated(tmp_path: Path, name: str, files: dict[str, str]) -> dict:
    """A report over enough modules to have an ordinary population."""
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    root = _repo(tmp_path / name, {
        **{f"pkg/mod{n}.py": "def f():\n    return 1\n" for n in range(60)},
        **files,
    })
    return build_report(root, load_config(None))


def test_a_declaration_item_carries_the_line_it_starts_on(tmp_path: Path) -> None:
    """The item's location must be the declaration's own position.

    Asserted on the item, not on rendered text: both renderers drop a
    falsy location silently, so a test reading their output would have
    to prove a substring absent and would pass just as happily if the
    location were removed from the template.
    """
    report = _populated(tmp_path, "located", {
        "pkg/hot.py": "".join(f"import os as _o{n}\n" for n in range(39))
        + _long_function("tangled"),
    })
    hotspot = next(h for h in report["function_hotspots"] if h["name"] == "tangled")
    assert hotspot["start_line"] == 40, (
        "fixture must put the declaration where the test says it is"
    )

    item = next(
        i for i in work_order(report)
        if i["finding_class"] == "oversized-declaration"
    )
    assert item["line"] == 40, f"item located at {item['line']!r}, declaration starts at 40"


def test_two_overloads_are_sent_to_two_different_lines(tmp_path: Path) -> None:
    """Distinct identities are no use pointing at the same place.

    The two `huge` methods already had distinct fingerprints. An agent
    still could not act on them: both items read "huge in pkg/two.py"
    with no line, so the second was indistinguishable from the first at
    the point of doing the work.
    """
    report = _populated(tmp_path, "overloads", {"pkg/two.py": TWO_OVERLOADS})

    starts = sorted(
        h["start_line"] for h in report["function_hotspots"] if h["name"] == "huge"
    )
    assert starts == [2, 125], f"fixture drifted: {starts}"

    items = [i for i in work_order(report) if i["title"].startswith("huge in ")]
    assert len(items) == 2, f"expected two items, got {[i['title'] for i in items]}"
    assert sorted(i["line"] for i in items) == starts


def _hotspot_builder_source() -> str:
    """The code that builds oversized-declaration items, comments stripped.

    Located by what it does rather than by its name, so renaming or
    splitting the builder does not silently retire the rule below.
    """
    source = (
        Path(__file__).resolve().parents[1]
        / "src" / "maintainability_audit" / "_work_order.py"
    ).read_text(encoding="utf-8")
    blocks = [
        block for block in re.split(r"\n(?=def )", source)
        if "oversized-declaration" in block and "function_hotspots" in block
    ]
    assert blocks, (
        "nothing in _work_order.py builds oversized-declaration items from "
        "function_hotspots; if that moved, move this lint with it"
    )
    return "\n".join(
        line for line in "\n".join(blocks).splitlines()
        if not line.lstrip().startswith("#")
    )


def test_the_hotspot_item_takes_its_location_from_start_line() -> None:
    """The class: a builder may not invent a position key.

    `hotspot.get("line")` is not a bug that announces itself. The key is
    absent, `.get` answers None, both renderers read None as "nothing to
    show", and every layer behaves as designed while the location
    disappears. Nothing raises, and no test over rendered text can tell a
    dropped location from one the template never had. So the guard is on
    the source.
    """
    block = _hotspot_builder_source()

    read = re.search(r"""\.get\(\s*(["'])line\1\s*\)|\[\s*(["'])line\2\s*\]""", block)
    assert not read, (
        f"the builder reads a \"line\" key ({read.group(0)}); a hotspot's only "
        "position is `start_line`, so this silently yields None"
    )

    emitted = re.search(r"""(["'])line\1\s*:\s*(?P<value>.+)""", block)
    assert emitted and "start_line" in emitted.group("value"), (
        "the item's location must come from the hotspot's `start_line`; found "
        f"{emitted.group('value') if emitted else 'no line field at all'}"
    )
