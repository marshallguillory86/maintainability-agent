"""A chosen report file is saved; chat gets the summary and the path.

The report — HTML or Markdown — is the complete record, with the history
charts drawn from the audit series. Chat is the bounded view. Found on
Scrollwork's first chat-door run with 3.9.0: `format: "html"` returned
the whole 257 KB HTML inline beside the Markdown and work orders, 309 KB
in one result. The host refused it for size and nothing was saved, so
the report and its charts reached nobody.

The host asks where to save (docs/help/first-run.md, the skill) and
passes that location as `output_path`. MA writes the file there and
returns the path. A file format with no location is refused before any
audit runs, so the host asks rather than guessing.
"""

from __future__ import annotations

import json

import pytest
from _mcp_fixtures import _drop_generated_line
from test_mcp_baseline_payload import _repo

from maintainability_audit._mcp_audit import InvalidAuditArgument, audit_repository


def _audit(root, **kwargs):
    return audit_repository(
        str(root), roots=(root.parent.resolve(),), record_history=False, **kwargs)


def test_html_is_written_to_the_chosen_directory_and_not_sent(tmp_path) -> None:
    root = _repo(tmp_path)
    (root / "docs").mkdir(exist_ok=True)

    result = _audit(root, format="html", output_path=str(root / "docs"))

    saved = root / "docs" / "maintainability-report.html"
    assert saved.is_file() and "<html" in saved.read_text(encoding="utf-8").lower()
    assert result["report_path"] == str(saved)
    assert "report_html" not in result
    assert "<html" not in json.dumps(result).lower(), "the HTML still travels in the result"


def test_markdown_writes_the_complete_report_and_sends_the_bounded_view(tmp_path) -> None:
    root = _repo(tmp_path)
    target = root / "audit.md"

    # Chat first: the saved file lands in the tree and a later scan counts it.
    chat = _audit(root, format="chat")
    result = _audit(root, format="markdown", output_path=str(target))

    assert target.is_file()
    assert result["report_path"] == str(target)
    assert _drop_generated_line(result["report_markdown"]) == _drop_generated_line(chat["report_markdown"]), (
        "chat must get the bounded view, never the complete report"
    )
    assert len(target.read_text(encoding="utf-8")) > len(result["report_markdown"])


@pytest.mark.parametrize("fmt", ["html", "markdown"])
def test_a_file_format_without_a_location_is_refused_before_auditing(tmp_path, fmt) -> None:
    root = _repo(tmp_path)

    with pytest.raises(InvalidAuditArgument, match="output_path"):
        audit_repository(str(root), roots=(root.parent.resolve(),), format=fmt)

    assert not (root / ".maintainability" / "history.jsonl").exists(), (
        "an audit ran before the refusal"
    )


def test_a_location_outside_every_allowed_root_is_refused(tmp_path) -> None:
    root = _repo(tmp_path / "inside")
    outside = tmp_path / "elsewhere"
    outside.mkdir()

    with pytest.raises(InvalidAuditArgument, match="output_path"):
        audit_repository(str(root), roots=(root.resolve(),), record_history=False,
                         format="html", output_path=str(outside))

    assert not list(outside.iterdir())


def test_chat_needs_no_location_and_writes_nothing(tmp_path) -> None:
    root = _repo(tmp_path)
    before = sorted(p.name for p in root.iterdir())

    result = _audit(root, format="chat")

    assert "report_path" not in result
    assert sorted(p.name for p in root.iterdir()) == before


@pytest.mark.parametrize("fmt", ["html", "markdown"])
def test_a_saved_report_is_not_audited_as_the_repositorys_code(tmp_path, fmt) -> None:
    """The next audit must measure the repository, not last run's report.

    A running history means a report saved on every run. Saved inside the
    tree and read back as source, it would grow the measured population by
    one file of generated HTML or Markdown per run and move the series
    it is there to chart.
    """
    root = _repo(tmp_path)
    before = _audit(root, format="json")["report"]["summary"]["files_scanned"]

    _audit(root, format=fmt, output_path=str(root))
    after = _audit(root, format="json")["report"]["summary"]["files_scanned"]

    assert after == before


def test_the_published_tool_takes_the_location_and_says_what_it_does() -> None:
    """A host can only pass what the tool publishes, and reads its docstring."""
    import inspect

    from maintainability_audit import mcp_server

    source = inspect.getsource(mcp_server)
    tool = source[source.index("async def audit_repository_tool("):]
    signature = tool[:tool.index(") -> dict[str, Any]:")]
    doc = tool[:tool.index("del ctx")]

    assert "output_path: str | None = None" in signature
    assert "output_path" in doc and "saved" in doc
    assert "never written to the\ntree" not in doc and "returned as text and never written" not in doc
