"""A path the audited tree chose cannot leave the audited tree (D211).

`config.repository_path` has always bounded a *configured* path: resolve
it, refuse a target outside the root, then walk the lexical route and
refuse a symlinked component, because an inward `.maintainability -> src`
link passes a containment check on the resolved path and shows only on
the route (D34). Its refusal states the principle: *"the audited tree
cannot redirect where this agent reads or writes."*

Three readers take their paths **from the audited tree** and never went
through it — practice detection, test-command detection and the
generated-file banner. D147 routed them through the regular-file door,
which checks what a path *is*; nothing checked where it *goes*.

**The consequence was measurable.** A repository whose `pyproject.toml`
was a symlink to a file outside its root scored **practice level 2 with
a `linter-config` signal**; the same tree with an ordinary in-root file
scored **1**. The audited tree raised its own reported level using
evidence this tool was never pointed at — and practice level feeds the
pillar posture, so it reaches the report a reader acts on.

That is P3's shape reflected: P3 forbids *withholding* evidence from
improving a reported value, and this was *planting* evidence outside the
boundary to improve one.

The operator door is deliberately exempt and says so: an operator names
their own config and a symlinked config is an ordinary setup. The
difference this file turns on is **who chose the path**.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from maintainability_audit._operator_reads import PathNotAllowed, open_repository_file

SOURCE = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"

#: Modules whose reads take a path from the audited tree. Derived below
#: from the door they call, not trusted as a list: `test_the_population_
#: is_every_audited_tree_reader` fails if a fourth appears.
TREE_READERS = {"_practice", "_test_commands", "_banner"}


def _calls(module: str, name: str) -> int:
    tree = ast.parse((SOURCE / f"{module}.py").read_text(encoding="utf-8"))
    return sum(
        1 for node in ast.walk(tree)
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == name
    )


def test_the_population_is_every_audited_tree_reader() -> None:
    """Derived from the doors, so a fourth reader cannot appear unnoticed.

    A module that opens a repository path through the *unbounded* door
    is either a reader this file forgot or a regression, and either way
    it belongs in the failure message rather than in nobody's list.
    """
    unbounded = {
        path.stem for path in SOURCE.glob("*.py")
        if path.stem != "_operator_reads" and _calls(path.stem, "open_regular_file")
    }
    bounded = {
        path.stem for path in SOURCE.glob("*.py")
        if path.stem != "_operator_reads" and _calls(path.stem, "open_repository_file")
    }

    assert bounded | unbounded, "no module reads through either door"
    assert bounded | unbounded == TREE_READERS, (
        f"the readers changed: bounded={sorted(bounded)} "
        f"unbounded={sorted(unbounded)}, expected {sorted(TREE_READERS)}"
    )
    # `_banner` is the one exemption and it is stated rather than
    # incidental: it is called only from the discovery walk, on a path
    # that walk produced, and discovery does not descend an outbound
    # symlink — a tree carrying `leaked.py -> ../outside.py` audits with
    # `files_scanned: 1`. Its input is bounded before it is handed over,
    # and there is no root at that call site that would mean anything
    # the walk has not already decided.
    assert unbounded == {"_banner"}, (
        f"these read an audited-tree path through the unbounded door: "
        f"{sorted(unbounded - {'_banner'})}"
    )


def test_an_outbound_symlink_is_refused(tmp_path: Path) -> None:
    """The target resolves outside the root."""
    root = tmp_path / "repo"
    root.mkdir()
    (tmp_path / "outside.toml").write_text("[tool.ruff]\n", encoding="utf-8")
    link = root / "pyproject.toml"
    link.symlink_to(tmp_path / "outside.toml")

    with pytest.raises(PathNotAllowed):
        open_repository_file(root, link, "why")


def test_an_inward_symlink_is_refused_too(tmp_path: Path) -> None:
    """The case a containment check alone cannot see (D34).

    A link whose target resolves back *inside* the root passes "is it
    contained" and is still the tree redirecting a read. It shows only
    on the lexical route, which is why both checks are made.
    """
    root = tmp_path / "repo"
    (root / "real").mkdir(parents=True)
    (root / "real" / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")
    (root / "shadow").symlink_to(root / "real")

    with pytest.raises(PathNotAllowed):
        open_repository_file(root, root / "shadow" / "pyproject.toml", "why")


def test_the_tree_cannot_raise_its_own_practice_level(tmp_path: Path) -> None:
    """The worked example, end to end through the real reader.

    Asserted as *equality with the unlinked tree* rather than as a fixed
    number: what must hold is that the symlink buys nothing, and a
    future rubric change that moves both levels together leaves this
    true while a number typed here would go stale.
    """
    from maintainability_audit._practice import practice_level

    rich = tmp_path / "outside" / "rich.toml"
    rich.parent.mkdir()
    rich.write_text(
        '[tool.ruff]\nline-length = 100\n'
        '[tool.coverage.report]\nfail_under = 90\n',
        encoding="utf-8",
    )

    plain, linked = tmp_path / "plain", tmp_path / "linked"
    for root in (plain, linked):
        root.mkdir()
        (root / "app.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    (plain / "pyproject.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
    (linked / "pyproject.toml").symlink_to(rich)

    honest = practice_level(plain)
    redirected = practice_level(linked)

    assert redirected.level == honest.level, (
        f"a symlink out of the tree raised practice from {honest.level} to "
        f"{redirected.level}, which is the tree scoring itself on evidence "
        "this tool was never pointed at"
    )
    assert not [
        signal for signal in (redirected.as_dict().get("signals") or [])
        if signal not in (honest.as_dict().get("signals") or [])
    ], "the redirected tree earned a signal the honest one did not"


def test_an_ordinary_in_tree_file_still_reads(tmp_path: Path) -> None:
    """The boundary must not be a mute button.

    Practice detection exists to find these files; a check that refused
    everything would pass every assertion above and measure nothing.
    """
    root = tmp_path / "repo"
    root.mkdir()
    target = root / "pyproject.toml"
    target.write_text("[tool.ruff]\n", encoding="utf-8")

    handle = open_repository_file(root, target, "why")

    assert handle > 0
    import os

    os.close(handle)
