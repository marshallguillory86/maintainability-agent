"""Work-order item location and competing-libraries.

Split from test_work_order.py so both stay under the file-length gate.
"""
from __future__ import annotations

import re
from pathlib import Path

from test_work_order import _long_function, _repo

from maintainability_audit._work_order import work_order

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


# --------------------------------------------------------------------
# A class that cannot fire is an advertised judgment with no finding
# --------------------------------------------------------------------
#
# `CLASS_RISK_EFFORT` declares competing-libraries, the standard
# publishes its weighting, and the delta machinery prices its counter.
# The builder read `idiom_concerns`, a key the report does not have, so
# the class never produced an item. Renaming the key alone does not fix
# it: an idiom finding has no `path`, `first_path` or `line`, and the
# loop drops anything without one.

HTTPX = "import httpx\n\n\ndef fetch{n}():\n    return httpx.get('/{n}')\n"
AIOHTTP = "import aiohttp\n\n\ndef poll():\n    return aiohttp.ClientSession()\n"


def _competing_libraries(tmp_path: Path, name: str = "idioms") -> dict:
    """Two HTTP clients, httpx in the majority so `packages[-1]` is fixed."""
    return _populated(tmp_path, name, {
        "svc/a.py": HTTPX.format(n=1),
        "svc/c.py": HTTPX.format(n=2),
        "svc/b.py": AIOHTTP,
    })


def test_competing_libraries_reach_the_work_order(tmp_path: Path) -> None:
    """The class fires, and lands on the library that has to move.

    Located at the least-used package's example, which is where the
    prompt and the Markdown table already point. Asserting the path
    rather than only the item's existence is what makes a key-rename
    without a locator still fail: such an item has no path and is
    dropped before it reaches this list.
    """
    report = _competing_libraries(tmp_path)
    findings = report["divergent_idioms"]
    assert findings, "fixture must produce a divergent idiom"
    minority = findings[0]["packages"][-1]
    assert minority["package"] == "aiohttp", f"majority ordering drifted: {findings[0]}"

    # Reconsider by declared weighting (risk 2, effort 4), so it is
    # suppressed from the default order — asking for it is the only way
    # to see whether it exists at all.
    items = [
        i for i in work_order(report, include_reconsider=True)
        if i["finding_class"] == "competing-libraries"
    ]
    assert len(items) == 1, f"expected one idiom item, got {items}"

    item = items[0]
    assert item["path"] == minority["example"], (
        f"item points at {item['path']!r}, the least-used library is at "
        f"{minority['example']!r}"
    )
    assert findings[0]["concern"] in item["title"], (
        f"the title must name the concern: {item['title']!r}"
    )
    assert "remove" not in item["target"].lower(), (
        f"converging two libraries is a migration, not a removal: {item['target']!r}"
    )


def test_the_other_counted_classes_are_unchanged_and_no_idiom_is_invented(
    tmp_path: Path,
) -> None:
    """One library per concern produces no idiom item, and the located
    classes still locate themselves from `path` / `first_path`."""
    report = _populated(tmp_path, "counted", {
        "pkg/debt.py": "def g():\n    # TODO: finish this\n    return 1\n",
        "svc/only.py": HTTPX.format(n=1),
    })
    assert not report["divergent_idioms"], "fixture must not diverge"
    assert report["risk_findings"], "fixture must still produce a located finding"

    items = work_order(report, include_reconsider=True)
    assert not [i for i in items if i["finding_class"] == "competing-libraries"]

    risks = [i for i in items if i["finding_class"] == "risk-pattern"]
    assert risks, "the risk-pattern class stopped producing items"
    assert all(i["path"] and i["line"] for i in risks), (
        f"a located item lost its location: {[i for i in risks if not i['line']]}"
    )


def _competing_libraries_source() -> str:
    """The code that builds competing-libraries items, comments stripped.

    Found by what it does, so moving the class back into the located
    loop does not retire the rule — that arrangement reads a `path` off
    the finding and trips the second assertion below.
    """
    source = (
        Path(__file__).resolve().parents[1]
        / "src" / "maintainability_audit" / "_work_order.py"
    ).read_text(encoding="utf-8")
    blocks = [
        block for block in re.split(r"\n(?=def )", source)
        if '"competing-libraries"' in block and "report.get" in block
    ]
    assert blocks, "nothing builds competing-libraries items from the report"
    return "\n".join(
        line for line in "\n".join(blocks).splitlines()
        if not line.lstrip().startswith("#")
    )


def test_competing_libraries_reads_the_key_the_report_actually_carries() -> None:
    """The class: an advertised finding class must be reachable.

    `idiom_concerns` is not a key the report has ever had, so
    `report.get(...)` answered `[]` and a class with a declared
    weighting, a published rationale and a priced counter produced
    nothing — for as long as it has existed. Nothing failed; the class
    was simply never seen, which is the failure mode a weighting table
    cannot catch on its own.
    """
    block = _competing_libraries_source()

    # Quoted forms only. These names appear in the prose above the code
    # to explain the defect, and a lint that cannot tell a key it reads
    # from a key it warns about forbids its own explanation.
    assert re.search(r"""["']divergent_idioms["']""", block), (
        "the report key is `divergent_idioms`; reading anything else makes the "
        "class silently unreachable"
    )
    assert not re.search(r"""["']idiom_concerns["']""", block), (
        "`idiom_concerns` is not a report key, so it reads as an empty list"
    )

    located = re.search(
        r"""["']first_path["']|\.get\(\s*(["'])path\1|\[\s*(["'])path\2\s*\]""", block)
    assert not located, (
        f"idiom findings carry no path ({located.group(0)} would drop every one "
        "of them); locate the item from packages[-1]['example']"
    )
    assert "packages" in block and "example" in block, (
        "the item must be located from the least-used package's example"
    )
