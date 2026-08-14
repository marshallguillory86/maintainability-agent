"""What docs/architecture.md and docs/decisions.md claim, against the tree.

The layering rules live in ``test_architecture``; these are their
mirror image. That file asks whether the import graph matches the
document. This one asks whether the document's *claims* are true —
that a module it calls missing is missing, that a defect it calls
current is current, that a design point it calls embodied is one
something actually imports.

Both halves were one file until it passed this project's own 500-line
limit, the same seam `_adapters` split on. They separate cleanly
because they read different things: imports there, prose here.

Each rule was bought by a specific false sentence; the docstrings say
which.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "maintainability_audit"


# The as-is document once listed shipped modules as unimplemented while
# the layering test still passed: a name appearing *anywhere* satisfied
# it, including a Known-debt sentence that said the file did not exist.
# The proposal section at the end may name future work; everything
# above it may not deny a file that is in the tree.
_PROPOSAL_HEADING = "## Proposed extension boundaries"
_MODULE_DENIAL = re.compile(
    r"(do not exist|does not exist|did not exist|"
    r"unimplemented|not shipped|never created|"
    r"were never created|was never created|"
    r"does not ship|do not ship)",
    re.I,
)
_BACKTICK_NAME = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`")
_KNOWN_DEBT_SECTION = re.compile(r"^## Known debt\n(.*?)(?=^## )", re.S | re.M)
# Phrases that were true of an earlier tree and are now false. Mentioning
# them as *resolved* ("no longer", strikethrough) is fine; asserting them
# as current debt is the class of lie this file existed to stop.
_RESOLVED_AS_CURRENT = (
    (re.compile(r"today nothing records", re.I),
     "scans append through _scan_history"),
    (re.compile(r"finding identity is line-coupled", re.I),
     "identity is function:{path}:{name}#{ordinal} in _identity"),
    (re.compile(r"function:\{path\}:\{name\}:\{start_line\}"),
     "line-coupled identity format is gone"),
    (re.compile(r"ten modules do not exist", re.I),
     "the named modules mostly shipped under other names"),
    (re.compile(r"ADR 00[5-9].{0,20}unimplemented", re.I),
     "005-009 landed in code; remaining gaps are listed as specific debt"),
)


def _asis_architecture(text: str) -> str:
    idx = text.find(_PROPOSAL_HEADING)
    return text if idx < 0 else text[:idx]


def test_architecture_doc_does_not_deny_modules_that_exist() -> None:
    """A claim that a module does not exist must be true of the tree.

    Inverse of ``test_the_documented_layering_matches_the_document``.
    Only names in the clause that carries the denial are checked, so a
    Known-debt sentence can say ``_analyzers`` was never created and
    then name the files that absorbed the role.
    """
    text = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    asis = _asis_architecture(text)
    offenders: list[str] = []
    for match in _MODULE_DENIAL.finditer(asis):
        window = asis[max(0, match.start() - 160):match.end()]
        for name in _BACKTICK_NAME.findall(window):
            py = PACKAGE / f"{name}.py"
            pkg = PACKAGE / name
            if py.exists() or pkg.is_dir():
                located = py if py.exists() else pkg
                offenders.append(
                    f"{name} is denied but {located.relative_to(ROOT)} exists:\n"
                    f"  {window.strip()[:220]}"
                )

    assert not offenders, (
        "docs/architecture.md denies modules that exist:\n" + "\n".join(offenders)
    )


def test_architecture_known_debt_does_not_reassert_resolved_defects() -> None:
    """Live Known-debt bullets may not resurrect defects that already shipped."""
    text = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    match = _KNOWN_DEBT_SECTION.search(text)
    assert match, "docs/architecture.md is missing a Known debt section"
    live = "\n".join(
        line
        for line in match.group(1).splitlines()
        if not line.lstrip().startswith(("~~", "- ~~"))
        and "no longer" not in line.lower()
    )
    offenders = [
        f"{reason}: /{pattern.pattern}/ matched live Known debt"
        for pattern, reason in _RESOLVED_AS_CURRENT
        if pattern.search(live)
    ]

    assert not offenders, (
        "docs/architecture.md Known debt reasserts resolved defects:\n"
        + "\n".join(offenders)
    )


ALLOWED_SPAWN = {"_runner", "git_tools", "_backfill"}


def test_only_documented_modules_spawn_processes() -> None:
    """Rule 7: analyzers go through `_runner`; git is `git_tools` and `_backfill`."""
    offenders = [
        path.name
        for path in sorted(PACKAGE.glob("*.py"))
        if path.stem not in ALLOWED_SPAWN
        and re.search(r"\bsubprocess\b", path.read_text(encoding="utf-8"))
    ]

    assert not offenders, (
        "modules outside rule 7 import subprocess: "
        f"{offenders}; add them to the architecture rule or route through "
        f"{sorted(ALLOWED_SPAWN)}"
    )


# ---------------------------------------------------------------------------
# A shipped module that nothing imports is not an embodied design point
# ---------------------------------------------------------------------------

_KNOWN_DEBT_HEADING = "## Known debt"

# Claims that are true only once `_bands` actually drives a pressure.
# Checked as live prose: the labelled Known debt section may describe the
# unused module, and the proposal section may describe future work.
_BAND_CLAIMS = (
    "band matrix instead of binary thresholds",
    "bands drive the score",
)


def _bands_is_used_by_production() -> bool:
    """Whether any shipped module other than `_bands` imports it."""
    for path in PACKAGE.glob("*.py"):
        if path.name == "_bands.py":
            continue
        source = path.read_text(encoding="utf-8")
        if re.search(r"from \._bands\b|\bimport _bands\b", source):
            return True
    return False


def _live_architecture_prose(text: str) -> str:
    """The as-is body with the Known debt section removed.

    Known debt is where an unshipped design point is *supposed* to be
    described, so scanning it for the same phrases would forbid the
    honest sentence along with the dishonest one.
    """
    asis = _asis_architecture(text)
    debt = asis.find(_KNOWN_DEBT_HEADING)
    if debt < 0:
        return asis
    end = asis.find("\n## ", debt + 1)
    return asis[:debt] + ("" if end < 0 else asis[end:])


def test_architecture_does_not_claim_bands_drive_the_score_while_unused() -> None:
    """`_bands.py` shipped, `tests/test_bands.py` passes, nothing imports it.

    The embodied table read "Band matrix instead of binary thresholds"
    as current fact while `_pressures._weighted_rate` still computed a
    binary warn/fail rate — so CCN 16 and CCN 45 were one failure each,
    which is precisely the severity the matrix was written to keep.

    A module that exists and is never called is not an embodied design
    point; it is an intention with a file. This gate lifts itself the
    day scoring imports `_bands`, so the sentence becomes sayable
    exactly when it becomes true.
    """
    if _bands_is_used_by_production():
        return

    text = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    live = _live_architecture_prose(text).lower()
    offenders = [claim for claim in _BAND_CLAIMS if claim in live]

    assert not offenders, (
        "docs/architecture.md states as current fact: "
        f"{offenders}. No module under src/ imports `_bands`, and the score "
        "is still a binary warn/fail rate. Move the claim to Known debt or "
        "the proposal section until scoring actually consumes the table."
    )


def test_the_register_does_not_call_adr_008_done_while_bands_is_unused() -> None:
    """The same lie, one document over.

    The register said ADR 008 was implemented with no remaining gap. The
    translation layer, the LLM boundary, the entry points and the work
    order all landed; the band matrix did not, and a status cell that
    hides the one part that did not ship is a second status source
    disagreeing with the code.
    """
    if _bands_is_used_by_production():
        return

    register = (ROOT / "docs" / "decisions.md").read_text(encoding="utf-8")
    row = next(
        (line for line in register.splitlines()
         if line.startswith("| [008]")),
        "",
    )
    assert row, "ADR 008 has no row in the register"

    if "implemented" not in row.lower():
        return
    assert any(token in row.lower() for token in ("band matrix", "_bands", "binary")), (
        "the register calls ADR 008 implemented without naming the band "
        f"matrix gap. Row: {row}"
    )
