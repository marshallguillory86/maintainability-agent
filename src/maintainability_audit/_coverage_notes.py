"""What the coverage section says after its table.

The table answers "what ran". These notes answer the questions a reader
has *next*, and each exists because a report that omitted it was read as
good news:

- one source only — examined, but nothing corroborated it;
- a dimension the analyzer tier declined — measured by the built-in
  detectors, and the reader is owed the reason (P8);
- nothing examined — unmeasured, which is not clean;
- analyzer children are not network-isolated — the intent page has always
  said so, and the report did not.

Split out of `_scan_view` when that module reached this project's own
500-line file limit. They belong together: all four are the coverage
section's prose about its own gaps.

**One source, two skins.** The notes are built once as records and
formatted per skin. They used to be built as Markdown strings, which is
why the HTML report carried *none* of them — including "Nothing
examined", described three paragraphs above as the point of the whole
section. ADR 011's claim is that the skins render one report dict and
never disagree; a section whose prose existed only in the Markdown
formatter was that claim resting on nobody checking.
"""

from __future__ import annotations

import re
from html import escape
from typing import Any, NamedTuple


class CoverageNote(NamedTuple):
    """One gap, in the pieces a skin needs to render it.

    `concepts` are named separately from `body` because every skin marks
    them up as code and none of them wants to parse backticks back out
    of a sentence to do it.
    """

    title: str
    concepts: tuple[str, ...]
    body: str


def coverage_note_records(coverage: dict[str, Any]) -> list[CoverageNote]:
    """The gap notes, in the order a reader needs them."""
    notes: list[CoverageNote] = []

    single = coverage.get("concepts_single_source") or []
    if single:
        # Between covered and unexamined. A reader deciding how much
        # weight to put on a finding needs to know nothing corroborated it.
        notes.append(CoverageNote(
            title="One source only",
            concepts=tuple(single),
            body=(
                "A built-in detector examined these and no external tool did, "
                "so nothing corroborates them. Install a tool covering the "
                "concern to get a second opinion."
            ),
        ))

    for declined in coverage.get("dimensions_declined") or []:
        # P8, and not a rare path: lizard supplies no cognitive
        # complexity, so a JavaScript repository with lizard installed
        # takes this branch on every run. It used to be silent, which
        # left a declarations rate with nothing saying what produced it
        # -- and left a decision page crediting the analyzer pool for
        # work the built-in scanner was doing (D68).
        notes.append(CoverageNote(
            title=f"`{declined['dimension']}` measured by {declined['measured_by']}",
            concepts=(),
            body=f"{declined['reason']}.",
        ))

    unexamined = coverage.get("concepts_unexamined") or []
    if unexamined:
        # The point of the whole section. Silence about a concern is not
        # health, and a reader who is not told will assume it is.
        notes.append(CoverageNote(
            title="Nothing examined",
            concepts=tuple(unexamined),
            body=(
                "These concerns are unmeasured, not clean. Install a tool that "
                "covers them, or widen `analyzers.depth`, to have them reported."
            ),
        ))

    notes.extend(_child_boundary_note(coverage))
    return notes


def _child_boundary_note(coverage: dict[str, Any]) -> list[CoverageNote]:
    """What this run does not control about the tools it spawned.

    `docs/product-intent.md` has said since P1 was amended that this
    package "does not sandbox children", and lists *"that third-party
    tools cannot use the network"* among the things it does not promise.
    The **report** did not say it. A reader holding a page headed "no
    network access during analysis" and a list of tools that ran had no
    way to learn the second sentence does not cover the first — which is
    P8's gap, not P1's: the promise was correctly scoped, and the run
    relying on that scoping never disclosed it.

    Only when an external tool actually ran. With no children spawned
    there is nothing to disclose, and saying it anyway would be the noise
    this section is careful to avoid.
    """
    spawned = coverage.get("tools_contributed") or 0
    if not spawned:
        return []
    return [CoverageNote(
        title="Analyzer children are not network-isolated",
        concepts=(),
        body=(
            f"{spawned} external {'tool' if spawned == 1 else 'tools'} ran as "
            "local child processes. This agent does not transmit the audited "
            "source and opens no socket of its own, but it does not sandbox "
            "what it spawns: a third-party analyzer that reaches the network is "
            "outside what this run controls or observes. Determinism and no "
            "upload are the promise; a kernel air-gap is not."
        ),
    )]


def coverage_notes(coverage: dict[str, Any]) -> list[str]:
    """The gap notes as Markdown lines."""
    lines: list[str] = []
    for note in coverage_note_records(coverage):
        lead = f"**{note.title}:**"
        if note.concepts:
            lead += " " + ", ".join(f"`{name}`" for name in note.concepts) + "."
        lines.extend([lead, "", note.body, ""])
    return lines


def _inline_code_to_html(text: str) -> str:
    """`name` -> <code>name</code>, on already-escaped text.

    The note bodies name configuration keys the way prose about them has
    to, and the first cut of this formatter escaped them and stopped —
    so the HTML report printed a literal backtick around
    ``analyzers.depth``. That is the drift this module was just
    restructured to prevent, committed inside the fix for it: one skin's
    syntax surfacing as text in another.

    Escaping runs first, so nothing inside a span can close the tag.
    """
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escape(text))


def coverage_notes_html(coverage: dict[str, Any]) -> list[str]:
    """The same notes as HTML, from the same records.

    Concept names are marked up here rather than carried in as markup, so
    neither skin can render the other's syntax as literal text.
    """
    parts: list[str] = []
    for note in coverage_note_records(coverage):
        # The declined-dimension title names the dimension in backticks,
        # so the title needs the same treatment as the body — escaping it
        # and stopping is how the first leak happened one function up.
        lead = f"<p><strong>{_inline_code_to_html(note.title)}:</strong>"
        if note.concepts:
            lead += " " + ", ".join(
                f"<code>{escape(name)}</code>" for name in note.concepts
            ) + "."
        parts.extend([lead + "</p>", f"<p>{_inline_code_to_html(note.body)}</p>"])
    return parts
