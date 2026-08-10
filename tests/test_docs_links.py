"""Internal documentation links resolve, including their anchors.

Written when `docs/standard.md` was split into the normative standard
and the empirical `studies.md`. Moving two sections between files
invalidated anchors referenced from the README, the philosophy page,
the roadmap, and two source comments — and nothing in the build would
have noticed. A link check that validates the file but not the fragment
passes happily while every deep link lands at the top of the wrong page.

Documentation that silently rots is how this project ended up with a
retracted claim still linked from three places, so the check is a test
rather than a habit.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Markdown we author. Generated reports and vendored skill payloads are
# excluded: self-audit.md is regenerated from a command, and its file
# references are report data rather than navigation.
AUTHORED = sorted(
    path
    for path in list(ROOT.glob("*.md")) + list(ROOT.glob("docs/*.md")) + list(ROOT.glob("tools/**/*.md"))
    if path.name != "self-audit.md"
)

LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
ATX_HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*$", re.M)


def slug(heading: str) -> str:
    """GitHub's anchor rule: lowercase, strip punctuation, spaces to dashes.

    Inline markdown is stripped first so that a heading written with
    code spans or emphasis produces the anchor a reader's link actually
    targets.
    """
    text = re.sub(r"`([^`]*)`", r"\1", heading)
    text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s", "-", text)  # each space becomes one dash, as GitHub does


def anchors(path: Path) -> set[str]:
    return {slug(heading) for heading in ATX_HEADING.findall(path.read_text(encoding="utf-8"))}


def test_every_internal_link_resolves_to_a_file_and_an_anchor() -> None:
    broken: list[str] = []
    for source in AUTHORED:
        for label, target in LINK.findall(source.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            path_part, _, fragment = target.partition("#")
            destination = source if not path_part else (source.parent / path_part).resolve()
            where = source.relative_to(ROOT)
            if not destination.exists():
                broken.append(f"{where}: [{label}] -> {target} (no such file)")
                continue
            if fragment and destination.suffix == ".md" and fragment not in anchors(destination):
                broken.append(f"{where}: [{label}] -> {target} (no such heading)")

    assert not broken, "broken documentation links:\n" + "\n".join(broken)


# A p-value is the unambiguous signature of a study result. Narrative
# words like "cohort" are not: the standard legitimately says its bands
# were *informed by* corpus measurements, which is a statement about
# provenance rather than a claim about the world.
STATISTICAL_RESULT = ("p = 0.", "p=0.", "p < 0.", "p<0.")


def test_the_standard_carries_no_empirical_study() -> None:
    """The genre split, enforced.

    `standard.md` is normative: judgments applied uniformly, legitimate
    without a study. The moment a p-value or a cohort table lands back
    in it, the document is making a claim about the world in a place
    where readers take statements as settled — which is exactly how the
    retracted AI-authorship claim reached the README.
    """
    standard = (ROOT / "docs" / "standard.md").read_text(encoding="utf-8")
    leaked = [marker for marker in STATISTICAL_RESULT if marker in standard]

    assert not leaked, (
        f"empirical content in the normative standard: {leaked}; "
        "move it to docs/studies.md (see docs/README.md on genres)"
    )


APPROVED_BLOCK = re.compile(
    r"<!-- approved-summaries:start -->(.*?)<!-- approved-summaries:end -->", re.S
)
# Figures that only ever come from a study. Deliberately broad: the
# point is to catch a restatement wherever it is written, including in
# ordinary prose, not only inside a blockquote.
STUDY_FIGURE = re.compile(r"\b\d+ of \d+\b|\bp = 0\.\d+\b|\bmedian of \d+(?:\.\d+)?\b")
QUOTING_DOCS = ("docs/product-intent.md", "README.md")


def approved_summaries() -> list[str]:
    block = APPROVED_BLOCK.search((ROOT / "docs" / "studies.md").read_text(encoding="utf-8"))
    assert block, "docs/studies.md must carry an approved-summaries block"
    return [line.lstrip("- ").strip() for line in block.group(1).splitlines() if line.strip()]


def _sentences(text: str) -> list[str]:
    """Prose split into sentences, with markdown emphasis stripped.

    Crude on purpose. A sentence splitter that is clever about
    abbreviations would be a second thing to maintain; this only has to
    isolate the sentence carrying a figure.
    """
    plain = re.sub(r"[*_`]", "", text)
    plain = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", plain)
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n", plain) if part.strip()]


def test_a_quoted_study_result_matches_an_approved_summary_verbatim() -> None:
    """Governing documents quote an approved sentence or say nothing.

    The previous guard checked whether each figure appeared *somewhere*
    in studies.md and only looked inside blockquotes. An audit showed
    what that misses: it read 1 of 5 figures in the README, none of the
    main summary because it was written as prose, and matching loose
    numbers cannot detect a swapped attribution or a different sentence
    assembled from the same digits. Comparison is now character for
    character against the approved list.
    """
    approved = approved_summaries()
    violations: list[str] = []
    for name in QUOTING_DOCS:
        for sentence in _sentences((ROOT / name).read_text(encoding="utf-8")):
            if not STUDY_FIGURE.search(sentence):
                continue
            if not any(summary in sentence for summary in approved):
                violations.append(f"{name}: {sentence[:150]}")

    assert not violations, (
        "study figures stated outside an approved summary "
        "(quote one verbatim from docs/studies.md#approved-summaries, or drop the figures):\n"
        + "\n".join(violations)
    )


def test_no_markdown_table_is_split_by_prose() -> None:
    """A row separated from its header renders as literal pipes.

    I did this: inserting a policy paragraph between two rows of the
    genre table left the Operational and Generated rows outside it, and
    every existing check passed because the links were fine and the
    words were correct. A table row whose preceding line is neither a
    row nor a header separator is orphaned.
    """
    orphans: list[str] = []
    for source in AUTHORED:
        previous = ""
        in_code = False
        for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code = not in_code
            if not in_code and stripped.startswith("|") and not previous.startswith("|"):
                # Legitimate only as a header, which a separator follows.
                orphans.append(f"{source.relative_to(ROOT)}:{number}: {stripped[:60]}")
            if not in_code and stripped:
                previous = stripped
        # A header row is reported above but is fine; drop rows whose
        # successor is a separator by re-reading with one line of context.
    text_by_file = {source: source.read_text(encoding="utf-8").splitlines() for source in AUTHORED}
    real = []
    for entry in orphans:
        path_part, number, _ = entry.split(":", 2)
        source = next(s for s in AUTHORED if str(s.relative_to(ROOT)) == path_part)
        lines = text_by_file[source]
        following = lines[int(number)].strip() if int(number) < len(lines) else ""
        if not re.match(r"^\|[\s:|-]+\|$", following):
            real.append(entry)

    assert not real, "markdown table rows orphaned from their header:\n" + "\n".join(real)
