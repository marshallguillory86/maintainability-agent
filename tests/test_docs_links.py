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
