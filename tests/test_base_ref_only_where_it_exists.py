"""`github.base_ref` is used only where it has a value (D234).

`base_ref` is set on a pull request and empty on every other event. When
CI stopped running the maintainability audit on pull requests and moved it
to pushes on main (Decision 18, 2026-10-15), its `changed-only` stayed
`origin/${{ github.base_ref }}...HEAD`. On a push that is `origin/...HEAD`,
git cannot resolve it, and the job failed on every push to main from that
day — while every pull request, where the value exists, passed.

A job that reads `base_ref` either belongs to a workflow only pull requests
trigger, or is guarded to them with `if: github.event_name == 'pull_request'`.
The jobs are read from the workflow files, so a job added later is held to it.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
PULL_REQUEST_EVENTS = {"pull_request", "pull_request_target"}


def _triggers(text: str) -> set[str]:
    block = re.search(r"^on:\s*\n((?:(?:\s*#.*|  .*)?\n)+)", text, re.M)
    assert block, "a workflow without an `on:` block"
    return set(re.findall(r"^  ([a-z_]+):", block.group(1), re.M))


def _jobs(text: str) -> dict[str, str]:
    body = text.split("\njobs:\n", 1)[1]
    parts = re.split(r"^  ([A-Za-z0-9_-]+):\s*$", body, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2], strict=True))


def test_every_job_reading_base_ref_runs_only_on_pull_requests() -> None:
    readers, unguarded = [], []
    for workflow in WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        only_pull_requests = _triggers(text) <= PULL_REQUEST_EVENTS
        for job, body in _jobs(text).items():
            if "github.base_ref" not in body:
                continue
            readers.append(f"{workflow.name}:{job}")
            guarded = re.search(r"^    if: github\.event_name == 'pull_request'", body, re.M)
            if not (only_pull_requests or guarded):
                unguarded.append(f"{workflow.name}:{job}")
    # A parser that found no reader would pass this vacuously.
    assert len(readers) >= 2, readers
    assert unguarded == [], f"these jobs read base_ref on events where it is empty: {unguarded}"


def test_a_range_git_cannot_resolve_is_refused_by_name_not_a_traceback(tmp_path: Path, capsys) -> None:
    """The second half: the audit crashed with `GitCommandFailed` and a traceback.

    A pipeline reading that cannot tell a bad input from a broken tool. The
    pre-commit mode already refuses by name with exit 2; the audit does too.
    """
    import subprocess

    from maintainability_audit.cli import main

    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "-C", str(root), "init", "-q", "-b", "main"], check=True)
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "base"], check=True)

    code = main(["--root", str(root), "--no-analyzers", "--changed-only", "origin/...HEAD"])

    assert code == 2
    assert "origin/...HEAD" in capsys.readouterr().err
