"""Is there enough evidence to issue a grade? — ADR 001 stage 5.

Separate from scoring because the two questions are separate. The
rubric answers *what the available evidence estimates*; this answers
*whether enough evidence exists to certify a letter*. Conflating them
is what produced a scale where a shallow clone's missing history read
as demonstrated poor maintainability.

Nothing here changes a score. ``score.overall``, ``score.grade`` and
their neighbours keep their existing meaning and values, including the
evidence-floor grading that makes concealment unprofitable today.
``verified_grade`` is added *alongside* them and is null whenever the
profile's required evidence is not complete. Consumers keep reading the
compatibility fields until ADR 001 stage 7 migrates them deliberately.

The three states carry their full meaning here:

- ``Measured(0)`` is complete evidence. The scanner looked and found
  none, which is a finding, not a gap.
- ``NotApplicable`` is complete evidence. The measurement has no
  population in this repository — nothing is missing.
- ``Unknown`` is the only state that withholds verification.
"""
from __future__ import annotations

from typing import Any

from ._formula import ROOT_POPULATIONS, population_floor
from ._pressures import measured
from .evidence import SCOPE_FULL, NormalizedEvidence, Unknown, walk_evidence

# The named evidence contract a report was verified under. Reports state
# it so that CI, badges and APIs cannot silently compare results issued
# under different requirements — ADR 001 §5.
DEFAULT_PROFILE = "default-v1"

# **The frozen requirement list for that name.** Written out rather than
# derived from the typed model, and the difference is the whole point:
# deriving it meant that adding a field to SummaryEvidence or
# HistoryEvidence silently changed what `default-v1` demanded, so two
# materially different contracts would both call themselves v1 and the
# name would guarantee nothing. An audit caught that, and it is exactly
# the failure a version string exists to prevent.
#
# Adding a scoring input therefore forces a decision, enforced by
# ``test_every_typed_scoring_input_is_classified_by_the_profile``:
# require it under a **new** profile name, or record here that v1 does
# not require it. Editing this set in place changes a published
# contract; that is a v2, not a patch.
DEFAULT_V1_REQUIRED: frozenset[str] = frozenset({
    "summary.files_scanned",
    "summary.declarations_scanned",
    "summary.file_warnings",
    "summary.file_failures",
    "summary.function_warnings",
    "summary.function_failures",
    "summary.duplicate_blocks",
    "summary.risk_findings",
    "summary.hard_gate_failures",
    "summary.production_files_scanned",
    "summary.production_declarations_scanned",
    "summary.production_file_warnings",
    "summary.production_file_failures",
    "summary.production_function_warnings",
    "summary.production_function_failures",
    "summary.production_hard_gate_failures",
    "summary.test_file_count",
    "summary.dead_code_count",
    "summary.near_duplicate_count",
    "summary.idiom_concern_count",
    # Required, and the most load-bearing pair in the list: a report that
    # cannot say what it failed to read cannot be trusted to have read
    # anything. Unknown here means a report predating the field, and the
    # correct response to that is a withheld grade rather than a
    # confident one — the validation sample showed a 4.3 computed from a
    # quarter of curl's source with nothing in the output saying so.
    "summary.unread_source_files",
    "summary.read_source_files",
    # Required for the same reason as the two above: a report that
    # cannot say whether it could parse what it opened cannot be trusted
    # to have measured the population it scored.
    "summary.undetected_declaration_files",
    "summary.has_readme",
    "summary.has_changelog",
    "summary.has_docs_dir",
    "history.files_changed",
    "history.qualifying_hotspots",
    "history.code_coupling_pairs",
    "history.multi_commit_files",
    "history.single_author_files",
    # The 3.2 band pressures. Score-bearing: the band matrix prices a
    # complexity-12 warn above a plain warn, so it can only add pressure
    # over the count rate. Withholding one therefore only improves the
    # score -- the P3 hole Grok's e88b429 audit named -- so an absent band
    # withholds the grade rather than quietly falling back to the coarser
    # count rate. `_pressures._banded` no longer prices an Unknown band at
    # the count rate for the same reason.
    "summary.declaration_band_pressure",
    "summary.production_declaration_band_pressure",
    "summary.file_band_pressure",
    "summary.production_file_band_pressure",
})

