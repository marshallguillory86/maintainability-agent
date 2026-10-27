"""CI was judged too slow and too costly. The evidence: Quality Gates
ran twice per PR (push on every branch plus pull_request), MA audited itself
twice (maintainability.yml plus the Quality Gates audit job), a Windows probe
failed every run while blocking nothing, and Sonar ran on every PR.

The required checks must still run on every pull_request, or merges deadlock;
that guard lives in test_workflow_supply_chain.py.
"""

from __future__ import annotations

import re
from pathlib import Path

from _workflow_text import jobs, triggers

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def test_quality_gates_push_is_limited_to_main_so_a_pr_runs_once() -> None:
    """No push trigger at all (his pipeline lint: a merge never re-runs
    tests), or one limited to main."""
    push = triggers("quality-gates.yml").get("push")
    if push is None:
        return
    body = " ".join(s.strip() for s in push)
    assert re.search(r"branches:\s*\[\s*main\s*\]", body) or (
        "branches:" in body and re.search(r"-\s*main\b", body)
    ), f"push must be absent or restricted to branches: [main]; got {body!r}"


def test_maintainability_workflow_does_not_audit_every_pull_request_again() -> None:
    assert "pull_request" not in triggers("maintainability.yml")


def test_no_windows_job_runs_at_all() -> None:
    """Decision 18: Windows is not tested in CI; Windows users report
    problems as issues or PRs."""
    assert "probe-windows" not in jobs("quality-gates.yml")
    for path in WORKFLOWS.glob("*.yml"):
        assert "windows-" not in path.read_text(encoding="utf-8"), path.name


def test_sonar_does_not_run_on_pull_requests() -> None:
    condition = jobs("quality-gates.yml")["sonar"]["if"]
    assert condition, "sonar needs an `if:`"
    assert "pull_request" not in condition


def _runs_on_pull_request(condition: str) -> bool:
    """True when an `if:` leaves the job running on pull_request."""
    if not condition:
        return True
    if "!= 'pull_request'" in condition:
        return False
    return "pull_request" in condition or "!= 'push'" in condition


def _job_bodies(workflow: str) -> dict[str, str]:
    """Job id -> the job's raw text, so a test can read `runs-on` and steps."""
    from _workflow_text import _code_lines, _sub_blocks, _top_block

    blocks = _sub_blocks(_top_block(_code_lines(workflow), "jobs"), 2)
    return {job_id: "\n".join(body) for job_id, body in blocks.items()}


def test_no_macos_job_runs_in_ci() -> None:
    """His decision (2026-10-15, option 1): each test runs once, on Linux
    `verify`. macOS is covered by the local gate on his Mac."""
    assert "verify-macos" not in jobs("quality-gates.yml")
    for path in WORKFLOWS.glob("*.yml"):
        for job_id, job in jobs(path.name).items():
            assert "macos" not in job["name"].lower(), f"{path.name}:{job_id} name"
        for job_id, body in _job_bodies(path.name).items():
            runs_on = re.findall(r"^\s*runs-on:\s*(.*)$", body, flags=re.M)
            assert not any("macos" in value.lower() for value in runs_on), (
                f"{path.name}:{job_id} runs on macOS"
            )


def test_verify_does_not_run_on_a_merge_to_main() -> None:
    """Tests run once, on the pull request; a push to main does not rerun them."""
    condition = jobs("quality-gates.yml")["verify"]["if"]
    assert condition, "verify needs an `if:` that excludes push"
    assert "github.event_name != 'push'" in condition, condition


def test_exactly_one_job_runs_the_test_suite_on_pull_requests() -> None:
    bodies = _job_bodies("quality-gates.yml")
    conditions = jobs("quality-gates.yml")
    runners = [
        job_id
        for job_id, body in bodies.items()
        if "pytest" in body and _runs_on_pull_request(conditions[job_id]["if"])
    ]
    assert runners == ["verify"], f"jobs running pytest on pull_request: {runners}"
