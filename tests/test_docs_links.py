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
# Figure shapes that only ever come from a study. Percentages are
# deliberately NOT here: this repository states "92% coverage gate" and
# "25% of modularity", and no regex separates those from "0.83%
# near-duplication". Including them would either fail the build on
# rubric and config values or force junk entries into the approved list.
#
# The gap that leaves is closed by
# ``test_a_near_miss_of_an_approved_summary_is_not_allowed_to_pass``:
# percentage-bearing study claims are approved summaries, and a drifted
# copy of one is caught by similarity rather than by pattern. What
# remains manual is a **brand-new** percentage-only claim resembling no
# existing summary; that relies on review. An audit correctly flagged an
# earlier description of this guard as overstating its generality.
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

    Scope, stated precisely rather than generously: this catches
    sentences containing an "N of M", a p-value, or a "median of N",
    anywhere in the prose. It does **not** catch percentage-only
    claims; drift in those is caught by the near-miss test below
    instead, and a brand-new one relies on review. See the note on
    ``STUDY_FIGURE`` for why a regex cannot do it.

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


def test_a_near_miss_of_an_approved_summary_is_not_allowed_to_pass() -> None:
    """A sentence that is almost an approved summary must be exactly one.

    This is what makes the approved list mean something for claims the
    figure detector cannot see. Percentages are unmatchable by pattern —
    "0.83% near-duplication" and "92% coverage gate" are the same shape
    — so an altered percentage inside an otherwise-approved sentence
    would have slipped through, which made listing those sentences as
    "approved" hollow.

    Similarity rather than pattern: paraphrasing is already forbidden by
    the policy, so a sentence that closely resembles an approved summary
    without matching it is either a drifted copy or a paraphrase, and
    both are violations.
    """
    from difflib import SequenceMatcher

    approved = approved_summaries()
    drifted: list[str] = []
    for name in QUOTING_DOCS:
        for sentence in _sentences((ROOT / name).read_text(encoding="utf-8")):
            for summary in approved:
                if summary in sentence:
                    break
                if SequenceMatcher(None, sentence, summary).ratio() > 0.85:
                    drifted.append(f"{name}: {sentence[:120]}\n    approved: {summary[:120]}")
                    break

    assert not drifted, (
        "sentences that nearly match an approved summary but are not it "
        "(quote it verbatim or rewrite so it is clearly not a quotation):\n" + "\n".join(drifted)
    )
