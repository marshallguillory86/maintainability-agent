"""The MCP presentation contract distinguishes a chat skin from a file."""
from __future__ import annotations

import inspect

from test_mcp_baseline_payload import _repo

from maintainability_audit._mcp_audit import _finish_result, audit_repository


def test_chat_is_bounded_and_markdown_is_the_complete_report(tmp_path) -> None:
    root = _repo(tmp_path)
    roots = (root.parent.resolve(),)
    chat = audit_repository(str(root), roots=roots, format="chat", record_history=False)
    markdown = audit_repository(
        str(root), roots=roots, format="markdown", record_history=False,
    )

    assert chat["report_markdown"] != markdown["report_markdown"]
    contract = inspect.getdoc(_finish_result) or ""
    assert "bounded" in contract.lower()
    assert "complete" in contract.lower()
