"""A findings-exit with an empty body is not a clean analyzer run.

``_runner.run`` returns ``Outcome.RAN`` whenever the exit code is in
``findings_exit_codes``, including a non-zero "I found something" code
with no stdout or stderr. Ruff and flake8 exit 1 to report findings;
Checkstyle uses a non-zero count. An empty body with that exit is
"claimed findings, produced none" — the same absence-as-clean shape
multimetric already refuses in its adapter rather than reporting clean.

The version probe already rejects silence. The analysis spawn does not.

The complementary case is the other half of the boundary: exit 0 with
an empty body is a tool that looked and found nothing. That must stay
``RAN``, or a fix over-corrects into failing clean tools.
"""

from __future__ import annotations

import stat
from pathlib import Path

from maintainability_audit._runner import Invocation, Outcome, run


def _silent(tmp_path: Path, name: str, exit_code: int) -> Path:
    path = tmp_path / name
    path.write_text(f"#!/bin/sh\nexit {exit_code}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def test_a_nonzero_findings_exit_without_output_is_not_a_clean_run(
    tmp_path: Path,
) -> None:
    """A findings-present exit with an empty body must not count as RAN."""
    tool = _silent(tmp_path, "silent-findings", 1)

    result = run(
        "silent-findings",
        Invocation(argv=(str(tool),), findings_exit_codes=(0, 1)),
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr == ""
    assert result.outcome is not Outcome.RAN
    assert result.outcome is Outcome.NOT_WORKING
    assert not result.usable


def test_a_zero_exit_without_output_remains_a_legitimate_clean_run(
    tmp_path: Path,
) -> None:
    """Empty output with exit 0 is a real clean result and must stay RAN."""
    tool = _silent(tmp_path, "silent-clean", 0)

    result = run(
        "silent-clean",
        Invocation(argv=(str(tool),), findings_exit_codes=(0, 1)),
    )

    assert result.exit_code == 0
    assert result.stdout == ""
    assert result.stderr == ""
    assert result.outcome is Outcome.RAN
    assert result.usable
