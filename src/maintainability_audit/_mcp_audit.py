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

import os
import re
from pathlib import Path
from typing import Any

from ._calibration import CALIBRATION_C
from ._mcp_setup import setup_pending, setup_questions
from ._recurrence import escalations
from ._scan_history import (
    DEFAULT_HISTORY_PATH,
    append_scan,
    read_history,
    record_of,
    segments,
)
from ._trends import trend_report
from ._user_config import mark_repo_seen
from ._work_order import prompt_targets
from .baseline import finding_fingerprints
from .config import (
    VERSION,
    analyzers_run_default,
    discovered_config,
    load_config,
)
from .git_tools import changed_paths, run_git
from .prompts import render_ai_prompt
from .renderers import render_markdown
from .report import build_report

ALLOWED_ROOTS_ENV = "MAINTAINABILITY_MCP_ALLOWED_ROOTS"
_REVSPEC = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/@^~:+-]*(?:\.{2,3}[A-Za-z0-9._/@^~:+-]+)?")

class PathNotAllowed(ValueError):
    """A requested repository or config escaped the configured read boundary."""


def _resolved(path: str | Path, *, relative_to: Path | None = None) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute() and relative_to is not None:
        candidate = relative_to / candidate
    return candidate.resolve()


def allowed_roots(explicit: tuple[str, ...] = ()) -> tuple[Path, ...]:
    """Resolve the server allow-list once, defaulting to its launch directory."""
    configured = explicit or tuple(filter(None, os.environ.get(ALLOWED_ROOTS_ENV, "").split(os.pathsep)))
    roots = configured or (str(Path.cwd()),)
    return tuple(_resolved(root) for root in roots)


def _inside(path: Path, roots: tuple[Path, ...]) -> bool:
    return any(path == root or path.is_relative_to(root) for root in roots)


def authorize_repository(repository_root: str, roots: tuple[Path, ...]) -> Path:
    root = _resolved(repository_root)
    if not root.is_dir():
        raise ValueError(f"repository_root is not a directory: {root}")
    if not _inside(root, roots):
        allowed = ", ".join(str(item) for item in roots)
        raise PathNotAllowed(f"repository_root {root} is outside allowed roots: {allowed}")
    return root


def authorize_config(config_path: str | None, root: Path) -> str | None:
    if config_path is None:
        return None
    config = _resolved(config_path, relative_to=root)
    if not config.is_file():
        raise ValueError(f"config_path is not a file: {config}")
    if not (config == root or config.is_relative_to(root)):
        raise PathNotAllowed(f"config_path {config} is outside repository_root {root}")
    return str(config)


def validate_revspec(changed_only: str | None) -> str | None:
    """Admit one inert git revision expression, never command-line options."""
    if changed_only is None:
        return None
    if len(changed_only) > 200 or not _REVSPEC.fullmatch(changed_only):
        raise ValueError("changed_only must be one git revision or range without whitespace or options")
    return changed_only


