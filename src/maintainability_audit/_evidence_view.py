"""How the four score concepts are phrased, in one place.

ADR 001 stage 7. Four separate things reach a reader — the
maintainability *estimate*, its *range*, whether the *evidence* is
complete, and the *verified grade* — and before this stage every
consumer either ignored the last two or would have had to interpret
them itself. Four independent interpretations of "what does null mean"
is four chances to imply a repository was graded when it was not.

This module owns the wording and nothing else. It reads the public
report dictionary, computes no score, infers no status, and imports
nothing from the scoring layer: the score object stays the sole source
of the estimate, the range, the compatibility grade, the evidence
status and the verified grade.

The one rule every phrasing here obeys: **a null verified grade is
never rendered as a letter, a dash, or a blank.** Each of those reads
as a result, and the point of the field is that no result was issued.

Since ADR 001 stage 8 there is no second letter to fall back to. The
compatibility grade is gone from the contract, so a report either
carries a verified grade or carries none, and this module has no
fallback interpretation to apply. A score dictionary missing the
canonical fields is malformed and raises rather than being handed
compatibility semantics.
"""
from __future__ import annotations

from typing import Any

NOT_VERIFIED = "Not verified"
# One phrase for "no number was issued", used wherever a number would
# otherwise go. Never a dash and never a zero: both read as a value, and
# a reader scanning a table cannot tell a withheld score from a bad one.
NO_SCORE = "Not scored"


def is_scored(score: dict[str, Any]) -> bool:
    """Whether this run produced a number at all.

    Consults the estimate rather than the status so a consumer cannot
    render a number the scorer withheld, whatever new status values
    arrive later.
    """
    return score.get("maintainability_estimate") is not None


def estimate(score: dict[str, Any]) -> str:
    """The point estimate, always labelled as an estimate."""
    if not is_scored(score):
        return NO_SCORE
    return f"{score['maintainability_estimate']} / 5"


def score_range(score: dict[str, Any]) -> str:
    """The interval, and what a collapsed one actually means.

    Equal bounds do **not** establish complete evidence. The endpoints
    are rounded to one decimal, so concealing a lightly-weighted
    measurement can leave them coincident while the evidence is
    genuinely incomplete — an audit reproduced `[4.9, 4.9]` rendered as
    "no unmeasured evidence" on a report whose verified grade had been
    withheld. Completeness is a property of the typed evidence, never of
    two numbers that happen to match after rounding, so this consults
    the status rather than inferring it.
    """
    interval = score["maintainability_range"]
    if interval is None:
        return NO_SCORE
    low, high = interval
    if low != high:
        return f"{low} – {high}"
    if is_complete(score):
        return f"{low} (no unmeasured evidence)"
    return f"{low} (bounds coincide after rounding; evidence is still incomplete)"


def is_complete(score: dict[str, Any]) -> bool:
    return score["evidence_status"]["status"] == "complete"


def profile(score: dict[str, Any]) -> str:
    return score["evidence_status"]["profile"]


def estimate_source(score: dict[str, Any]) -> str:
    """What produced the number above — P8, stated in every skin.

    One helper so Markdown and HTML cannot drift into two answers about
    the same score. Reads `analyzer_scored_dimensions`, which the scorer
    records; "analyzer output exists" is a different claim from
    "analyzer output set this number".
    """
    scored = score.get("analyzer_scored_dimensions") or []
    if scored:
        return (f"Analyzer readings for {', '.join(scored)}; "
                "built-in detectors for remaining dimensions")
    return "Built-in detectors (fallback tier)"


def verified_grade(score: dict[str, Any]) -> str:
    """The verified grade, or the words that mean there isn't one."""
    return score["verified_grade"] or NOT_VERIFIED


def reasons(score: dict[str, Any]) -> list[dict[str, str]]:
    return list(score["evidence_status"]["reasons"])


def grade_blockers(score: dict[str, Any]) -> list[str]:
    """Why an *issued* grade is not higher.

    Empty whenever no grade was issued: there is nothing to cap. What is
    missing is explained by :func:`reasons` instead, and conflating the
    two is what let an evidence gap read as a quality demotion.
    """
    return list(score["verified_grade_blockers"])


def is_insufficient(score: dict[str, Any]) -> bool:
    return score["evidence_status"]["status"] == "insufficient"