# Inputs v1 deliberately does not require. Empty: a scoring input that
# should not withhold a grade is recorded here so the omission is a
# decision on the record rather than a gap.
#
# The four 3.2 band pressures used to live here, on the reasoning that a
# missing band predated the wiring and the count-rate fallback was a
# coarser-but-verifiable number. Grok's e88b429 audit showed that was a
# P3 hole: the band can only add pressure over the count rate, so
# withholding it only ever improved the score, and this list kept the
# concealment sweep from ever noticing. They are now required (above).
DEFAULT_V1_NOT_REQUIRED: frozenset[str] = frozenset()

COMPLETE = "complete"
INCOMPLETE = "incomplete"
# The evidence resolved, but not over a population this scale can speak
# to. Distinct from INCOMPLETE, which means a required measurement was
# never established: here everything was measured and the measuring is
# what does not apply (ADR 005).
INSUFFICIENT = "insufficient"


def verification(evidence: NormalizedEvidence, grade: str) -> dict[str, Any]:
    """``evidence_status`` and ``verified_grade`` for one report.

    ``default-v1`` requires the measurements in
    :data:`DEFAULT_V1_REQUIRED` to be resolved — ``Measured`` or
    ``NotApplicable``. One ``Unknown`` among them makes the status
    incomplete and withholds the verified grade, naming the measurement
    rather than reporting a bare "insufficient evidence".

    Returns the two fields as a mapping so the score document can splat
    them in one place instead of threading two more parameters through
    the rollup.
    """
    scope_reasons = _out_of_scale(evidence)
    if scope_reasons:
        # Scope is checked before completeness because it dominates: a
        # diff with every measurement resolved still cannot carry a
        # whole-repository grade, and reporting "complete" beside a
        # withheld score would read as a contradiction.
        return {
            "evidence_status": {
                "status": INSUFFICIENT,
                "profile": DEFAULT_PROFILE,
                "reasons": scope_reasons,
            },
            "verified_grade": None,
        }
    reasons = _unresolved(evidence)
    complete = not reasons
    return {
        "evidence_status": {
            "status": COMPLETE if complete else INCOMPLETE,
            "profile": DEFAULT_PROFILE,
            "reasons": reasons,
        },
        # Equal to the compatibility grade when the evidence supports
        # one, null when it does not. Never a pessimistic letter: ADR
        # 001 §1 rejects reporting unknown quality as bad quality.
        "verified_grade": grade if complete else None,
    }


def _out_of_scale(evidence: NormalizedEvidence) -> list[dict[str, str]]:
    """Reasons this run cannot carry a whole-repository score.

    The scale is calibrated over whole repositories. A diff is not a
    small repository; it is a different kind of object, so scoring one
    on this scale is a category error rather than a precision problem.
    Before this check a two-file diff of this repository reported
    estimate 4.2 with status "complete" over *zero* declarations, and
    every PR-scoped CI run inherited it.
    """
    # Checked before the population floors, because it explains them. A
    # Java repository reads as "0 declarations, below the floor of 139",
    # which sends the reader to look for more code when the code is
    # already there and simply was not opened. The true cause has to be
    # the reason printed, or the remedy is wrong.
    unread = _unread_source(evidence)
    if unread:
        return unread
    # Before the floors for the same reason unread source is: it
    # explains them. A repository whose language has no declaration
    # parser reports "0 declarations, below the floor of 139", which
    # tells a reader with forty files that their repository is too
    # small. The cause has to be the reason printed, or the remedy is
    # wrong — and here the remedy was "no re-scan will change that".
    blind = _no_declaration_parser(evidence)
    if blind:
        return blind
    thin = _below_root_floor(evidence)
    if thin:
        return thin
    if evidence.scope == SCOPE_FULL:
        return []
    return [{
        "measurement": "scan.scope",
        # States the fact only. What to do about it is one place --
        # `_evidence_view.remedy` -- so advice cannot drift from the cause,
        # and a reason plus a remedy do not read as the same sentence twice.
        "reason": (
            f"scan scope is {evidence.scope}, not a whole repository, and the scale "
            "is calibrated over whole repositories"
        ),
        # Same shape as every other reason, so consumers need no special
        # case: a reason without provenance sends the reader hunting.
        "provenance": "report.mode",
    }]


# The share of a repository's source that may go unread before a score
# stops describing the repository. A judgment, stated rather than buried:
# below this, the unread files are a fringe — a stray shell script in a
# Python project — and naming them is enough. At or above it, the score
# is drawn from a minority of the code while being presented as a
# statement about all of it.
#
# Set from the validation sample, where the failures were not marginal:
# curl read 25% of its source, whisper.cpp 23%, gson and ripgrep 0%. A
# tighter threshold would withhold scores from healthy polyglot
# repositories; a looser one would have let curl through.
MAX_UNREAD_SHARE = 0.20


