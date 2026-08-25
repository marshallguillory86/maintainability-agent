"""The MCP audit tool itself: authorization, execution, and the loop record.

Split out of ``mcp_server`` (which keeps transport assembly — bindings,
resources, prompts) when that file crossed the repository's own size
warn line. This module owns everything a single ``audit_repository``
call does: path authorization, the D1 tri-states, first-run degradation,
and — since D5/D6 — the durable remediation loop: an audit that records
its scan and the advice it delivered, then reads the series back into
``scan_history`` and ``design_review_candidates`` exactly as the CLI
does. One helper serves both entry points so the two can never disagree
about the same history file.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from ._calibration import CALIBRATION_C
from ._mcp_gate import _gate
from ._recurrence import escalations
from ._scan_history import (
    DEFAULT_HISTORY_PATH,
    append_scan,
    read_history,
    record_of,
    segments,
)
from ._trends import trend_report
from ._user_config import load_user_config, mark_repo_seen
from ._work_order import prompt_targets
from .baseline import finding_fingerprints
from .config import (
    VERSION,
    analyzers_run_default,
    discovered_config,
    load_config,
    repository_path,
)
from .config import PathNotAllowed as PathNotAllowed  # noqa: PLC0414 - re-export
from .git_tools import changed_paths, run_git
from .prompts import render_ai_prompt
from .renderers import render_markdown
from .report import build_report

ALLOWED_ROOTS_ENV = "MAINTAINABILITY_MCP_ALLOWED_ROOTS"


class InvalidAuditArgument(ValueError):
    """An argument this seam rejected before any audit began.

    Named so the transport can tell the refusals it makes on purpose
    from a `ValueError` raised somewhere below it. `_formula`,
    `_jvm_adapters` and others raise bare `ValueError`s whose messages
    name internal state and file paths; those must stay crashes, whose
    text the SDK withholds. A `ValueError` subclass keeps every existing
    caller — the CLI and the tests that match on `ValueError` — working
    unchanged.
    """


DEFAULT_BASELINE_PATH = ".maintainability/baseline.json"
_REVSPEC = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/@^~:+-]*(?:\.{2,3}[A-Za-z0-9._/@^~:+-]+)?")

def _resolved(path: str | Path, *, relative_to: Path | None = None) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute() and relative_to is not None:
        candidate = relative_to / candidate
    return candidate.resolve()


def allowed_roots(explicit: tuple[str, ...] = ()) -> tuple[Path, ...]:
    """Resolve the server allow-list once, defaulting to its launch directory.

    "Always" grants the user made through the D10 elicitation live in
    the user-tier config and join whatever the launch configured — a
    standing grant must survive a restart, which launch flags alone
    cannot promise.
    """
    configured = explicit or tuple(filter(None, os.environ.get(ALLOWED_ROOTS_ENV, "").split(os.pathsep)))
    roots = configured or (str(Path.cwd()),)
    return tuple(_resolved(root) for root in (*roots, *_persisted_root_grants()))


def _persisted_root_grants() -> tuple[str, ...]:
    grants = (load_user_config() or {}).get("allowed_roots")
    return tuple(str(entry) for entry in grants) if isinstance(grants, list) else ()


def _inside(path: Path, roots: tuple[Path, ...]) -> bool:
    return any(path == root or path.is_relative_to(root) for root in roots)


def authorize_repository(repository_root: str, roots: tuple[Path, ...]) -> Path:
    root = _resolved(repository_root)
    if not root.is_dir():
        raise InvalidAuditArgument(f"repository_root is not a directory: {root}")
    if not _inside(root, roots):
        allowed = ", ".join(str(item) for item in roots)
        raise PathNotAllowed(
            f"repository_root {root} is outside allowed roots: {allowed}. "
            f"Grant standing access by relaunching the server with "
            f"--allow-root {root} or by listing the path in "
            f"${ALLOWED_ROOTS_ENV}."
        )
    return root


def authorize_config(config_path: str | None, root: Path) -> str | None:
    if config_path is None:
        return None
    config = _resolved(config_path, relative_to=root)
    if not config.is_file():
        raise InvalidAuditArgument(f"config_path is not a file: {config}")
    if not (config == root or config.is_relative_to(root)):
        raise PathNotAllowed(f"config_path {config} is outside repository_root {root}")
    return str(config)


def validate_revspec(changed_only: str | None) -> str | None:
    """Admit one inert git revision expression, never command-line options."""
    if changed_only is None:
        return None
    if len(changed_only) > 200 or not _REVSPEC.fullmatch(changed_only):
        raise InvalidAuditArgument("changed_only must be one git revision or range without whitespace or options")
    return changed_only


def audit_repository(
    repository_root: str,
    config_path: str | None = None,
    changed_only: str | None = None,
    run_analyzers: bool | None = None,
    format: str | None = None,
    record_history: bool | None = None,
    baseline_path: str | None = None,
    write_baseline: bool = False,
    include_prompt: bool = True,
    *,
    action: str | None = "run",
    roots: tuple[Path, ...] | None = None,
) -> dict[str, Any]:
    """Run the production audit and return its report plus bounded work order.

    ``action`` is the interactive gate — see ``_gate`` for what each
    value means and why the default differs by door (D27).

    ``run_analyzers`` is tri-state (D1). ``None`` — the default — lets the
    repository's config decide, and a loaded config file defaults the pool
    on: the pool is the primary evidence source (ADR 006), and a caller
    should not need to know a flag to receive the product. Explicit
    ``True``/``False`` overrides for one call, in either direction.
    ``format`` follows the same rule: ``None`` takes the persisted default
    presentation from first-run setup (chat when nothing chose otherwise),
    and a per-call value always wins. ``record_history`` is the loop's
    tri-state (D5): ``None`` appends when a history already exists — the
    file's existence is the standing answer, same as the CLI — and
    otherwise follows the persisted first-run consent
    (``history.record``, decision 4); capability never records, only an
    answer does. A recorded scan
    always carries the delivered prompt's targets (D6): every MCP result
    hands over the remediation prompt, so the advice is remembered.

    A model reading this report is the reader the pool's findings were
    collected for — it can see what the scoring engine structurally
    cannot, which is why the default here follows the config rather than
    silently serving the six built-in detectors while the tools sit unused.
    """
    authorized_roots = roots if roots is not None else allowed_roots()
    root = authorize_repository(repository_root, authorized_roots)
    gated = _gate(root, config_path, action)
    if gated is not None:
        return gated
    config = load_config(authorize_config(config_path, root) or discovered_config(root))
    revspec = validate_revspec(changed_only)
    only_paths = changed_paths(root, revspec) if revspec else None
    if run_analyzers is None:
        run_analyzers = analyzers_run_default(config)
    report = build_report(
        root, config,
        only_paths=only_paths,
        changed_revspec=revspec,
        run_analyzers=run_analyzers,
    )
    status = report.get("git_status_short", "")
    # D20: a repository-controlled paths.history must not escape the
    # repository it came from.
    history_path = repository_path(
        root, (config.get("paths") or {}).get("history"), DEFAULT_HISTORY_PATH)
    # Advice omitted from the payload is never remembered as delivered
    # (D6 coherence with D8's include_prompt).
    record_scan_and_attach(report, config, history_path, root,
                           record=_record_resolved(record_history, history_path, config),
                           want_targets=bool(include_prompt))
    baseline = _baseline_workflow(report, root, baseline_path, write_baseline)
    if format is None:
        # Per-call beats persisted beats the documented default: chat —
        # which is Markdown on the wire — not markdown-the-file (M2).
        format = (config.get("presentation") or {}).get("format") or "chat"
    result = _top_level_result(report, root, status, run_analyzers,
                               baseline, include_prompt)
    return _finish_result(result, format, root, config, report)


def _analyzers_contributed(report: dict[str, Any]) -> bool:
    """Did any external analyzer actually contribute evidence?

    Read from the coverage document the analysis produced, never from
    the request that preceded it. A missing coverage section means the
    pool did not run — an unrequested pool, or one that failed before
    it could report — and in both cases the honest answer is no.
    """
    coverage = report.get("analyzer_coverage")
    if not isinstance(coverage, dict):
        return False
    return bool(coverage.get("tools_contributed"))


def _top_level_result(report: dict[str, Any], root: Path, status: str,
                      run_analyzers: bool, baseline: list[str] | None,
                      include_prompt: bool) -> dict[str, Any]:
    """The keys every format carries, before presentation shaping."""
    result = {
        "agent": "maintainability-agent",
        "agent_version": VERSION,
        # Stated on both kinds of reply, so "did this produce a result?"
        # is one key a consumer can read rather than the absence of
        # another (D26/D27).
        "audit_ran": True,
        "source_commit": run_git(["rev-parse", "HEAD"], root) or None,
        "worktree_dirty": bool(status),
        "gate_passed": not report["hard_gate_failures"],
        # Stated at the top level so a caller cannot mistake an audit that
        # ran six built-in detectors for one that ran ten tools. Two
        # reports with different coverage are not comparable (P8).
        #
        # Outcome, not intent. This used to carry the resolved tri-state,
        # so it read true whenever the pool was *wanted* — and a field run
        # whose catalog was missing reported `"analyzers_run": true` with
        # zero analyzers executed. A caller trusting the envelope over the
        # prose got a false green: the repository's own `absence-as-zero`
        # pattern, one level up, capability recorded as result. The
        # request is kept beside it rather than lost, and the gap between
        # the two is explained by `environment_work_order`.
        "analyzers_run": _analyzers_contributed(report),
        "analyzers_requested": run_analyzers,
    }
    if baseline is not None:
        result["new_findings"] = baseline
    # D9: a selected tool that could not run is actionable evidence the
    # host must be able to surface on every format — the report dict
    # travels only for json, so the remedy cannot live only inside it.
    if report.get("environment_work_order"):
        result["environment_work_order"] = report["environment_work_order"]
    if include_prompt:
        result["remediation_prompt"] = render_ai_prompt(report)
    return result


def _record_resolved(record_history: bool | None, history_path: Path,
                     config: dict[str, Any]) -> bool:
    """The D5 tri-state, resolved: explicit wins, then the standing answers.

    ``None`` records when a series already exists — an existing file
    appends regardless of any later change of heart in config — or when
    the persisted first-run consent (``history.record``, decision 4)
    said yes. Capability never records; only an answer does.
    """
    if record_history is not None:
        return bool(record_history)
    consent = (config.get("history") or {}).get("record")
    return history_path.exists() or consent is True


def _refuse_clobbering_non_baseline(target: Path) -> None:
    """A baseline may replace a baseline, and nothing else (D34).

    `baseline_path` arrives from a model on the primary surface, and
    being inside the granted root was the only check. An audit pointed
    it at `README.md` and the file became baseline JSON — in a tool
    whose MCP description and architecture both promise five artifacts
    and "never source".

    An absent file is fine, and so is one this tool already wrote. Any
    other existing file is someone's work.
    """
    if not target.exists():
        return
    try:
        existing = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as unreadable:
        raise PathNotAllowed(
            f"{target} exists and is not a readable baseline "
            f"({unreadable}); refusing to overwrite it."
        ) from unreadable
    if not (isinstance(existing, dict) and "identities" in existing):
        raise PathNotAllowed(
            f"{target} exists and is not a baseline; refusing to "
            "overwrite it. Choose a path that is absent or holds a "
            "baseline this tool wrote."
        )


def _baseline_workflow(report: dict[str, Any], root: Path,
                       baseline_path: str | None,
                       write: bool) -> list[str] | None:
    """D7: write and/or consult a baseline inside the repository boundary.

    The default location is a standing answer like the history file:
    once a baseline exists there, every later call reports what is new
    against it. ``None`` return means no baseline is in play, and the
    result omits ``new_findings`` rather than publishing an empty claim.
    Suppression never touches ``gate_passed`` — hard gates stay hard.
    """
    from .baseline import findings_not_in_baseline
    from .baseline import write_baseline as write_baseline_file

    target = _resolved(baseline_path or str(DEFAULT_BASELINE_PATH), relative_to=root)
    if not (target == root or target.is_relative_to(root)):
        raise PathNotAllowed(f"baseline_path {target} is outside repository_root {root}")
    if write:
        _refuse_clobbering_non_baseline(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        write_baseline_file(str(target), report)
    if not target.is_file():
        return None
    return sorted(
        identity.fingerprint
        for identity in findings_not_in_baseline(report, str(target), root)
    )


def record_scan_and_attach(report: dict[str, Any], config: dict[str, Any],
                           history_path: Path, root: Path, *,
                           record: bool, want_targets: bool) -> None:
    """The loop's honest ordering, shared by both entry points (audit H1).

    The current scan closes recurrence *before* advice is derived: the
    in-memory record joins the stored series for the views, so a second
    return escalates on this very report; the prompt then withholds the
    candidate; and only what the prompt actually asks is recorded as
    targeted. Append-only holds — the record is appended once, complete.
    ``want_targets`` is False on the CLI path when no prompt artifact
    was requested: advice never delivered is never remembered as given.
    """
    from dataclasses import replace

    pending = record_of(
        report, config, VERSION, CALIBRATION_C,
        tuple(sorted(finding_fingerprints(report))))
    attach_history_views(report, history_path, root,
                         pending=pending if record else None)
    targeted = prompt_targets(report) if want_targets else ()
    if record:
        append_scan(history_path, replace(pending, targeted=targeted))


def attach_history_views(report: dict[str, Any], history_path: Path,
                         root: Path, pending: Any = None) -> None:
    """The durable series, read back into the report — one reader, two doors.

    The CLI and the MCP tool both call this, so the two entry points can
    never disagree about what one history file says. One report per
    segment, never one across them: the comparability gate ran first, so
    nothing here is computed over a change in the instrument. `root`
    carries git's rename evidence into the escalation matching (ADR 009).
    """
    records = read_history(history_path)
    if pending is not None:
        records = [*records, pending]
    series = segments(records)
    report["scan_history"] = [trend_report(segment) for segment in series]
    report["design_review_candidates"] = (
        escalations(series[-1], Path(root)) if series else []
    )


def _finish_result(result: dict[str, Any], format: str, root: Path,
                   config: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    """Presentation, the degradation payload, and the first-contact record.

    8.5: the host asked the user which presentation and passes the answer
    here. One findings body per call (D8): json carries the report dict
    and no rendering; chat and markdown carry the rendered Markdown (on
    the wire the two are the same text, ADR 011 §2); html adds the HTML
    text beside that Markdown, returned for the host to save or show —
    files are the CLI's job (ADR 011 §4).
    """
    if format not in ("chat", "markdown", "html", "json"):
        raise InvalidAuditArgument(f"format must be chat, markdown, html or json, not {format!r}")
    # D8: the requested format governs the payload — one findings body
    # per call (html also carries Markdown: chat shows Markdown
    # whatever else was requested, ADR 011). The report dict travels
    # only for json, where the caller does its own presentation.
    if format == "json":
        result["report"] = report
    else:
        result["report_markdown"] = render_markdown(report)
    if format == "html":
        from .renderers import render_html

        history = repository_path(
            root, config.get("paths", {}).get("history"), DEFAULT_HISTORY_PATH)
        result["report_html"] = render_html(report, read_history(history))
    result["format"] = format
    # No setup questions ride a finished audit. This used to attach them
    # whenever the repository was still pending, which was D3's
    # degradation rule and became wrong the moment setup turned into a
    # precondition: reaching here means an explicit `config_path` was
    # supplied, so the caller had a configuration and there is nothing
    # to ask. An audit found the leftover — `audit_ran: true` and
    # `setup_needed` in one payload, D26's exact shape surviving on the
    # one path that bypasses the gate (D30).
    #
    # First contact is recorded whatever the gate said: "has this
    # tool ever run here" is about the run, not the verdict (D13).
    mark_repo_seen(root)
    return result