# What to do about a withheld score depends on which situation you are in,
# and a bare "insufficient" leaves the reader unable to tell. ADR 005 names
# three, and they are not workarounds for each other.
WIDEN_THE_SCAN = (
    "The population exists but this scan did not look at it. Re-run over the "
    "whole repository for a comparable score."
)
READ_THE_SOURCE = (
    "The repository's source is present but this scan never opened it: those "
    "file extensions are not in `paths.include_extensions`. Add them and re-run "
    "for a score that describes this codebase. Until then the findings below "
    "come only from the files that were read."
)
# Two variants, chosen by whether the analyzer pool ran (D1): telling a
# configured repository to enable the pool it already ran is a lie, and
# the honest remedy there is the missing parser or tool.
NO_DECLARATION_PARSER_POOL_OFF = (
    "These files were read — their length, duplication and risk are measured — "
    "but this tool has no declaration parser for their language, so it found no "
    "functions or classes to draw a rate from. Adding the extension to "
    "`paths.include_extensions` will not change that, and the repository is not "
    "too small. Enable the analyzer pool (`analyzers.run` in the config, or "
    "`--analyzers` for one run) for located findings from tools that do read "
    "these languages; the rates stay withheld until a parser exists."
)
NO_DECLARATION_PARSER_POOL_RAN = (
    "These files were read — their length, duplication and risk are measured — "
    "but this tool has no declaration parser for their language, so it found no "
    "functions or classes to draw a rate from. The analyzer pool already ran; "
    "what is missing is a declaration parser or an installed tool for these "
    "languages — the environment work order lists the install commands. The "
    "rates stay withheld until one exists."
)
TAKE_THE_FINDINGS = (
    "This repository is smaller than anything the scale was calibrated on, and "
    "no re-scan will change that. The audit is complete: every finding and every "
    "work item below is real and actionable. Only the rates are withheld."
)


def remedy(score: dict[str, Any], pool_ran: bool = False) -> str:
    """Which of ADR 005's three paths applies to this report.

    Chosen from the reason's measurement rather than from prose, so the
    advice cannot drift from what actually withheld the score.
    ``pool_ran`` is whether the analyzer pool executed for this report
    (coverage present), threaded in by the renderer: the no-parser
    remedy must not prescribe enabling a pool that already ran (D1).
    """
    measurements = {item["measurement"] for item in reasons(score)}
    # Checked first: unread source explains a thin population, so
    # "this repository is too small" would be the wrong advice for a
    # repository whose code is simply unreadable to this configuration.
    if "summary.unread_source_files" in measurements:
        return READ_THE_SOURCE
    # Before the size advice, and distinct from it: "add the extension"
    # is wrong because it is already added, and "too small" is wrong
    # because the files are there and unparseable.
    if "summary.undetected_declaration_files" in measurements:
        return NO_DECLARATION_PARSER_POOL_RAN if pool_ran else NO_DECLARATION_PARSER_POOL_OFF
    if "scan.scope" in measurements:
        return WIDEN_THE_SCAN
    return TAKE_THE_FINDINGS


def status_sentence(score: dict[str, Any], pool_ran: bool = False) -> str:
    """One line a human can act on, for any state."""
    if is_insufficient(score):
        # The remedy is the message here: the reader's next action is to
        # widen the scan or to read the findings, not to restore evidence.
        detail = reasons(score)
        why = detail[0]["reason"] if detail else "the scan cannot support a score"
        return f"No score issued — {why}. {remedy(score, pool_ran)}"
    if is_complete(score):
        return f"Evidence complete under profile `{profile(score)}`."
    missing = len(reasons(score))
    measurement = "measurement" if missing == 1 else "measurements"
    return (
        f"Evidence incomplete under profile `{profile(score)}`: "
        f"{missing} required {measurement} unavailable, so no verified grade was issued."
    )


def reason_lines(score: dict[str, Any], bullet: str = "- ") -> list[str]:
    """Each unavailable measurement, with its typed path and provenance.

    Provenance is included rather than summarised: "history is missing"
    sends someone hunting, `history.files_changed` tells them exactly
    which measurement to restore.
    """
    return [
        f"{bullet}`{item['measurement']}` — {item['reason']} (provenance: `{item['provenance']}`)"
        for item in reasons(score)
    ]