def _unread_source(evidence: NormalizedEvidence) -> list[dict[str, str]]:
    """Source files that exist, that this scan never opened.

    The most complete form of the defect this project exists to remove.
    Every earlier instance was a *count* that was absent and read as
    zero; this is the **population** being absent — code present in the
    tree, invisible to `include_extensions`, and silently outside the
    number the report prints.

    Measured, not hypothesised: curl reported 4.3 computed from 1,041
    declarations of Markdown and Python test scripts while lizard, in the
    same report, measured 20,547 declarations of the C nobody read.
    """
    unread = measured(evidence.summary.unread_source_files)
    read = measured(evidence.summary.read_source_files)
    if unread is None or read is None or unread == 0:
        # Unknown here means a report that predates this field, not a
        # clean tree. It cannot be treated as evidence either way, and
        # `build_report` always stamps it — see
        # `test_every_report_states_what_it_could_not_read`.
        return []

    total = unread + read
    share = unread / total if total else 1.0
    if share < MAX_UNREAD_SHARE:
        return []
    return [{
        "measurement": "summary.unread_source_files",
        # The fact only. Which extensions, and what to do about them,
        # come from `summary.unread_source` through `_evidence_view` —
        # naming them here too would put the same fact in two places that
        # can disagree, which is the companion-flag defect the evidence
        # model forbids.
        "reason": (
            f"{int(unread)} of {int(total)} source files ({share:.0%}) were not read: "
            "their extensions are absent from paths.include_extensions, so no score "
            "drawn from this tree describes the repository"
        ),
        "provenance": "summary.unread_source",
    }]


def _no_declaration_parser(evidence: NormalizedEvidence) -> list[dict[str, str]]:
    """Files were read, and nothing could parse declarations out of them.

    Fires only where the declarations floor would otherwise fire: a tree
    with plenty of Python and a handful of Go still has a real
    declaration population, and saying "no parser" there would be a
    warning about nothing.

    The reason names the *cause* and points at `summary.
    undetected_declarations` for the extensions rather than restating
    them. Two copies of one list drift, which is why `_unread_source`
    refuses to restate its own list too.
    """
    blind = measured(evidence.summary.undetected_declaration_files)
    declarations = measured(evidence.summary.declarations_scanned)
    floor = population_floor("declarations_scanned")
    if not blind or declarations is None or floor is None or declarations >= floor:
        return []
    return [{
        "measurement": "summary.undetected_declaration_files",
        "reason": (
            f"{int(blind)} scanned files are in a language this tool has no "
            "declaration parser for, so it measured their length, duplication "
            "and risk but found no functions or classes in them. The "
            "declaration population is empty because nothing could read it, "
            "not because the repository is small"
        ),
        "provenance": "summary.undetected_declarations",
    }]


def _below_root_floor(evidence: NormalizedEvidence) -> list[dict[str, str]]:
    """Populations too small for anything drawn from this tree to mean something.

    Gated at the root rather than per aspect because the history rates
    describe the same codebase: "0 hotspots over 5 changed files" is no
    more informative than "0 dead code over 1 declaration". A repository
    with one production function and one test reported 5.0/A+ with every
    count genuinely zero, and per-aspect floors alone left it scoring on
    the history aspects that have no corpus-derived floor.
    """
    reasons: list[dict[str, str]] = []
    for population in ROOT_POPULATIONS:
        floor = population_floor(population)
        observed = measured(getattr(evidence.summary, population))
        if floor is None or observed is None or observed >= floor:
            continue
        reasons.append({
            "measurement": f"summary.{population}",
            # Built from the floor table rather than written out: an
            # earlier version restated the corpus minima in prose and went
            # stale the moment a floor was corrected.
            "reason": (
                f"{int(observed)} is below the calibration floor of {floor} for "
                f"{population}, so no rate drawn from this tree is supported"
            ),
            "provenance": f"summary.{population}",
        })
    return reasons


def _unresolved(evidence: NormalizedEvidence) -> list[dict[str, str]]:
    """Every required measurement the report could not establish.

    Only measurements the profile requires. Sorted by measurement path:
    a report diffed against another must not show spurious reordering.
    """
    return sorted(
        (
            {
                "measurement": path,
                "reason": state.reason,
                "provenance": state.provenance,
            }
            for path, state in walk_evidence(evidence)
            if path in DEFAULT_V1_REQUIRED and isinstance(state, Unknown)
        ),
        key=lambda reason: reason["measurement"],
    )
