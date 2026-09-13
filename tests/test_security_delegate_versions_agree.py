"""The secure-code-agent this project gates on is one this audit will run.

3.7.0 made secure-code-agent a package dependency pinned `>=0.10,<0.11`, repeated in
`_security_delegate.REQUIREMENT`, with CI on `==0.10.0` — all taken from the pin CI
already had, while the published tool was at 0.12.1. It is no longer a dependency
(secure-code-agent D3, ADR 008: independently releasable), so the audit's own supported
range is the one declaration, and every CI pin has to fall inside it.

Covers existing behaviour: CI's pin sat inside the declared range before this change
too — on the wrong version. Knowing the current release needs the index, which an
offline suite cannot read; this guard keeps the declarations together from here.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def test_the_supported_range_and_the_install_remedy_are_one_declaration() -> None:
    from maintainability_audit._security_delegate import (
        REQUIREMENT,
        SUPPORTED_CEILING,
        SUPPORTED_FLOOR,
    )

    bounds = dict(re.findall(r"(>=|<)([0-9][0-9.]*)", REQUIREMENT))
    assert _version_tuple(bounds[">="]) == SUPPORTED_FLOOR, (REQUIREMENT, SUPPORTED_FLOOR)
    assert _version_tuple(bounds["<"]) == SUPPORTED_CEILING, (REQUIREMENT, SUPPORTED_CEILING)


def test_secure_code_agent_is_not_a_package_dependency() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    coupled = [dep for dep in project.get("dependencies", []) if dep.startswith("secure-code-agent")]
    assert not coupled, (
        f"secure-code-agent is a package dependency again ({coupled}); the tools are "
        "independently releasable (secure-code-agent D3, ADR 008)"
    )


def test_every_ci_pin_is_a_release_the_audit_runs() -> None:
    from maintainability_audit._security_delegate import SUPPORTED_CEILING, SUPPORTED_FLOOR

    workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    assert workflows, "no workflows found"
    pins = [(path.name, pin) for path in workflows
            for pin in re.findall(r"secure-code-agent==([0-9][0-9.]*)", path.read_text(encoding="utf-8"))]
    assert pins, "no workflow pins secure-code-agent; the gate would run whatever pip picks"
    outside = [(name, pin) for name, pin in pins
               if not (SUPPORTED_FLOOR <= _version_tuple(pin) < SUPPORTED_CEILING)]
    assert not outside, f"CI pins a secure-code-agent this audit refuses to run: {outside}"


def _jobs(text: str) -> dict[str, str]:
    """Each job's text in a workflow, split on the two-space job keys under `jobs:`.

    Read as text, as `test_ci_installs_the_analyzer_pool` does: the suite does
    not import a YAML parser.
    """
    body = text.split("\njobs:\n", 1)[1] if "\njobs:\n" in text else ""
    parts = re.split(r"^  ([A-Za-z0-9_-]+):\s*$", body, flags=re.MULTILINE)
    return {parts[index]: parts[index + 1] for index in range(1, len(parts) - 1, 2)}


def test_every_job_that_runs_the_suite_installs_secure_code_agent() -> None:
    """The 3.7.2 tag failed in `release.yml`: it ran the suite without the tool.

    `test_every_ci_pin_is_a_release_the_audit_runs` checked the pins that
    existed, and the release job had none. The population here is every job,
    in every workflow, whose steps run pytest.
    """
    running = [
        (path.name, job, body)
        for path in sorted((ROOT / ".github" / "workflows").glob("*.yml"))
        for job, body in _jobs(path.read_text(encoding="utf-8")).items()
        if re.search(r"-m pytest\b", body)
    ]
    assert running, "no workflow job runs pytest; the sweep would pass vacuously"
    missing = [(name, job) for name, job, body in running if "secure-code-agent==" not in body]
    assert not missing, f"jobs that run the suite without installing secure-code-agent: {missing}"
