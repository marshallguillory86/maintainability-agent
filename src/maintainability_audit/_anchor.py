"""What the reference corpus does not hold, and how to say it.

Rubric data, like `_calibration`: a fact about the anchor rather than a
computation over a repository. It lives beside the constant it qualifies
because the two go stale together — a recalibration that adds Swift and
COBOL to the corpus empties this in the same commit that moves
`CALIBRATION_C`.

**Unanchored is policy, not an oversight.** Under the corpus policy
decided with 2.4.1, a language ships parsed and the corpus is re-measured
once after the remaining scanners land: adding a scanner moves
`scanner_fingerprint` and invalidates every stored measurement, so paying
per language means paying in full, repeatedly, for an anchor that is
obsolete again at the next one.

What is *not* policy is silence about it where the grade is read. The
report carried `score.reference` and the note said the corpus spanned
"every language this scanner parses" — which was true when it was written
and false from 2.4.0 onward, for three releases. A Grok audit on
2026-09-04 named it as the second instance of a shape this project had
already shipped once: a limit disclosed only in JSON is disclosed nowhere
that matters.
"""
from __future__ import annotations

#: Parsed by a scanner, absent from the reference corpus.
#:
#: Stated rather than derived, and the reason still holds:
#: `tools/calibration/corpus.json` is a repository file that does not ship
#: in the wheel, so a runtime read would be unavailable exactly where a
#: user reads a grade. What a stated list buys in availability it owes in
#: upkeep, and it did not pay.
#:
#: **D143.** This read `("Swift", "COBOL", "Go", "Rust", "PHP", "Ruby")`
#: after 3.0.0 anchored five of those six. The corpus grew from 112
#: repositories to 180 and from eight measured languages to thirteen, and
#: this line did not move — so every skin told a Swift, Go, Rust, PHP or
#: Ruby reader their grade was provisional against a corpus that had
#: measured their language for two releases. A caveat that names an
#: anchored language is not a caution, it is a false statement about the
#: evidence, and it undersells the thing the recalibration was for.
#:
#: COBOL stays, and stays alone. It is parsed and deliberately never
#: anchored: GitHub holds one COBOL repository above 500 stars and what is
#: there is curriculum, Java parsers and JavaScript wrappers rather than
#: COBOL codebases, so the corpus policy excludes it permanently rather
#: than temporarily. Emptying this tuple would delete a disclosure that is
#: still true.
#:
#: `tests/test_unanchored_set_matches_corpus.py` recomputes
#: `parsed - corpus` from `DECLARATION_SUFFIXES` and `corpus.json` and
#: fails if this stops matching — including when a language is *added* to
#: the corpus, which is the direction that went unnoticed.
UNANCHORED_LANGUAGES: tuple[str, ...] = ("COBOL",)


def unanchored_names() -> str:
    """The languages, joined for a sentence. Empty when there are none."""
    return " and ".join(UNANCHORED_LANGUAGES)


def unanchored_sentence() -> str:
    """One sentence naming what the anchor omits, for the corpus note."""
    if not UNANCHORED_LANGUAGES:
        return ""
    from ._grammar import agreement

    say = agreement(len(UNANCHORED_LANGUAGES))
    return (
        f"{unanchored_names()} {say.verb} parsed but absent from it, so "
        f"{say.possessive} findings are as good as {say.possessive} "
        f"parser while {say.possessive} grade is provisional."
    )
