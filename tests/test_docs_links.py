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
# Percentage claims are therefore a review responsibility, not a build
# one. The canonical wording for the two that exist lives in
# studies.md so there is something to review against; nothing here
# detects a paraphrase of them. An audit correctly flagged an earlier
# description of this guard as overstating its generality, and a
# similarity heuristic added to cover the gap was removed as false
# confidence. If automatic enforcement is wanted later, the way is
# explicit approved-quotation markers and exact normalized comparison —
# not a threshold.
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
    claims or paraphrases of any kind; those are review's job. See the
    note on ``STUDY_FIGURE`` for why a pattern cannot do it.

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


SELF_AUDIT_DISTANCE_CLAIMS = (
    "one commit behind",
    "exactly one commit",
    "always current",
    "the latest report",
)


def test_the_self_audit_claims_provenance_not_distance() -> None:
    """The stamp says which commit; it must not promise how far.

    "Always exactly one commit behind" was true only on an unmerged
    feature branch. Every merge strategy breaks it — a merge commit puts
    the stamp two or more back, a squash makes it not an ancestor, a
    rebase rewrites the hash — and defending it meant regenerating the
    report whenever anything landed on top, which is a loop with no
    termination. It was regenerated three times in one session for
    exactly that reason.

    A stamped commit is a provenance record. Any claim about distance
    from HEAD is unmaintainable, so none may be made.
    """
    offenders = []
    for name in ("README.md", "docs/self-audit.md"):
        text = (ROOT / name).read_text(encoding="utf-8").lower()
        offenders += [f"{name}: {claim!r}" for claim in SELF_AUDIT_DISTANCE_CLAIMS if claim in text]

    assert not offenders, (
        "the self-audit must claim provenance, not distance from HEAD:\n" + "\n".join(offenders)
    )


def test_every_cli_flag_is_documented_and_every_documented_flag_exists() -> None:
    """docs/cli.md is prose over an interface, and prose drifts.

    Six flags shipped across Phases 4 and 5 — `--analyzers`, `--work`,
    `--record-history`, `--backfill`, `--backfill-interval` — and none
    reached the page a user reads to find out what the tool can do. A
    capability nobody can discover is a capability nobody has.

    Both directions: an undocumented flag is invisible, and a documented
    flag that no longer exists sends someone to a parser error.
    """
    import argparse
    import re

    from maintainability_audit.cli import add_arguments

    parser = argparse.ArgumentParser()
    add_arguments(parser)
    shipped = {
        option
        for action in parser._actions  # noqa: SLF001 - argparse exposes no public list
        for option in action.option_strings
        if option.startswith("--")
    } - {"--help"}

    page = (ROOT / "docs" / "cli.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"\| `(--[a-z-]+)", page))

    assert not shipped - documented, (
        f"flags with no entry in docs/cli.md: {sorted(shipped - documented)}"
    )
    assert not documented - shipped, (
        f"docs/cli.md documents flags the CLI does not have: "
        f"{sorted(documented - shipped)}"
    )


def test_the_readme_table_matches_the_stamped_self_audit() -> None:
    """A README that advertises a stale score is the defect this tool catches.

    It has happened before: an earlier revision advertised 5.0/A+ after
    the codebase had drifted to a B, and a hostile audit caught it. It
    happened again across Phases 4 and 5 — every row was from a
    117-file tree that now has 184 files.

    Compared row by row against `docs/self-audit.md` rather than by
    eye, because "the numbers look about right" is exactly how the last
    two drifts survived review.
    """
    import re

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    audit = (ROOT / "docs" / "self-audit.md").read_text(encoding="utf-8")

    def rows(text: str) -> dict[str, str]:
        return {
            name.strip(): value.strip().replace("*", "")
            for name, value in re.findall(r"^\| ([A-Z][^|]+?) \| ([^|]+?) \|$",
                                          text, re.M)
        }

    stamped, advertised = rows(audit), rows(readme)
    shared = set(stamped) & set(advertised)
    assert shared, "the README no longer quotes any metric from the self-audit"

    mismatched = {
        name: (advertised[name], stamped[name])
        for name in shared
        if advertised[name] != stamped[name]
    }
    assert not mismatched, (
        f"README advertises figures the stamped self-audit does not support "
        f"(readme, audit): {mismatched}"
    )


# ---------------------------------------------------------------------------
# The decision register is the single status source
# ---------------------------------------------------------------------------

# Statuses an ADR may carry on its own Status line. Implementation
# progress is not among them: it lives in the register, which is the one
# place it is stated.
ADR_STATES = ("Accepted", "Proposed", "Rejected", "Superseded")

# Words that turn a pointer into a competing status claim.
PROGRESS_CLAIMS = ("implemented", "not implemented")


def _adr_files() -> list[Path]:
    return sorted((ROOT / "docs").glob("adr-*.md"))


def _status_line(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- Status:"):
            return line
    return ""


def test_every_adr_declares_a_status() -> None:
    """An ADR with no status is a document nobody can act on."""
    missing = sorted(p.name for p in _adr_files() if not _status_line(p))

    assert not missing, f"ADRs with no `- Status:` line: {missing}"


def test_every_accepted_adr_appears_in_the_register() -> None:
    """The register answers "what are we still arguing about?" — once.

    ADR 010 was written, accepted and implemented without ever being
    added, so the register listed nine decisions where ten existed. A
    renamed ADR or a new `adr-011.md` must fail here the day it lands,
    not whenever somebody happens to read both files.
    """
    register = (ROOT / "docs" / "decisions.md").read_text(encoding="utf-8")
    missing = []
    for path in _adr_files():
        if "Accepted" not in _status_line(path):
            continue
        number = re.match(r"adr-(\d+)", path.name)
        assert number, f"{path.name} does not follow adr-NNN-title.md"
        if f"({path.name})" not in register:
            missing.append(path.name)

    assert not missing, (
        f"Accepted ADRs absent from the register: {missing}. "
        "Add a row to docs/decisions.md."
    )


def test_no_adr_carries_its_own_implementation_claim() -> None:
    """One status source, not two that can disagree.

    Before this, five ADRs said "Accepted", one said "Accepted and
    implemented", the register said "not implemented" for all of them,
    and docs/README.md said "Implemented" for all of them. Four answers
    to one question, and three of them wrong.

    An ADR's Status line points at the register or names a bare state.
    Progress belongs to the register alone.
    """
    offenders = {}
    for path in _adr_files():
        line = _status_line(path)
        lowered = line.lower()
        if any(claim in lowered for claim in PROGRESS_CLAIMS) and "register" not in lowered:
            offenders[path.name] = line
        elif not any(state in line for state in ADR_STATES):
            offenders[path.name] = line

    assert not offenders, (
        "ADR Status lines carrying their own progress claim, or naming no "
        f"recognised state: {offenders}"
    )


def test_the_readme_adr_table_points_at_the_register_rather_than_competing() -> None:
    """A second status table is a second thing to forget to update.

    The README's ADR rows may gloss what a decision is *about*. They may
    not carry an Implemented / not implemented flag, because that is the
    register's job and a duplicate drifts from it — which is exactly how
    ADR 007's refused rename came to be advertised as "outstanding" in
    one file and "refused" in another.
    """
    page = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    offenders = [
        line for line in page.splitlines()
        if line.startswith("| [ADR ")
        and any(claim in line.lower() for claim in PROGRESS_CLAIMS)
    ]

    assert not offenders, (
        "docs/README.md ADR rows state implementation status; that belongs "
        f"to docs/decisions.md: {offenders}"
    )
