"""The user-level configuration tier and its state — D13, XDG layout.

Two files, owned by the person rather than any one repository:

* ``config.json`` under XDG config home — defaults a user carries to
  every repository they audit. It sits *between* the built-in defaults
  and the repository file in `load_config`'s precedence, so a
  repository always wins over a person and a person always wins over
  the shipped defaults.
* ``state.json`` under XDG state home — which repository roots this
  tool has audited, and when first. This is the substrate that makes
  "has this ever run here?" a file read instead of a guess, which is
  what D2's first-run setup asks before deciding to elicit.

Everything degrades to absence: a missing, corrupt, or unreadable file
reads as "no user tier", never a crash — a broken dotfile must not be
able to take the audit down. State writes are atomic (temp file then
rename) so a killed process cannot leave a half-written file that the
next run reads as corrupt.
"""
from __future__ import annotations

import contextlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_APP_DIR = "maintainability-agent"


def _xdg_base(variable: str, *fallback: str) -> Path:
    """The XDG base directory: the env var when set, else its home default."""
    configured = os.environ.get(variable)
    base = Path(configured) if configured else Path.home().joinpath(*fallback)
    return base / _APP_DIR


def user_config_path() -> Path:
    return _xdg_base("XDG_CONFIG_HOME", ".config") / "config.json"


def user_state_path() -> Path:
    return _xdg_base("XDG_STATE_HOME", ".local", "state") / "state.json"


def _read_json_object(path: Path) -> dict[str, Any] | None:
    """The file's JSON object, or None for absent, corrupt, or unreadable."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def load_user_config() -> dict[str, Any] | None:
    """The user tier, or None when there is none to apply."""
    return _read_json_object(user_config_path())


def _write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, staged = tempfile.mkstemp(dir=str(path.parent), prefix=".staged-")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(staged, path)
    except OSError:
        # State is a convenience record, never worth failing an audit
        # over: a read-only home directory loses the memo, not the run.
        with contextlib.suppress(OSError):
            os.unlink(staged)


def _seen(state: dict[str, Any] | None) -> dict[str, str]:
    seen = (state or {}).get("seen")
    return dict(seen) if isinstance(seen, dict) else {}


def mark_repo_seen(root: Path) -> None:
    """Record that this tool audited `root`, keyed by its absolute path."""
    seen = _seen(_read_json_object(user_state_path()))
    seen[str(Path(root).resolve())] = datetime.now(UTC).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    _write_atomic(user_state_path(), {"seen": seen})


def repo_first_run(root: Path) -> bool:
    """Whether this tool has never audited `root` — a file read, not a guess."""
    return str(Path(root).resolve()) not in _seen(_read_json_object(user_state_path()))
