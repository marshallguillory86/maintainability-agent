"""D89: the analyzer pool is pinned where it gates, and floats where it warns.

P1's determinism is conditional on pinned analyzer versions. The runs
that judge a pull request must therefore install the pool through
checked-in constraints, or a green gate certifies only that the suite
passed against that day's releases. The old "an analyzer shipped"
signal still matters and moves to the weekly scheduled run.

Split out of `test_determinism` when that module crossed the file-size
gate, and split into three tests because the single one that covered
this reached complexity 22. Three claims, three checks:

* the gates pin;
* the scheduled job floats, and can actually fail;
* the page describes the arrangement the workflow implements.

The second is the one that has been wrong twice, both times by asserting
a string where the claim is about behaviour — the class D97 names.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "quality-gates.yml"


ANALYZER_POOL = (
    "cohesion",
    "complexipy",
    "flake8",
    "interrogate",
    "lizard",
    "multimetric",
    "mypy",
    "pydocstyle",
    "pylint",
    "radon",
    "ruff",
    "vulture",
)
def _job_block(workflow: str, name: str) -> str:
    pattern = re.compile(rf"(?ms)^  {re.escape(name)}:\n(.*?)(?=^  [a-z0-9-]+:\n|\Z)")
    match = pattern.search(workflow)
    assert match, f"workflow job {name!r} is missing"
    return match.group(1)


def _workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_the_gating_jobs_install_through_the_constraints_file() -> None:
    """A PR gate that floats cannot certify P1's condition."""
    workflow = _workflow()
    for name in ("verify", "audit"):
        job = _job_block(workflow, name)
        assert job, f"the {name} job is gone; this check has nothing to read"
        assert "--constraint constraints/analyzers.txt" in job, (
            f"{name} installs the analyzer pool without the checked-in "
            "constraints file, so the PR gate floats"
        )
        for tool in ANALYZER_POOL:
            assert re.search(rf"\b{re.escape(tool)}\b", job), (
                f"{name} no longer names {tool}, so the pinned gate is not "
                "installing the full pip analyzer pool"
            )


def test_the_scheduled_drift_job_floats_and_can_actually_fail() -> None:
    """The half that has been wrong twice, both times by string-matching.

    First version: asserted `diff -u constraints/analyzers.txt` appeared.
    Appending `|| true` neuters drift detection entirely and left it
    green. Second version: asserted the step mentions stripping;
    replacing the helper body with `cat` left *that* green.

    So the workflow's own normaliser is extracted and **run** against the
    real constraints file, and its output has to be something `pip
    freeze` could have produced. The constraints file carries provenance
    comments that `pip freeze` never emits, which is why the original
    comparison went red every week whether or not anything had drifted —
    and a check that can never pass is worth less than none.
    """
    drift = _job_block(_workflow(), "analyzer-drift")
    assert drift, "the analyzer drift job is gone"
    assert "github.event_name == 'schedule'" in drift, (
        "the unpinned drift job is no longer limited to the scheduled run"
    )

    # Selected by the step's *name line*. Matching anywhere in the block
    # picked the job header instead, whose `if:` condition carries an
    # `==` -- so the "this step does not pin" assertion failed on the
    # wrong text entirely.
    # `[1:]` skips the job header, whose own `name:` also says
    # "unpinned" and whose `if:` carries an `==` -- so selecting on the
    # word alone read the header and failed the "does not pin" check
    # against the wrong text.
    steps = drift.split("- name:")[1:]
    install = next(
        (block for block in steps if "unpinned" in block.split("\n")[0]), None)
    assert install is not None, "the scheduled unpinned install step is gone"
    assert "--constraint" not in install and "==" not in install, (
        "the drift detector pins its install, so it cannot see movement"
    )
    for tool in ANALYZER_POOL:
        assert re.search(rf"\b{re.escape(tool)}\b", install), (
            f"the drift install no longer names {tool}"
        )

    _assert_the_comparison_can_fail(steps)


def _assert_the_comparison_can_fail(steps: list[str]) -> None:
    """The comparison step, checked by running what it defines."""
    compare = next(
        (block for block in steps if "drifted" in block.split("\n")[0]), None)
    assert compare is not None, "the drift comparison step is gone"
    assert "pip freeze --all" in compare and "diff -u" in compare, (
        "the scheduled run no longer resolves and compares the pool"
    )
    for neutered in ("|| true", "continue-on-error", "|| exit 0", "set +e"):
        assert neutered not in compare, (
            f"the comparison is neutered with {neutered!r}: it reports "
            "drift and passes anyway"
        )

    helper = re.search(r"^\s*(strip\(\) \{.*?\})\s*$", compare, re.M)
    assert helper is not None, "the drift step defines no normaliser"
    result = subprocess.run(  # noqa: S602 - the workflow's own one-liner
        f"{helper.group(1)}\nstrip constraints/analyzers.txt",
        shell=True, cwd=ROOT, capture_output=True, text=True, check=False,
    )
    produced = [line for line in result.stdout.splitlines() if line.strip()]
    assert produced, "the normaliser produced nothing from the constraints file"
    commented = [line for line in produced if line.lstrip().startswith("#")]
    assert not commented, (
        "the comparison keeps the provenance comments `pip freeze` never "
        f"emits, so the diff is non-empty every run: {commented[:2]}"
    )


def test_product_intent_describes_the_arrangement_the_workflow_implements() -> None:
    """The page and the pipeline, held together."""
    intent = (ROOT / "docs" / "product-intent.md").read_text(encoding="utf-8")
    for phrase in (
        "`verify` and `audit` install the twelve",
        "scheduled run keeps the old drift signal",
        "fails visibly on a diff",
    ):
        assert phrase in intent, (
            f"product-intent no longer says {phrase!r}, so the page and the "
            "workflow can drift apart unnoticed"
        )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "D89 residual: constraints/analyzers.txt was resolved on macOS "
        "arm64 while the jobs it constrains run ubuntu-latest. Closing it "
        "needs a Linux resolve, which needs installing the pool -- the "
        "reason D89 existed. `resolve-constraints` in the workflow "
        "produces that file; strict, so this fails the day it is fixed "
        "and the marker is left behind."
    ),
)
def test_the_constraints_were_resolved_on_the_platform_the_gates_run_on() -> None:
    """A pin resolved somewhere else is not a pin.

    Two consequences, and the second is the one that bites. The pinned
    install may not resolve on Linux at all, which CI reports the first
    time it runs. But the drift comparison would report platform-
    divergent closures as analyzer drift, weekly, forever — the failure
    this module already fixed once.
    """
    constraints = (ROOT / "constraints" / "analyzers.txt").read_text(encoding="utf-8")
    provenance = [line for line in constraints.splitlines() if line.startswith("#")]
    assert provenance, (
        "the constraints file records no provenance, so nobody can tell "
        "which platform resolved it"
    )
    workflow = _workflow()
    constrained = [
        job for job in ("verify", "audit", "analyzer-drift")
        if "constraints/analyzers.txt" in _job_block(workflow, job)
    ]
    assert constrained, "no job uses the constraints file; this check is moot"
    runners = {
        line.split("runs-on:", 1)[1].strip()
        for job in constrained
        for line in _job_block(workflow, job).splitlines()
        if "runs-on:" in line
    }
    assert runners, "the constrained jobs name no runner"
    header = provenance[0]
    assert not (any("ubuntu" in r for r in runners) and "Linux" not in header), (
        f"the constraints were resolved on a platform the gating jobs do "
        f"not run ({sorted(runners)} vs {header!r}). Re-resolve on the "
        "runner's platform with the resolve-constraints job"
    )
