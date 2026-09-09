"""Repository-controlled reads go through the regular-file primitive (D145).

Two questions, kept apart on purpose.

**Does a hostile path in the tree still hang or vanish?** That is asked by
behaviour, on real FIFOs, through the public entry points. It is the
question that matters and it cannot be satisfied by rearranging code.

**Did a new reader skip the door?** That is asked structurally, over a
written list of the readers that take a path from the audited tree.

The first version of this file could not answer either. It asserted its
violation list was non-empty and then that it was empty, which no state of
the code satisfies; and it derived its FIFO cases from "functions in
`_discovery.py` that call `read_text`" — the defect itself — so fixing the
defect emptied the parameter set and the module stopped collecting. A check
that can only run while the bug is present proves nothing about its absence.

The non-vacuity clause the falsifier standard requires belongs on the
population a sweep *walks*, never on the violations it finds. Both sweeps
here assert their population, and the population is derived from something
the fix does not delete: the literal filenames `_discovery` mentions, and
the module list below.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "maintainability_audit"

#: Readers that take a path the audited repository chooses. Written down
#: rather than inferred, because "repository-controlled" is a fact about
#: where the path came from and no AST walk can see that. Each entry is
#: checked to exist, so a rename fails here instead of silently emptying
#: the sweep.
TREE_READERS: tuple[tuple[str, str], ...] = (
    ("_discovery.py", "_generated_directories"),
    ("_discovery.py", "_vendored_directories"),
    ("_practice.py", "_read"),
    ("_banner.py", "banner_says_generated"),
    ("_semantic_ts.py", "recorded_type_analysis"),
    ("_test_commands.py", "_read"),
)

#: Root metadata files discovery reads because the tree named them. Taken
#: from the literals `_discovery.py` mentions anywhere, not from the calls
#: that used to read them unsafely.
METADATA_NAMES: tuple[str, ...] = ("package.json", ".gitmodules")

_DIRECT_READ_ATTRS = frozenset({"read_text", "open"})


def _function(module: str, name: str) -> ast.FunctionDef:
    tree = ast.parse((PACKAGE / module).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{module} no longer defines {name}()")


def _direct_reads(node: ast.FunctionDef) -> list[int]:
    """Lines where this function reads a path by name rather than by handle."""
    lines = []
    for call in (n for n in ast.walk(node) if isinstance(n, ast.Call)):
        func = call.func
        by_attribute = isinstance(func, ast.Attribute) and func.attr in _DIRECT_READ_ATTRS
        by_builtin = isinstance(func, ast.Name) and func.id == "open"
        if by_attribute or by_builtin:
            lines.append(call.lineno)
    return lines


def test_the_reader_list_is_a_population_and_every_member_resolves() -> None:
    """A sweep over a list that has gone stale proves nothing.

    Covers existing behaviour: this is the falsifier standard's own
    non-vacuity clause. It asserts the population is real, so it passes
    at any base where the readers exist — which is the point of it.
    """
    assert TREE_READERS, "no tree readers listed; the sweep below is vacuous"
    for module, name in TREE_READERS:
        _function(module, name)


@pytest.mark.parametrize(("module", "name"), TREE_READERS)
def test_a_tree_reader_never_reads_a_path_by_name(module: str, name: str) -> None:
    """`read_text` on a FIFO waits for a writer that never comes."""
    found = _direct_reads(_function(module, name))
    assert not found, (
        f"{module}:{name}() reads a repository-controlled path by name at "
        f"line(s) {found}; route it through read_source_file or "
        "open_regular_file so a device, socket or FIFO refuses instead of "
        "blocking the audit"
    )


def test_the_metadata_names_are_still_the_ones_discovery_reads() -> None:
    """The FIFO cases below must not drift away from the module.

    Covers existing behaviour: a drift guard on the parametrization,
    not a defence of the fix. `_discovery` mentioned both names before
    the change and after it, which is exactly why the cases are derived
    from the mentions rather than from the reads.
    """
    assert METADATA_NAMES, "no metadata names; the FIFO sweep is vacuous"
    source = (PACKAGE / "_discovery.py").read_text(encoding="utf-8")
    missing = [name for name in METADATA_NAMES if repr(name)[1:-1] not in source]
    assert not missing, (
        f"_discovery.py no longer mentions {missing}; update METADATA_NAMES "
        "or the FIFO cases are testing a path nothing reads"
    )


_PROBE = """
import sys; sys.path.insert(0, {src!r})
from pathlib import Path
from maintainability_audit._discovery import discover
from maintainability_audit.config import load_config
from maintainability_audit._operator_reads import PathNotAllowed
try:
    discover(Path({root!r}), load_config(None))
except PathNotAllowed:
    print('refused')
else:
    print('returned')
"""


@pytest.mark.parametrize("name", METADATA_NAMES)
def test_metadata_fifo_refuses_and_does_not_block(tmp_path: Path, name: str) -> None:
    """Refused, not waited on, and not read as an absent file."""
    os.mkfifo(tmp_path / name)
    probe = _PROBE.format(src=str(ROOT / "src"), root=str(tmp_path))
    try:
        finished = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True, text=True, timeout=15, check=False,
        )
    except subprocess.TimeoutExpired as error:
        pytest.fail(f"metadata FIFO {name!r} blocked discovery for {error.timeout}s")
    assert "refused" in finished.stdout, (
        f"metadata FIFO {name!r} did not refuse: "
        f"{finished.stdout.strip()!r} {finished.stderr[-300:]}"
    )


def test_a_source_suffixed_fifo_is_refused_by_the_unread_walk(tmp_path: Path) -> None:
    """The other half of D141: skipped by `is_file()` is not the same as absent.

    `unread_source` reports what share of the repository the score
    describes, so a FIFO skipped here goes missing from both sides of that
    fraction and the share reads as if the file never existed.
    """
    from maintainability_audit._operator_reads import PathNotAllowed
    from maintainability_audit.config import load_config
    from maintainability_audit.metrics import unread_source

    os.mkfifo(tmp_path / "hang.py")
    with pytest.raises(PathNotAllowed):
        unread_source(tmp_path, load_config(None))
