"""A process the suite starts reads the same coverage settings the suite does.

Several tests run a repository's own test command in a temporary tree —
that is the test-execution feature, exercised end to end. Under
`pytest --cov`, pytest-cov's subprocess hook makes each of those children
write coverage data of its own, and the child reads its settings the way
coverage always does: from the configuration file in its working
directory. The working directory is a temporary repository with no
`pyproject.toml`, so the child falls back to coverage's defaults, and the
default is statement coverage. This repository measures branches.

`combine` then refuses to merge the two:

    DataError: Can't combine statement coverage data with branch data

and pytest exits 3 **after printing "N passed"**. It reads like a pass
with an alarming traceback beneath it — and the INTERNALERROR consumes the
failure summary, so a test that genuinely failed in that run is reported
nowhere. That happened on 2026-09-23: one failure, name unknown, never
reproduced, because the only run that saw it could not say what it was.

That is this project's own recurring defect, a failure read as a pass,
in the tool it uses to check itself. The fix is to tell every child
which configuration to read instead of letting it guess from where it
happens to be standing.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_a_child_started_elsewhere_reads_this_repositorys_coverage_config(
    tmp_path: Path,
) -> None:
    """The child runs where the product runs a suite: a tree of its own.

    Without the pin it reads coverage's defaults from `tmp_path`, which
    has no configuration, and reports statement coverage — the half that
    cannot be combined with the parent's branch data.
    """
    # The setting the child has to agree with, checked first: if this
    # repository stopped measuring branches, a child reading `False` would
    # be agreeing with it and the assertion below would be vacuous.
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    run = text.split("[tool.coverage.run]", 1)
    assert len(run) == 2, "no [tool.coverage.run] table; nothing to agree with"
    assert "branch = true" in run[1].split("\n[", 1)[0]

    # Coverage is imported by the child, not here: `test_declared_imports`
    # forbids an undeclared third-party import in tests, and the child's
    # import already fails this test loudly through `check=True` if the
    # module is missing. Nothing is skipped either way.
    result = subprocess.run(
        [
            sys.executable, "-c",
            "import coverage; print(coverage.Coverage().config.branch)",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "True", (
        "a process started outside the repository read coverage's defaults "
        "rather than this repository's configuration, so its data cannot be "
        "combined with the suite's and `pytest --cov` aborts after printing "
        "its pass count"
    )
