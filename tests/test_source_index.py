"""Each file read once, each file parsed once.

Five scanners each needed the same lines and the same declarations, and
each computed them independently — so an audit read every file five
times and parsed every source file three times.

These tests pin the two properties that matter: the work is actually
shared, and every scanner still runs standalone without an index, since
each is a public entry point.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from maintainability_audit.config import load_config
from maintainability_audit.deadcode import dead_declarations
from maintainability_audit.duplication import duplicate_blocks, risk_findings
from maintainability_audit.idioms import divergent_idioms
from maintainability_audit.metrics import collect_metrics, iter_files
from maintainability_audit.similarity import near_duplicate_findings
from maintainability_audit.source import SourceIndex, index_or_new

SOURCE = """
def _helper(value):
    if value:
        return value * 2
    return 0
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# The work is shared
# ---------------------------------------------------------------------------

def test_a_file_is_read_only_once(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "app.py"
    write(path, SOURCE)
    index = SourceIndex()
    reads: list[Path] = []

    original = Path.read_text
    monkeypatch.setattr(Path, "read_text", lambda self, **kw: (reads.append(self), original(self, **kw))[1])

    for _ in range(5):
        index.lines(path)

    assert reads.count(path) == 1


def test_a_file_is_parsed_only_once(tmp_path: Path) -> None:
    path = tmp_path / "app.py"
    write(path, SOURCE)
    index = SourceIndex()

    first = index.declarations(path)
    second = index.declarations(path)

    assert first is second, "declarations should come from the cache, not be recomputed"
    assert [d.name for d in first[0]] == ["_helper"]


def test_lines_and_declarations_share_one_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One read of the file, however many callers ask about it.

    This asserted object identity until 2.11.0 — that `declarations`
    returned the very list `lines` did. That only ever held for Python,
    because every other language returns a *masked* copy to score
    against, and Python was handed its raw source. Fixing that (comments
    and string literals were being counted as branches) made the identity
    false while the property it stood for stayed true.

    So the read is counted directly, which is what the name claims.
    """
    path = tmp_path / "app.py"
    write(path, SOURCE)
    index = SourceIndex()

    reads = []
    original = Path.read_text

    def counted(self, *args, **kwargs):        # noqa: ANN001, ANN002, ANN003
        if self == path:
            reads.append(self)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counted)

    ranges, masked = index.declarations(path)
    raw = index.lines(path)

    assert len(reads) == 1, f"the file was read {len(reads)} times"
    assert ranges, "no declaration was found in the fixture"
    assert len(masked) == len(raw), (
        "the scored copy is derived from the same read and must line up "
        "with it, or every reported line number is off"
    )


def test_extensions_without_a_detector_return_no_declarations(tmp_path: Path) -> None:
    """Callers should be able to ask about any file without first
    checking the suffix."""
    path = tmp_path / "notes.md"
    write(path, "# heading\n")
    index = SourceIndex()

    ranges, lines = index.declarations(path)

    assert ranges == []
    assert lines == ["# heading"]


def test_undecodable_bytes_do_not_raise(tmp_path: Path) -> None:
    path = tmp_path / "bad.py"
    path.write_bytes(b"ok\n\xff\n")

    assert SourceIndex().lines(path)[0] == "ok"


# ---------------------------------------------------------------------------
# Every scanner still works without one
# ---------------------------------------------------------------------------

def test_index_or_new_supplies_a_throwaway() -> None:
    provided = SourceIndex()

    assert index_or_new(provided) is provided
    assert isinstance(index_or_new(None), SourceIndex)


def test_every_scanner_runs_standalone(tmp_path: Path) -> None:
    """Each of these is a public entry point and must not require an
    index to be threaded in."""
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "app.py", SOURCE)
    config = load_config(None)
    files = iter_files(tmp_path, config)

    assert collect_metrics(tmp_path, config, None)[0] == files
    assert duplicate_blocks(tmp_path, files, 20) == []
    assert risk_findings(tmp_path, files, config) == []
    assert near_duplicate_findings(tmp_path, files) == []
    assert divergent_idioms(tmp_path, files, config) == []
    assert {item["name"] for item in dead_declarations(tmp_path, files)} == {"_helper"}


def test_scanners_agree_whether_or_not_an_index_is_shared(tmp_path: Path) -> None:
    """A shared index must not change any result — only how often the
    work is done."""
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "a.py", SOURCE)
    write(tmp_path / "b.py", "def other():\n    return 1\n")
    config = load_config(None)
    files = iter_files(tmp_path, config)
    index = SourceIndex()

    assert dead_declarations(tmp_path, files) == dead_declarations(tmp_path, files, index)
    assert near_duplicate_findings(tmp_path, files) == near_duplicate_findings(tmp_path, files, index)
    assert duplicate_blocks(tmp_path, files, 20) == duplicate_blocks(tmp_path, files, 20, index)
