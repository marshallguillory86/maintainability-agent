"""D62: the release plan's table is measured, not remembered.

Its own header warns that a previous version "survived fifty-five
commits past the point it stopped being true". It then did it again —
0.7.0 recorded as the last tag while v0.9.1 was shipped, 14,122 lines
against 20,071, 1,097 tests against 1,560.

Split out of `test_written_record` when that file crossed this
project's 500-line gate, which it did because of this test.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_the_release_plan_table_is_measured_not_remembered() -> None:
    """D62: the plan's own warning, enforced instead of hoped for.

    Its header says a previous version of this table "survived
    fifty-five commits past the point it stopped being true". It then
    did it again — last tag 0.7.0 recorded while v0.9.1 was shipped,
    14,122 lines against 20,071, 1,097 tests against 1,560.

    The tag is checked exactly, because it changes only when someone
    tags and there is no excuse for it being wrong. The counts are
    checked within a stated tolerance: they move with every commit, and
    a test demanding exactness would be edited to pass rather than read.
    Fifteen percent is wide enough to survive ordinary work and narrow
    enough that another fifty-five commits cannot hide inside it.
    """

    plan = _read(ROOT / "docs" / "release-plan.md")

    tags = subprocess.run(
        ["git", "-C", str(ROOT), "tag", "--sort=-v:refname"],
        capture_output=True, text=True, check=False,
    ).stdout.split()
    if tags:
        assert f"| Last tagged version | {tags[0]} |" in plan, (
            f"the release plan does not name {tags[0]} as the last tag"
        )

    modules = sorted((ROOT / "src").rglob("*.py"))
    lines = sum(
        len(path.read_text(encoding="utf-8").splitlines()) for path in modules
    )
    test_files = list((ROOT / "tests").glob("test_*.py"))

    for label, actual in (
        ("Production code", lines),
        ("Production code modules", len(modules)),
        ("Tests", len(test_files)),
    ):
        row = next(
            (line for line in plan.splitlines()
             if line.startswith(f"| {label.split(' modules')[0]} |")),
            None,
        )
        assert row, f"the release plan has no {label!r} row"
        numbers = [int(n.replace(",", "")) for n in re.findall(r"[\d,]+\d|\d", row)]
        assert numbers, f"the {label!r} row states no number: {row}"
        closest = min(numbers, key=lambda value: abs(value - actual))
        assert abs(closest - actual) <= actual * 0.15, (
            f"the release plan says {closest} for {label} and the tree has "
            f"{actual}; re-measure the table rather than editing this number"
        )
