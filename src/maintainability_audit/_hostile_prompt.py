"""ADR 013: seed the hostile audit, never perform it.

This project is built by hostile audits. An adversary reads a change and
tries to make a stated promise false — a symlinked write that escapes the
grant, an empty analyzer run priced as clean, a type check that never ran
reported as a pass — and every accepted finding becomes a
population-derived falsifier that fails without its fix.

That loop is the highest-leverage quality process here and it was the only
one with no artifact. Remediation has `render_ai_prompt`; agent standards
have `render_agent_instructions`. The hostile audit depended on a person
hand-writing a fresh prompt into a fresh session, re-deriving context the
report already holds, with audit quality riding on whoever wrote the
prompt that day. Not repeatable, not seeded, not comparable run to run.

So this is a third emitter on the same seam, and the boundary is the one
ADR 008 already drew:

    The deterministic core **seeds** the hostile audit; it never
    **performs** it.

An LLM red-team inside the audit would break P1 outright — a hostile
result that changes between identical runs is not evidence — so the
adversarial reasoning happens outside, exactly as the fixing does. What
this returns is text: no gate, no score, no report written, nothing sent
anywhere. Findings return to the falsifier-and-fix loop, never to the
estimate, range or grade.
"""

from __future__ import annotations

from typing import Any

#: The published promises and the thing that would falsify each, kept in
#: code so the prompt can name them offline and does not depend on `docs/`
#: being installed beside the package.
#:
#: `tests/test_hostile_prompt.py` holds this table to
#: `docs/product-intent.md` in both directions, because a promise the
#: adversary is handed in a stale wording is worse than one it is not
#: handed at all: it aims the audit at a claim the project no longer makes.
PROMISES: tuple[tuple[str, str, str], ...] = (
    ("P1", "The audit is deterministic: same tree, config, pinned analyzer versions and "
           "scan history in, same evidence, findings and score out, at a fixed point in time",
     "Two runs on one tree disagreeing, or an undisclosed network read"),
    ("P2", "The score applies the same rubric to every repository, and the rubric is "
           "readable in source",
     "A repo-specific code path changing a weight or band"),
    ("P3", "Withholding evidence cannot improve the reported grade",
     "Any input whose removal raises the graded field"),
    ("P4", "`maintainability_estimate` equals the weighted mean of the categories printed "
           "beside it",
     "A report where the arithmetic does not check"),
    ("P5", "The remediation prompt names only findings the audit actually produced",
     "A prompt instruction with no corresponding finding"),
    ("P6", "Every empirical claim in this repo is reproducible from checked-in pinned inputs",
     "A quoted number that cannot be re-derived offline"),
    ("P7", "A score is issued only where enough was examined to support it, and never as a "
           "consequence of not looking",
     "A number a reader with the repository in front of them would call absurd"),
    ("P8", "Every report states what examined it — which analyzers ran, which did not, and "
           "what measured each value",
     "A reported value with no attributable source"),
)

#: The standard these audits already hold themselves to. Writing it into
#: the prompt is the point: an audit that speculates produces a wall of
#: worries, and this project has spent real time refuting stale and false
#: claims from adversaries who were not told the contract.
CONTRACT = (
    "Reproduce, do not speculate. A finding is a concrete input and the wrong output or "
    "crash it produces — not a worry, not a code smell, not a hypothesis.",
    "Verify against the commit named above before reporting. Several past audits of this "
    "project contained claims that were already false at the commit under audit.",
    "Every accepted finding must become a population-derived falsifier: a test that fails "
    "without its fix. If you cannot state the test, you do not yet have the finding.",
    "A real hole and a population-derived claim are different outcomes. Label which you "
    "have; do not present the second as the first.",
    "Absence of evidence is a finding about this tool only when the tool reported it as a "
    "pass. Say which.",
)


def _bullets(items: Any, limit: int = 12) -> list[str]:
    """Short, readable labels — never a stringified structure.

    The first render of this brief pasted the whole `by_outcome` mapping
    into one line: several thousand characters of nested dicts, including
    every language jscpd claims. A brief that buries its own content is
    worse than the hand-written prompt it replaces, so anything
    dict-shaped is reduced to a name here.
    """
    if not items:
        return []
    if isinstance(items, dict):
        return [f"{key}: {_label(value)}" for key, value in list(items.items())[:limit]]
    return [_label(item) for item in list(items)[:limit]]


def _label(value: Any) -> str:
    """A name for one item, whatever shape the report holds it in."""
    if isinstance(value, dict):
        for key in ("tool", "name", "concept", "dimension", "status", "detail"):
            if value.get(key):
                return str(value[key])
        return "?"
    if isinstance(value, (list, tuple)):
        named = [_label(item) for item in value]
        head = ", ".join(named[:6])
        return f"{len(named)} ({head}{', …' if len(named) > 6 else ''})"
    return str(value)


