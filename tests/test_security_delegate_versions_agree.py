"""The secure-code-agent version this package declares, runs and gates on is one version.

3.7.0 declared `secure-code-agent>=0.10,<0.11` in `pyproject.toml`, repeated it in
`_security_delegate.REQUIREMENT` for the install remedy, and CI pinned `==0.10.0` — all
taken from the pin CI already had, while the published tool was at 0.12.1. Installing
this package on a machine with the current release downgraded it. The three
declarations are read from their files here, so a bump that misses one fails.

Covers existing behaviour: the three agreed before this change too — on the wrong
version. What moved them to 0.12.1 was checking the published releases, which an
offline suite cannot do; this guard keeps them together from here.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _declared() -> str:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    found = [dep for dep in project.get("dependencies", []) if dep.startswith("secure-code-agent")]
    assert len(found) == 1, f"expected one secure-code-agent dependency, found {found}"
    return found[0].replace(" ", "")


def _version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def test_the_install_remedy_names_the_declared_dependency() -> None:
    from maintainability_audit._security_delegate import REQUIREMENT

    assert REQUIREMENT.replace(" ", "") == _declared(), (
        f"the install remedy says {REQUIREMENT!r} but pyproject declares {_declared()!r}"
    )


def test_every_ci_pin_satisfies_the_declared_range() -> None:
    declared = _declared()
    bounds = dict(re.findall(r"(>=|<)([0-9][0-9.]*)", declared))
    assert ">=" in bounds and "<" in bounds, f"the declared range is not bounded: {declared}"
    workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    assert workflows, "no workflows found"
    pins = [(path.name, pin) for path in workflows
            for pin in re.findall(r"secure-code-agent==([0-9][0-9.]*)", path.read_text(encoding="utf-8"))]
    assert pins, "no workflow pins secure-code-agent; the gate would run whatever pip picks"
    outside = [(name, pin) for name, pin in pins
               if not (_version_tuple(bounds[">="]) <= _version_tuple(pin) < _version_tuple(bounds["<"]))]
    assert not outside, f"CI pins outside the declared {declared}: {outside}"