def remediation_note(score: dict[str, Any], pool_ran: bool = False) -> list[str]:
    """What an agent should do about incomplete evidence: not refactor.

    Missing evidence is not a maintainability defect in the source, and
    an agent told about it without this instruction will try to fix the
    code. The work order stays bounded to real findings; restoring the
    evidence is a separate, usually one-line, change to how the audit
    was invoked.
    """
    if is_complete(score):
        return []
    return [
        "",
        "### Evidence",
        "",
        status_sentence(score, pool_ran),
        "",
        *reason_lines(score),
        "",
        "**This is not a code defect and must not widen the work order.** Do not refactor,",
        "add abstractions, or change behaviour in response to it.",
        _restore_hint(score),
        "Fix only the findings listed elsewhere in this prompt.",
    ]


def instruction_note(score: dict[str, Any]) -> list[str]:
    """The don't-widen guard, in the compact form the instructions use.

    The agent-instruction file is a bullet list, not prose, so it takes
    the same rule as the remediation prompt without the heading. An
    audit found this consumer showing only the grade value while
    claiming the whole contract was migrated.
    """
    if is_complete(score):
        return []
    return [
        "- Missing evidence is **not** a code defect: do not refactor or widen scope for it. "
        + _restore_hint(score),
    ]


def _restore_hint(score: dict[str, Any]) -> str:
    """Advice that matches what is actually missing.

    The first version told every incomplete report to check its clone
    depth, including one whose only missing measurement was
    `summary.test_file_count` — naming a summary input and then
    recommending a fix to git history. An audit caught it. Guidance now
    follows the measurement paths.
    """
    sections = {item["measurement"].split(".", 1)[0] for item in reasons(score)}
    if sections == {"history"}:
        return (
            "Every missing measurement is from git history, which usually means the audit "
            "ran on a shallow clone — `actions/checkout` defaults to `fetch-depth: 1`. "
            "Rerun with full history, or report that it is unavailable."
        )
    if sections == {"summary"}:
        return (
            "The missing measurements are scanner outputs, not history. Something upstream "
            "did not report them: check that the audit ran over the whole tree and that the "
            "report was not filtered or hand-edited before scoring."
        )
    return (
        "The missing measurements come from more than one producer; see the paths above. "
        "Restore the inputs they name and rerun the audit rather than changing code."
    )


def unidentified_paths_markdown(paths: list[str]) -> list[str]:
    """Refused path identifications, on the surface people read (audit M2).

    A finding whose path matched zero or several tree files keeps the
    tool's own spelling; a reader following it to a file that does not
    exist deserves the refusal stated where they are looking, not only
    in the JSON.
    """
    if not paths:
        return []
    lines = [
        "### Unidentified source paths", "",
        "These tool-reported paths matched zero or several files in the "
        "tree, so their identification was refused and the tool's own "
        "spelling was kept:", "",
    ]
    lines.extend(f"- `{path}`" for path in paths)
    lines.append("")
    return lines


def test_suite_lines(block: dict[str, Any] | None) -> list[str]:
    """Skin-agnostic sentences describing the opted-in suite run.

    Empty on the default path (no opt-in, no ``test_suite`` block), so the
    section is absent from a report that never ran the tree. When it did
    run, both skins render these same sentences, so a failed suite reads
    as failed everywhere rather than being silently indistinguishable from
    a pass — the report states what examined ``test_effectiveness`` (P8),
    which is the suite named here.
    """
    if not block:
        return []
    command = " ".join(block.get("command") or []) or "(unset)"
    if block.get("ran"):
        outcome = "passed" if block.get("passed") else f"failed (exit {block.get('exit_code')})"
    else:
        outcome = f"did not run (exit {block.get('exit_code')})"
    coverage = block.get("coverage_percent")
    coverage_text = (
        f"{coverage}% line coverage" if coverage is not None
        else "no coverage reported by the run"
    )
    lines = [
        f"The operator opted in to running the repository's test command; it {outcome}.",
        f"Command: {command}",
        f"Coverage: {coverage_text}",
    ]
    detail = (block.get("detail") or "").strip()
    if detail and not block.get("passed"):
        lines.append(f"Detail: {detail}")
    return lines
