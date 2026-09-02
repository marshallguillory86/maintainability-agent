"""Every language the tool opens is a language something reads.

Split from `test_unread_code.py` in 1.1.0. That file holds the founding
defect — a report may not carry a score for code it never read — and
these are the CI lints that keep the defect from coming back as a
*class*: the include list and the parser set must agree, a withheld
score must blame the missing parser rather than the population floor,
and the language table may not market a detector that never runs.

They live apart because they are the tests every new language touches.
C arrived in 1.1.0 and C++ and C# follow; the file they are added to
should be the one about language coverage, and it should have room.

`_repo`, the fixtures and the sample constants stay in
`test_unread_code`; what is needed here is imported from it, so there is
one definition of each.
"""

from __future__ import annotations

import re
from pathlib import Path

from test_unread_code import JAVA, _repo

from maintainability_audit.config import load_config
from maintainability_audit.report import build_report


def test_every_default_extension_is_parseable_or_has_a_stated_reason() -> None:
    """Each suffix the tool opens by default either yields declarations
    or is a suffix nobody expects declarations from.

    `include_extensions` and `DECLARATION_SUFFIXES` are two lists that
    drift apart silently, and the gap between them is where the false
    "too small" sentence lived. `.md` and `.css` are in the first and
    not the second on purpose — nobody expects a function from a
    stylesheet — so the rule is not "they must match", it is that a
    *source* suffix in the scan must be parseable or be reported as
    unparseable.
    """
    from maintainability_audit._metrics_types import KNOWN_SOURCE_SUFFIXES
    from maintainability_audit.declarations import DECLARATION_SUFFIXES

    included = set(load_config(None)["paths"]["include_extensions"])
    source = {s for s in included if s in KNOWN_SOURCE_SUFFIXES}
    unparseable = sorted(source - set(DECLARATION_SUFFIXES))

    assert not unparseable, (
        f"default include_extensions opens {unparseable} as source, and no "
        "declaration parser reads them. Either add a parser, drop them from "
        "the default, or — if this is deliberate — extend "
        "`test_following_the_remedy_does_not_produce_a_smaller_lie` to cover "
        "them so the withhold reason is asserted."
    )


def test_the_floor_is_never_blamed_when_a_missing_parser_explains_it(
    tmp_path: Path, real_population_floors: dict,
) -> None:
    """The structural form of the defect, asserted directly.

    A withheld score may not cite the declarations floor while
    `unread_source` is empty and scanned files carry suffixes no parser
    reads. That combination is precisely the false sentence: the files
    are present, they were opened, and the floor is a consequence of not
    being able to parse them rather than of the repository's size.
    """
    root = _repo(tmp_path / "blamed",
                 {f"src/Thing{n}.java": JAVA % {"n": n} for n in range(40)})
    config = load_config(None)
    config["paths"]["include_extensions"] = [*config["paths"]["include_extensions"], ".java"]

    report = build_report(root, config)
    summary, score = report["summary"], report["score"]
    reasons = score["evidence_status"]["reasons"]

    blames_floor = any(r["measurement"] == "summary.declarations_scanned" for r in reasons)
    unread_empty = not summary["unread_source"]
    has_unparseable = bool(summary["undetected_declarations"])

    assert not (blames_floor and unread_empty and has_unparseable), (
        "the score was withheld on the declarations floor while the files "
        "were read and unparseable — the floor is the symptom, the missing "
        f"parser is the cause. Reasons: {[r['measurement'] for r in reasons]}"
    )


# Phrases that assert the last-resort pattern scan as a working detector.
# Only positive claims: "not parsed for declarations" describes the same
# module truthfully and must stay sayable.
#
# Two patterns because the two contexts differ. A table cell is terse,
# so "Approximate" alone is the whole claim there. Prose is not, and
# reading the same word as a claim in prose caught a sentence saying the
# opposite ("does not get an approximate population") along with one
# about complexity scoring that has no bearing on this at all -- a lint
# that fails on the correction it was written to require is worse than
# no lint.
_SCAN_CLAIM = re.compile(
    r"(line-pattern|pattern scan|last[- ]resort|bounded by indentation|approximate)",
    re.I,
)
_PROSE_CLAIM = re.compile(r"(line-pattern|pattern scan|last[- ]resort)", re.I)
# A claim tied to the one case that is real -- Python whose AST parse
# failed -- is allowed anywhere.
_REAL_CASE = re.compile(r"(python|syntax error|unparseable|`?ast`?\b)", re.I)
# Digits and capitals both occur in real suffixes — `.f90`, `.F90` —
# and a reader that matched neither silently skipped the rows it was
# written to police, which is a lint that stops linting without failing.
_SUFFIX = re.compile(r"`(\.[A-Za-z][A-Za-z0-9]*)`")


def _language_table(text: str) -> list[str]:
    """The rows of the per-language table, excluding header and rule."""
    rows = [line for line in text.splitlines() if line.startswith("|")]
    return [row for row in rows[2:] if row.count("|") >= 3]


def _declarations_through_production(root: Path, suffix: str) -> int:
    """Declarations the real scan path finds, with `suffix` opted in."""
    from maintainability_audit.metrics import collect_metrics

    config = load_config(None)
    config["paths"]["include_extensions"] = [*config["paths"]["include_extensions"], suffix]
    _, _, functions = collect_metrics(root, config, None)
    return len(functions)


def test_the_language_table_does_not_market_a_detector_that_never_runs(
    tmp_path: Path,
) -> None:
    """A row claiming the pattern scan must name a suffix that reaches it.

    The table read "Everything else | line-pattern scan, bounded by
    indentation | Approximate; used only as a last resort" while the
    paragraph directly beneath it said only the listed extensions get
    declaration-level findings. Both could not be true, and the false
    one was the row a reader consults to decide whether this tool reads
    their language.

    `_regex_function_ranges` is real code, and its patterns match `def`,
    `function` and arrows. Reaching it with Java would not approximate
    anything; it would return zero declarations and let the report call
    that a measurement. The gate in `SourceIndex` and `collect_metrics`
    is what keeps that from happening, so the document may not advertise
    around it.

    Self-lifting by construction: the day `.java` joins
    `DECLARATION_SUFFIXES` behind a real detector, a row naming `.java`
    passes. What stays blocked is the claim that the *ungated* languages
    are scanned.
    """
    from maintainability_audit.declarations import DECLARATION_SUFFIXES

    root = _repo(tmp_path / "table", {f"src/Thing{n}.java": JAVA % {"n": n} for n in range(3)})
    if _declarations_through_production(root, ".java"):
        return  # a detector shipped; this page is somebody's to rewrite

    text = (Path(__file__).resolve().parents[1] / "docs" / "language-support.md").read_text(
        encoding="utf-8"
    )

    offenders = [
        row for row in _language_table(text)
        if _SCAN_CLAIM.search(row)
        and not (set(_SUFFIX.findall(row)) & set(DECLARATION_SUFFIXES))
    ]
    assert not offenders, (
        "docs/language-support.md offers a declaration scan for languages "
        "production never parses. A row claiming the pattern scan has to "
        "name a suffix in DECLARATION_SUFFIXES:\n" + "\n".join(offenders)
    )

    prose = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if not sentence.lstrip().startswith("|")
        and _PROSE_CLAIM.search(sentence)
        and not _REAL_CASE.search(sentence)
    ]
    assert not prose, (
        "docs/language-support.md presents the last-resort scan as a "
        "detector for languages outside DECLARATION_SUFFIXES. It runs for "
        "Python that `ast` could not parse, and nothing else:\n" + "\n".join(prose)
    )
