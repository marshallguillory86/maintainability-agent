"""The release workflow follows the version-bump decision boundary.

The old workflow made a tag push the only release event, which put a manual
credential-bearing step between merging a version bump and publishing it.
These text-level checks keep the GitHub Actions graph honest without adding a
YAML dependency to the test environment.
"""
from __future__ import annotations

import re
from pathlib import Path

from _workflow_text import job_bodies, triggers, workflow_steps

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / ".github" / "workflows" / "release.yml"
CUT_RELEASE = ROOT / ".github" / "workflows" / "cut-release.yml"


def _workflow() -> str:
    assert RELEASE.exists(), f"{RELEASE} is missing"
    return RELEASE.read_text(encoding="utf-8")


def _cut_release_workflow() -> str:
    assert CUT_RELEASE.exists(), f"{CUT_RELEASE} is missing"
    return CUT_RELEASE.read_text(encoding="utf-8")


def _job_blocks() -> dict[str, str]:
    return job_bodies("release.yml")


def test_cut_release_triggers_on_main_push() -> None:
    """The push-to-main trigger lives in cut-release.yml, not release.yml."""
    on = triggers("cut-release.yml")
    assert "push" in on
    assert re.search(r"branches:\s*\[\s*main\s*\]", "\n".join(on["push"]))
    release_on = triggers("release.yml")
    assert "branches:" not in "\n".join(release_on.get("push", []))


def test_cut_release_runs_decision_and_dispatches_release() -> None:
    """A GITHUB_TOKEN dispatch is the event that starts the separate release workflow."""
    workflow = _cut_release_workflow()
    assert "tools/release_decision.py" in workflow
    assert re.search(
        r"if:.*create_tag|create_tag.*if:", workflow, flags=re.IGNORECASE | re.DOTALL
    )
    assert "gh workflow run release.yml --ref main" in workflow


def test_cut_release_has_only_read_contents_and_write_actions_permissions() -> None:
    """The cut workflow gets only the token permissions needed to dispatch release."""
    workflow = _cut_release_workflow()
    permissions_match = re.search(
        r"(?ms)^permissions:\s*\n(?P<body>(?:^  \w+:\s+\w+\s*$\n?)+)",
        workflow,
    )
    assert permissions_match, "cut-release.yml has no top-level permissions block"
    permissions = dict(re.findall(r"^  (\w+):\s+(\w+)\s*$", permissions_match["body"], re.M))
    assert permissions == {"contents": "read", "actions": "write"}


def test_cut_release_contains_no_test_runner() -> None:
    """The merge-triggered workflow obeys the pipeline rule by running no tests."""
    workflow = _cut_release_workflow().lower()
    assert "pytest" not in workflow
    assert "python3 -m pytest" not in workflow
    assert "tools/local-gate.sh" not in workflow


def test_decide_job_runs_the_release_decision_tool() -> None:
    """One decision job must make the release and tag outputs authoritative."""
    jobs = _job_blocks()
    decide = jobs.get("decide", "")
    assert decide, "release.yml has no decide job"
    assert "tools/release_decision.py" in decide
    assert "release" in decide and "create_tag" in decide and "tag" in decide


def test_build_needs_decide_and_uses_its_release_output() -> None:
    """The build must be gated by the decision before publish can proceed."""
    build = _job_blocks().get("build", "")
    assert re.search(r"needs:\s*decide\b|needs:\s*\[\s*decide\s*\]", build)
    assert "needs.decide.outputs.release" in build


def test_tag_job_needs_publish_and_is_gated_on_create_tag() -> None:
    """The tag is cut only after PyPI accepts the built artifact."""
    jobs = _job_blocks()
    tag_jobs = {
        name: body for name, body in jobs.items()
        if re.search(r"\bgit\s+tag\b", body)
    }
    assert tag_jobs, "release.yml has no job that creates the release tag"
    assert any(re.search(r"needs:.*publish", body) for body in tag_jobs.values())
    assert any("needs.decide.outputs.create_tag" in body for body in tag_jobs.values())


def test_github_release_needs_the_tag_job_and_uses_decided_tag() -> None:
    """GitHub Release must follow tag creation and use the decision output."""
    github_release = _job_blocks().get("github-release", "")
    assert github_release
    assert re.search(r"needs:.*(?:create-tag|tag)", github_release)
    assert "needs.decide.outputs.tag" in github_release
    assert "github.ref_name" not in github_release


def test_wheel_version_check_always_compares_with_decided_tag() -> None:
    """Every release path must verify the wheel against the decided version."""
    build = _job_blocks().get("build", "")
    assert "needs.decide.outputs.tag" in build
    assert "GITHUB_REF_TYPE" not in build


def test_build_refuses_commits_not_on_main_before_testing_the_package() -> None:
    """The pypi environment accepts v* tags, and a tag can be pushed on any commit."""
    steps = workflow_steps(_workflow())
    ancestry = [
        step
        for step in steps
        if "git merge-base --is-ancestor" in step["run"]
        and '"$GITHUB_SHA"' in step["run"]
        and "origin/main" in step["run"]
    ]
    assert ancestry, (
        "the build must verify that GITHUB_SHA is an ancestor of origin/main "
        "before a tag or workflow_dispatch path can publish"
    )
    gate = ancestry[0]
    assert not gate["if"], "the main-ancestry check must run on every release path"
    test_package = next(i for i, step in enumerate(steps) if step["name"] == "Test the built package")
    assert steps.index(gate) < test_package
