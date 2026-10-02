"""A source-suffixed symlink to nothing is skipped and named, never fatal.

D141 taught the walk to refuse a path that claims a source extension and
is not a regular file, for devices and FIFOs. A symlink whose target does
not exist also fails `is_file()`, so it hit the same refusal and the whole
audit ended in a traceback. The ordinary case is a link into a git
submodule that was not fetched: Magisk ships `cxx.h` that way, and could
not be audited at all.

There is nothing at the end of such a link to measure, so it is skipped —
and named, in the report and in the data, because D141's other lesson
stands: a scan that quietly measures less than it was asked to is the
absence read as a pass. A FIFO is still refused.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from maintainability_audit._operator_reads import PathNotAllowed
from maintainability_audit.config import load_config
from maintainability_audit.renderers import render_markdown
from maintainability_audit.report import build_report


def _tree_with_a_dangling_link(root: Path) -> None:
    (root / "src").mkdir()
    (root / "src" / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (root / "src" / "b.py").symlink_to("../vendor/missing/b.py")


def test_the_audit_completes_and_names_the_link(tmp_path: Path) -> None:
    _tree_with_a_dangling_link(tmp_path)

    report = build_report(tmp_path, load_config(None))

    assert report["summary"]["dangling_source_links"] == ["src/b.py"]
    assert report["summary"]["files_scanned"] >= 1


def test_the_markdown_report_names_the_link(tmp_path: Path) -> None:
    _tree_with_a_dangling_link(tmp_path)

    markdown = render_markdown(build_report(tmp_path, load_config(None)))

    assert "src/b.py" in markdown


def test_a_tree_without_one_says_nothing(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")

    report = build_report(tmp_path, load_config(None))

    assert report["summary"]["dangling_source_links"] == []
    assert "symlink" not in render_markdown(report).lower()


def test_only_the_dangling_link_is_skipped_and_a_fifo_is_still_refused(tmp_path: Path) -> None:
    """The skip is for a link to nothing, not for anything that is not a file."""
    _tree_with_a_dangling_link(tmp_path)
    build_report(tmp_path, load_config(None))
    os.mkfifo(tmp_path / "src" / "hang.py")

    with pytest.raises(PathNotAllowed, match="not a regular file"):
        build_report(tmp_path, load_config(None))


def test_the_html_report_names_the_link(tmp_path: Path) -> None:
    """Three skins of one report: HTML may not quietly omit what the others say."""
    from maintainability_audit._html_view import render_html

    _tree_with_a_dangling_link(tmp_path)

    page = render_html(build_report(tmp_path, load_config(None)), [])

    assert "src/b.py" in page
