"""Every parsed language owes a loop pair (D212).

Covers existing behaviour: this passes at D212's base, because the
fixtures it counts live in the test file and the base keeps `tests/`
from this commit.

It is here because it is the mechanism whose absence let one defect
survive three fixes. Fortran's `do`, Swift's `guard` and PHP's
`foreach` were each found in one language and fixed in that language,
and nothing ever asked whether the other nine had the same hole — so
C#'s `foreach` was sitting in the shared pattern that PHP's own
`foreach` note is printed beside.

A language absent from `LOOPS` is one the cited falsifier says nothing
about, and saying nothing quietly is exactly the failure. This makes
the silence loud.

Kept out of the cited file so its citations stay evidence for D212.
"""

from __future__ import annotations

from test_every_language_counts_its_own_loop import LOOPS

from maintainability_audit.declarations import DECLARATION_SUFFIXES


def test_every_parsed_language_has_a_loop_pair() -> None:
    """Clause two, and the mechanism that let three fixes miss the fourth.

    A language absent from `LOOPS` is one this file says nothing about,
    and saying nothing is exactly how `foreach` sat unmatched in the
    pattern PHP's own `foreach` note is printed beside.
    """
    assert DECLARATION_SUFFIXES, "no parsed suffixes, so this sweeps nothing"
    covered = {
        suffix for suffix in DECLARATION_SUFFIXES
        if suffix in LOOPS
    }

    assert covered, "no parsed suffix has a loop pair"
    # Families, not every spelling: `.hpp` and `.cc` are the same
    # language as `.cpp`. What must hold is that a language whose
    # keywords this tool claims to know has a pair somewhere.
    families = {".cs", ".php", ".java", ".py", ".go", ".rs", ".swift", ".rb", ".js", ".c"}
    missing = sorted(families - covered)

    assert not missing, f"these parsed languages have no loop pair: {missing}"
