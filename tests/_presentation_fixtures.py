"""One repository fixture for the presentation-override tests (D194).

Shared because the two suites that exercise the override — the one that
proves the disclosure and the one that holds the silent cases — need the
same repository and the same call. They were split so the falsifier
citations stay evidence, and splitting duplicated these helpers, which
this repository's own duplicate-block gate rejected on the next run.

The gate was right. A fixture that drifts between two files is how one
suite ends up testing a repository the other does not have.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from maintainability_audit import _mcp_audit


def write_config(root: Path, persisted: str | None) -> dict[str, Any]:
    """A minimal audited repository, optionally having chosen a presentation.

    `None` is the repository that never answered the question, which is a
    different case from one that chose and was overridden.
    """
    config: dict[str, Any] = {
        "version": 1,
        "analyzers": {"run": False},
        "history": {"record": False},
    }
    if persisted is not None:
        config["presentation"] = {"format": persisted}
    (root / "maintainability-agent.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    return config


def audit(root: Path, persisted: str | None, requested: str | None) -> dict[str, Any]:
    """Run the audit through the MCP door and return its top-level result."""
    write_config(root, persisted)
    (root / "module.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    return _mcp_audit.audit_repository(
        str(root), action="run", format=requested,
        run_analyzers=False, record_history=False, include_prompt=False,
        roots=(root.resolve(),),
    )