def _scope(report: dict[str, Any]) -> list[str]:
    """Where the audit is pointed, from what the run already knows."""
    lines = []
    commit = report.get("git_commit")
    if commit:
        branch = report.get("git_branch") or "?"
        lines.append(f"- Commit under audit: `{commit}` on `{branch}`")
    dirty = report.get("git_status_short")
    if dirty:
        lines.append(
            "- **The tree is dirty.** Uncommitted changes are in scope and are not in the "
            "commit above, so a finding must say which it is against."
        )
    mode = report.get("mode")
    if mode:
        revspec = report.get("changed_revspec")
        lines.append(f"- Scan mode: `{mode}`" + (f" over `{revspec}`" if revspec else ""))
    lines.append(f"- Report schema: `{report.get('schema_version', '?')}`, "
                 f"generated {report.get('generated_at', '?')}")
    return lines


def _scored(report: dict[str, Any]) -> list[str]:
    """What the run concluded, and what held the grade down."""
    score = report.get("score") or {}
    status = score.get("evidence_status")
    if isinstance(status, dict):
        status = status.get("status", "?")
    lines = [
        f"- Estimate {score.get('maintainability_estimate')} "
        f"(range {score.get('maintainability_range')}), "
        f"verified grade {score.get('verified_grade')!r}, "
        f"evidence {status}",
    ]
    blockers = score.get("verified_grade_blockers")
    if blockers:
        lines.append(f"- Grade blocked by: {'; '.join(_bullets(blockers, 6))}")
    worst = score.get("worst_dimension")
    if worst:
        lines.append(f"- Worst dimension: {worst}")
    return lines


def _analyzer_outcomes(coverage: dict[str, Any]) -> list[str]:
    """Which tools ran, and which did not — one line per outcome."""
    outcomes = coverage.get("by_outcome")
    if not isinstance(outcomes, dict):
        return []
    lines = []
    for outcome, tools in outcomes.items():
        names = [_label(tool) for tool in tools] if isinstance(tools, list) else [_label(tools)]
        shown = ", ".join(names[:10]) + (", …" if len(names) > 10 else "")
        lines.append(f"- Analyzers {outcome}: {len(names)} — {shown}")
    return lines


def _coverage_gaps(coverage: dict[str, Any]) -> list[str]:
    """Where nothing looked, or only one thing did.

    Kept apart from the rest because it is the section that matters most:
    an unmeasured concept is where P7 and P8 are easiest to break, and a
    single-source concept has no second reading to disagree with it.
    """
    lines = []
    unexamined = coverage.get("concepts_unexamined")
    if unexamined:
        lines.append(
            f"- **Concepts nothing measured** ({len(unexamined)}): "
            f"{', '.join(_bullets(unexamined, 10))} — these are where P7 and P8 are "
            "easiest to break"
        )
    single = coverage.get("concepts_single_source")
    if single:
        lines.append(
            f"- Concepts with one source only ({len(single)}): "
            f"{', '.join(_bullets(single, 8))} — no corroboration to disagree with"
        )
    declined = coverage.get("dimensions_declined")
    if declined:
        lines.append(f"- Dimensions declined: {', '.join(_bullets(declined, 8))}")
    return lines


def _measured(report: dict[str, Any]) -> list[str]:
    """The evidence already computed, so the audit starts where it ended.

    An adversary that has to re-derive coverage spends its budget on
    arithmetic the report performed. Handing it over is most of the value.
    """
    coverage = report.get("analyzer_coverage") or {}
    lines = _scored(report)
    lines += _analyzer_outcomes(coverage)
    lines += _coverage_gaps(coverage)

    gates = report.get("hard_gate_failures")
    lines.append(f"- Hard gate failures: {len(gates) if gates else 0}")
    work_order = report.get("environment_work_order")
    if work_order:
        lines.append(
            f"- Selected analyzers that could not run ({len(work_order)}): a tool that did "
            "not run must not read as clean"
        )
    return lines


def render_hostile_audit_prompt(report: dict[str, Any]) -> str:
    """A bounded adversarial brief, deterministic from one report.

    Returns text. It writes nothing, gates nothing and scores nothing.
    """
    out: list[str] = [
        "# Hostile audit brief",
        "",
        "You are auditing a deterministic maintainability tool that publishes falsifiable "
        "promises. Your job is to make one of them false with a reproducible case.",
        "",
        "This brief was emitted by the tool itself from a single audit run, so it is the "
        "same brief for the same inputs. The tool seeds this audit; it does not perform it.",
        "",
        "## Scope",
        "",
        *_scope(report),
        "",
        "## What the run already measured",
        "",
        "Start here rather than re-deriving it.",
        "",
        *_measured(report),
        "",
        "## The promises, and what would falsify each",
        "",
        "Attack a claim, not a preference. Each row is a published promise and the shape "
        "of evidence that breaks it.",
        "",
        "| Promise | Claim | Falsified by |",
        "|---|---|---|",
    ]
    out += [f"| {tag} | {claim} | {falsifier} |" for tag, claim, falsifier in PROMISES]
    out += [
        "",
        "## The audit contract",
        "",
    ]
    out += [f"{index}. {rule}" for index, rule in enumerate(CONTRACT, start=1)]
    out += [
        "",
        "## Report",
        "",
        "For each finding: the promise it breaks, the concrete input, the wrong output, "
        "and the test that would fail without the fix. If nothing falsifies, say so "
        "plainly and name what you tried — a hostile audit that finds nothing is a "
        "result, and inventing a finding to avoid an empty report wastes the loop.",
    ]
    return "\n".join(out)
