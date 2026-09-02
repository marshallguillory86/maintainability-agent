"""License names, normalized and classified.

Split out of ``build_catalog.py`` in 1.6.0, which had crossed this
project's 500-line file gate — the same reason ``_config_defaults`` came
out of ``config``.

One concern, and a self-contained one: turning whatever string an
upstream inventory recorded into a status and a class this project's
license policy can act on. ``build_catalog`` re-exports both entry
points, so every existing caller is unchanged.
"""

from __future__ import annotations

PROPRIETARY = {"proprietary", "commercial"}
UNVERIFIABLE = {"other", "unknown", "", "noassertion", "custom"}

_SOURCE_AVAILABLE = (
    "elastic license", "business source", "sustainable use",
    "android software development kit",
)
_STRONG_COPYLEFT = (
    "agpl", "affero", "gpl-3", "gpl v3", "gpl-2", "gpl v2", "gplv2", "gplv3",
    "general public license", "gnu gpl", "gnu public license", "cc-by-sa",
    "european union public license", "eupl", "gpl",
)
_WEAK_COPYLEFT = ("lgpl", "lesser general public", "mozilla public", "mpl-", "eclipse public", "cddl")
_PERMISSIVE = (
    "mit", "bsd", "apache", "isc", "zlib", "boost", "bsl-1.0", "upl",
    "postgresql license", "artistic", "uiuc", "llvm release", "ncsa",
    "unlicense", "cc0", "wtfpl", "python software foundation",
)


_DUAL_SEPARATORS = (" / ", "/", " or ", ", ", " & ", " + ")


_PERMISSIVE = (
    "mit", "bsd", "apache", "isc", "zlib", "boost", "bsl-1.0", "upl",
    "postgresql license", "artistic", "uiuc", "llvm release", "ncsa",
    "unlicense", "cc0", "wtfpl", "python software foundation",
)


_WEAK_COPYLEFT = ("lgpl", "lesser general public", "mozilla public", "mpl-", "eclipse public", "cddl")
_PERMISSIVE = (
    "mit", "bsd", "apache", "isc", "zlib", "boost", "bsl-1.0", "upl",
    "postgresql license", "artistic", "uiuc", "llvm release", "ncsa",
    "unlicense", "cc0", "wtfpl", "python software foundation",
)


_STRONG_COPYLEFT = (
    "agpl", "affero", "gpl-3", "gpl v3", "gpl-2", "gpl v2", "gplv2", "gplv3",
    "general public license", "gnu gpl", "gnu public license", "cc-by-sa",
    "european union public license", "eupl", "gpl",
)
_WEAK_COPYLEFT = ("lgpl", "lesser general public", "mozilla public", "mpl-", "eclipse public", "cddl")
_PERMISSIVE = (
    "mit", "bsd", "apache", "isc", "zlib", "boost", "bsl-1.0", "upl",
    "postgresql license", "artistic", "uiuc", "llvm release", "ncsa",
    "unlicense", "cc0", "wtfpl", "python software foundation",
)


def _split_dual(low: str) -> list[str]:
    for separator in _DUAL_SEPARATORS:
        if separator in low:
            return [part.strip() for part in low.split(separator) if part.strip()]
    return [low]


def _single_class(low: str) -> str:
    """The class of one license name, with no dual-license handling."""
    if any(token in low for token in _SOURCE_AVAILABLE):
        return "source-available"
    if any(token in low for token in _WEAK_COPYLEFT):
        return "weak-copyleft"
    if any(token in low for token in _STRONG_COPYLEFT):
        return "strong-copyleft"
    if any(token in low for token in _PERMISSIVE):
        return "permissive"
    return "unverified"


def classify_license(name: str, status: str) -> str:
    """Map a license string to a policy class. Unmatched means unmatched.

    Split into three because the audit flagged this at complexity 19
    against a limit of 15 — the ladder of token tests and the
    dual-license resolution are separate jobs that happened to share a
    function.
    """
    if status in {"proprietary", "unverified"}:
        return status
    low = name.lower()
    if any(token in low for token in _SOURCE_AVAILABLE):
        return "source-available"

    # A dual license gives the licensee the choice, so it takes the most
    # permissive class on offer.
    parts = _split_dual(low)
    if len(parts) > 1:
        classes = {_single_class(part) for part in parts}
        for best in ("permissive", "weak-copyleft", "strong-copyleft"):
            if best in classes:
                return best
        return "unverified"
    return _single_class(low)


# What a tool actually measures, in this project's own vocabulary. The upstream
# database cannot supply this: its tags are languages, ecosystems and frameworks
# (rails, nodejs, spring), and 443 of the 448 eligible tools carry no concern tag
# at all. A concern can only be assigned by running the tool and seeing what it
# emits, so this map grows exactly as fast as the adapters do.
#
# The vocabulary is the scoring model's, not an invented one, so a user's answer
# to "what do you care about?" maps onto aspects that actually exist.
CONCERNS = (
    "complexity",     # cyclomatic, cognitive, nesting, declaration size
    "duplication",    # exact and near clones
    "dead-code",      # unreachable or unreferenced
    "documentation",  # docstring and comment coverage
    "structure",      # file size, coupling, cohesion, dependency shape
    "testing",        # test presence, coverage, mutation
    "style",          # naming and convention conformance
    "types",          # type coverage and soundness
    "metrics",        # maintainability index, Halstead, raw counts
)

# Tools that actually have an adapter in this package. VERIFIED_TIERS
# is "we ran it and assigned a depth"; an adapter is whether we can
# invoke and parse it. Those sets used to be the same, which marked
# flake8, cohesion, cloc and wily implemented with no class in src/ —
# flake8 and cohesion have since earned real ones (2.7); cloc and wily
# have not.


def normalize_license(raw: str) -> tuple[str, str]:
    """Return (status, normalized name). Never guesses."""
    text = str(raw or "").strip()
    low = text.lower()
    if low in UNVERIFIABLE:
        return "unverified", text or "(none stated)"
    if low in PROPRIETARY:
        return "proprietary", text
    if any(token in low for token in _SOURCE_AVAILABLE):
        return "source-available", text
    return "foss", text
