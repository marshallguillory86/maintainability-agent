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
#: Stated rather than derived. `tools/calibration/corpus.json` is a
#: repository file and does not ship in the wheel, so a runtime read would
#: be unavailable exactly where a user reads a grade.
#: `test_anchor_disclosure` recomputes `parsed - corpus` from both sources
#: and fails if this stops matching, so the list cannot quietly go stale.
UNANCHORED_LANGUAGES: tuple[str, ...] = ("Swift", "COBOL", "Go", "Rust")


def unanchored_names() -> str:
    """The languages, joined for a sentence. Empty when there are none."""
    return " and ".join(UNANCHORED_LANGUAGES)


def unanchored_sentence() -> str:
    """One sentence naming what the anchor omits, for the corpus note."""
    if not UNANCHORED_LANGUAGES:
        return ""
    return (
        f"{unanchored_names()} are parsed but absent from it, so their "
        "findings are as good as their parser while their grade is "
        "provisional."
    )
