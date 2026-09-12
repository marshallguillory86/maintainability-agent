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


def test_no_surface_claims_chat_and_markdown_are_one_text() -> None:
    """The claim is false wherever it appears, so it is swept, not spot-fixed.

    `_finish_result`'s docstring said chat and markdown are "on the wire
    the two are the same text" while the code beside it already rendered
    chat bounded and markdown complete. That was corrected — and the
    **MCP tool docstring**, the one hosts actually read, went on saying
    it. Grok's next round found it still standing, having reported it the
    round before.

    Fixing the instance and not the class is what let one round's finding
    survive into the next, so this asserts over every module rather than
    over the two that were wrong.
    """
    import re
    from pathlib import Path

    package = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"
    # The negation is the correction, not the defect: `_mcp_audit` now
    # says the two are *not* one text, and a sweep that flagged its own
    # fix would be unmaintainable — the first version of this test did
    # exactly that and caught only itself.
    claim = re.compile(
        r"(?<!not )the same (Markdown|text) on the wire"
        r"|the two are (?!not )the same (text|Markdown)",
        re.I,
    )
    offenders = [
        f"{path.name}:{n}"
        for path in package.rglob("*.py")
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if claim.search(line)
    ]

    assert not offenders, (
        "chat is the bounded skin and markdown the complete report; these "
        f"say otherwise: {offenders}"
    )


def test_the_tool_docstring_hosts_read_names_both_skins() -> None:
    """The exposed contract, not only the internal one.

    `_finish_result` is internal. The docstring on the MCP tool is what a
    host renders for the person choosing a format, and it is the one that
    was still wrong after the internal fix.
    """
    import inspect

    from maintainability_audit import mcp_server

    source = inspect.getsource(mcp_server)
    start = source.index("async def audit_repository_tool")
    doc = source[start:source.index('"""', source.index('"""', start) + 3)]

    assert "bounded" in doc.lower(), "the tool docstring must name the chat skin as bounded"
    assert "complete" in doc.lower(), "the tool docstring must name markdown as complete"