def audit_repository(
    repository_root: str,
    config_path: str | None = None,
    changed_only: str | None = None,
    run_analyzers: bool | None = None,
    format: str | None = None,
    record_history: bool | None = None,
    *,
    roots: tuple[Path, ...] | None = None,
) -> dict[str, Any]:
    """Run the production audit and return its report plus bounded work order.

    ``run_analyzers`` is tri-state (D1). ``None`` — the default — lets the
    repository's config decide, and a loaded config file defaults the pool
    on: the pool is the primary evidence source (ADR 006), and a caller
    should not need to know a flag to receive the product. Explicit
    ``True``/``False`` overrides for one call, in either direction.
    ``format`` follows the same rule: ``None`` takes the persisted default
    presentation from first-run setup (chat when nothing chose otherwise),
    and a per-call value always wins. ``record_history`` is the loop's
    tri-state (D5): ``None`` appends when a history already exists — the
    file's existence is the standing answer, same as the CLI — and the
    tool binding upgrades ``None`` to ``True`` for elicitation-capable
    clients, the chat analog of the CLI's TTY rule. A recorded scan
    always carries the delivered prompt's targets (D6): every MCP result
    hands over the remediation prompt, so the advice is remembered.

    A model reading this report is the reader the pool's findings were
    collected for — it can see what the scoring engine structurally
    cannot, which is why the default here follows the config rather than
    silently serving the six built-in detectors while the tools sit unused.
    """
    authorized_roots = roots if roots is not None else allowed_roots()
    root = authorize_repository(repository_root, authorized_roots)
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
    history_path = root / ((config.get("paths") or {}).get("history") or DEFAULT_HISTORY_PATH)
    if record_history is None:
        record_history = history_path.exists()
    if record_history:
        append_scan(history_path, record_of(
            report, config, VERSION, CALIBRATION_C,
            tuple(sorted(finding_fingerprints(report))),
            targeted=prompt_targets(report)))
    attach_history_views(report, history_path, root)
    if format is None:
        # Per-call beats persisted beats the documented default: chat —
        # which is Markdown on the wire — not markdown-the-file (M2).
        format = (config.get("presentation") or {}).get("format") or "chat"
    result = {
        "agent": "maintainability-agent",
        "agent_version": VERSION,
        "source_commit": run_git(["rev-parse", "HEAD"], root) or None,
        "worktree_dirty": bool(status),
        "gate_passed": not report["hard_gate_failures"],
        # Stated at the top level so a caller cannot mistake an audit that
        # ran six built-in detectors for one that ran ten tools. Two
        # reports with different coverage are not comparable (P8).
        "analyzers_run": run_analyzers,
        "report": report,
        "report_markdown": render_markdown(report),
        "remediation_prompt": render_ai_prompt(report),
    }
    return _finish_result(result, format, root, config, report)


def attach_history_views(report: dict[str, Any], history_path: Path,
                         root: Path) -> None:
    """The durable series, read back into the report — one reader, two doors.

    The CLI and the MCP tool both call this, so the two entry points can
    never disagree about what one history file says. One report per
    segment, never one across them: the comparability gate ran first, so
    nothing here is computed over a change in the instrument. `root`
    carries git's rename evidence into the escalation matching (ADR 009).
    """
    series = segments(read_history(history_path))
    report["scan_history"] = [trend_report(segment) for segment in series]
    report["design_review_candidates"] = (
        escalations(series[-1], Path(root)) if series else []
    )


def _finish_result(result: dict[str, Any], format: str, root: Path,
                   config: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    """Presentation, the degradation payload, and the first-contact record.

    8.5: the host asked the user which presentation and passes the answer
    here. HTML comes back as *text* for the host to save or show; files
    are the CLI's job (ADR 011 §4). Markdown is always present, because
    chat shows Markdown whatever else was requested — "chat" is accepted
    because the prompt itself offers it, and on the wire chat *is*
    Markdown (ADR 011 §2).
    """
    if format not in ("chat", "markdown", "html", "json"):
        raise ValueError(f"format must be chat, markdown, html or json, not {format!r}")
    if format == "html":
        from ._scan_history import DEFAULT_HISTORY_PATH, read_history
        from .renderers import render_html

        history = root / (config.get("paths", {}).get("history") or DEFAULT_HISTORY_PATH)
        result["report_html"] = render_html(report, read_history(history))
    result["format"] = format
    if setup_pending(root):
        # The host could not (or chose not to) elicit, and nothing is
        # configured: hand the same questions over as data so the host's
        # own question UI can ask and call again (D3's degradation rule).
        result["setup_needed"] = {"questions": setup_questions(load_config(None))}
    # First contact is now recorded whatever the gate said: "has this
    # tool ever run here" is about the run, not the verdict (D13).
    mark_repo_seen(root)
    return result

