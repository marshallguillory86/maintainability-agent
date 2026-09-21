"""A presentation the doors accept is a presentation the question offers (D201).

`--format json` shipped on 2026-08-something and was accepted by both
doors — argparse on the CLI, the argument validator on MCP — for eleven
releases. It was offered by nothing: the TTY prompt read "chat (Enter),
markdown, or html", the MCP `default_format` question listed the same
three, and `PRESENTATIONS` held three.

That is not a rendering bug, which is why no rendering test saw it. It
is a capability built, validated and documented in the CLI reference
that no user was ever shown at the place the product asks. A reader of
[ADR 011](../docs/adr-011-three-report-presentations.md) could not find
it either, because the ADR never mentioned `json` at all — which is how
the same reader called its absence a defect twice in one day and was
twice told it was deliberate.

The claim is a universal one and the population is derived from the
argument parser rather than typed here: **every value `--format`
accepts is offered at the question.** A sixth format added to argparse
and not to `PRESENTATIONS` fails this, which is the recurrence being
blocked, not the instance.
"""

from __future__ import annotations

import argparse
import json

from maintainability_audit._arguments import add_arguments
from maintainability_audit._catalog import PRESENTATIONS


def _format_choices() -> set[str]:
    """Every value `--format` accepts, read off the parser itself."""
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    actions = [
        action
        for action in parser._actions  # noqa: SLF001 - the only accessor
        if action.dest == "format"
    ]
    assert len(actions) == 1, "the parser has no single --format action"
    return set(actions[0].choices or ())


def test_every_format_the_cli_accepts_is_offered_at_the_question() -> None:
    """`chat` is the one offered value with no flag: it is the absence of a file."""
    accepted = _format_choices()

    assert accepted, "the parser reported no --format choices, so nothing was checked"
    missing = sorted(accepted - set(PRESENTATIONS))

    assert not missing, (
        f"--format accepts {missing} and the presentation question offers "
        f"{list(PRESENTATIONS)}; a format the tool builds and nobody is shown"
    )


def test_choosing_json_at_the_terminal_renders_json(monkeypatch, tmp_path) -> None:
    """The answer has to reach the renderer, not only the parser.

    A fourth word accepted by the question and dropped by the resolver
    would render Markdown and report success — the `args.format or
    "markdown"` fallback, which is what the two file skins avoid by
    naming an output path instead.
    """
    from maintainability_audit import cli

    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args([])
    report = {"root": str(tmp_path), "overall": {"grade": "A"}}

    monkeypatch.setattr(cli, "_stdin_is_a_tty", lambda: True)
    monkeypatch.setattr(cli, "ask_presentation", lambda: "json")

    rendered = cli._render_presentation(args, report, tmp_path / "history.jsonl")

    assert json.loads(rendered)["overall"]["grade"] == "A"
    assert args.output is None and args.html_output is None, (
        "the json answer wrote a file; it is a stdout presentation like chat"
    )
