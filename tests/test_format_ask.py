"""8.4 + 8.5: the question is asked where a human is, and only there.

The CLI asks at a TTY because that is where a person can answer; flags
win because a stated choice is not a question; CI never blocks because
an `input()` in a pipeline is a hung build — the same class as 6.1, and
held by the same kind of test.

MCP cannot ask at all: the server has no terminal, so the *prompt*
tells the host agent to ask and pass the answer as a format argument.
The tool itself never prompts and never writes the tree.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from test_history_schema2 import _repo

from maintainability_audit.cli import main
from maintainability_audit.mcp_server import audit_repository, create_server


def _tty(monkeypatch: pytest.MonkeyPatch, answer: bool) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: answer, raising=False)


def _script(monkeypatch: pytest.MonkeyPatch, asked: list[str], answers: dict[str, str]):
    def respond(prompt: str = "") -> str:
        asked.append(prompt)
        lowered = prompt.lower()
        for token, answer in answers.items():
            if token in lowered:
                return answer
        return ""

    monkeypatch.setattr("builtins.input", respond)


def test_a_tty_invoke_with_no_format_flag_asks_and_enter_means_chat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    root = _repo(tmp_path)
    _tty(monkeypatch, True)
    asked: list[str] = []
    _script(monkeypatch, asked, {})

    assert main(["--root", str(root)]) == 0

    format_prompts = [p for p in asked if "format" in p.lower() or "chat" in p.lower()]
    assert format_prompts, f"a TTY invoke with no format flag asked nothing: {asked}"
    out = capsys.readouterr().out
    assert "# Maintainability CI Report" in out, (
        "Enter did not select chat: the report was not printed to the terminal"
    )


def test_answering_html_writes_the_single_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    _tty(monkeypatch, True)
    asked: list[str] = []
    _script(monkeypatch, asked, {"format": "html", "chat": "html"})

    assert main(["--root", str(root)]) == 0

    written = tmp_path / "maintainability-report.html"
    assert written.exists(), "choosing html produced no HTML file"
    text = written.read_text(encoding="utf-8")
    assert "<svg" in text and "<style" in text


def test_a_format_flag_suppresses_the_question(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Flags win. A stated choice is not a question (ADR 011 invariant 4)."""
    root = _repo(tmp_path)
    _tty(monkeypatch, True)
    asked: list[str] = []
    _script(monkeypatch, asked, {})
    out = tmp_path / "report.md"

    assert main(["--root", str(root), "--output", str(out)]) == 0
    assert not [p for p in asked if "format" in p.lower() or "chat" in p.lower()], (
        f"--output was given and the CLI still asked: {asked}"
    )

    asked.clear()
    assert main(["--root", str(root), "--format", "markdown", "--output", str(out)]) == 0
    assert not [p for p in asked if "format" in p.lower() or "chat" in p.lower()]

    asked.clear()
    html = tmp_path / "report.html"
    assert main(["--root", str(root), "--html-output", str(html)]) == 0
    assert html.exists(), "--html-output did not produce the requested presentation"
    assert not [p for p in asked if "format" in p.lower() or "chat" in p.lower()], (
        f"--html-output was given and the CLI still asked: {asked}"
    )


def test_non_tty_never_asks_for_a_format(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    root = _repo(tmp_path)
    _tty(monkeypatch, False)

    def explode(prompt: str = "") -> str:
        raise AssertionError(f"input() on a non-TTY: {prompt!r}")

    monkeypatch.setattr("builtins.input", explode)

    assert main(["--root", str(root)]) == 0
    assert "# Maintainability CI Report" in capsys.readouterr().out


def test_the_choice_is_not_persisted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR 011 §3: ask every interactive invoke. No file remembers html."""
    root = _repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    _tty(monkeypatch, True)
    asked: list[str] = []
    _script(monkeypatch, asked, {"format": "html", "chat": "html"})
    assert main(["--root", str(root)]) == 0

    first = [p for p in asked if "format" in p.lower() or "chat" in p.lower()]
    asked.clear()
    assert main(["--root", str(root)]) == 0
    second = [p for p in asked if "format" in p.lower() or "chat" in p.lower()]

    assert first and second, "the question must be asked on every interactive invoke"


# --------------------------------------------------------------------
# 8.5 — MCP: the host asks; the tool takes an argument
# --------------------------------------------------------------------


def test_the_tool_takes_a_format_argument_and_never_prompts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(prompt: str = "") -> str:
        raise AssertionError("the MCP tool called input()")

    monkeypatch.setattr("builtins.input", explode)
    root = _repo(tmp_path)
    before = {p for p in root.rglob("*")}

    result = audit_repository(str(root), format="markdown", roots=(tmp_path.resolve(),))

    assert result["report_markdown"].startswith("# Maintainability CI Report")
    assert {p for p in root.rglob("*")} == before, "the MCP tool wrote the tree"


def test_chat_returns_markdown_and_html_is_returned_not_written(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    before = {p for p in root.rglob("*")}

    result = audit_repository(str(root), format="html", roots=(tmp_path.resolve(),))

    assert "report_markdown" in result, "chat always has the Markdown to show"
    assert "<svg" in result.get("report_html", ""), (
        "format=html returned no HTML text"
    )
    assert {p for p in root.rglob("*")} == before, (
        "HTML and Markdown files are written only by the CLI (ADR 011 §4)"
    )


def test_the_mcp_prompt_tells_the_host_to_ask(tmp_path: Path) -> None:
    server = create_server(roots=(tmp_path.resolve(),))
    prompts = asyncio.run(server.list_prompts())
    named = [p for p in prompts if p.name in {"maintainability-agent", "audit"}]
    assert named

    result = asyncio.run(server.get_prompt(named[0].name))
    text = " ".join(
        message.content.text if hasattr(message.content, "text") else str(message.content)
        for message in result.messages
    ).lower()

    assert "ask" in text and "format" in text, (
        "the prompt never tells the host to ask the user which presentation"
    )
    assert "chat" in text and "html" in text and "markdown" in text


def test_format_chat_is_markdown_on_the_wire(tmp_path: Path) -> None:
    """The host relays the user's own word for the default.

    The prompt tells the host to ask "chat, markdown, or html" and pass
    the answer as the format argument — so `format="chat"` is a legal
    input by the server's own instructions, and rejecting it makes the
    prompt a trap. Chat *is* Markdown on the wire (ADR 011 §2): same
    payload as the default, no HTML text, and never a tree write.
    """
    root = _repo(tmp_path)
    before = {p for p in root.rglob("*")}

    result = audit_repository(str(root), format="chat", roots=(tmp_path.resolve(),))

    assert result["report_markdown"].startswith("# Maintainability CI Report")
    assert result["format"] == "chat"
    assert "report_html" not in result, "chat renders no HTML"
    assert {p for p in root.rglob("*")} == before, "the MCP tool wrote the tree"
