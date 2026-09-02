"""Every pip-installable adapter is exercised by CI, or CI says why.

44 of the suite's 45 skips were "<tool> is not installed", and CI skipped
the same set. So the 15 hand-written adapters shipped covered only by
their unit tests -- never by an actual invocation of the tool they adapt.
A wrong flag, a changed output format or a renamed field would have
passed every gate this project has.

The list is derived from the catalog and `_environment._INSTALL`, not
hand-maintained here, because a hand-maintained list is the exact shape
this project has spent a week removing: the sixteenth adapter would be
added, silently not installed, and the suite would keep reporting green
while covering fifteen.

Tools whose install command is not pip -- the Node and JVM ones -- are
out of scope by declaration rather than by omission, and this test names
them so the exemption stays visible.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "quality-gates.yml"


def _pip_installable_adapters() -> set[str]:
    """Adapters the product itself would tell a user to `pip install`."""
    from maintainability_audit._catalog import CATALOG_PATH
    from maintainability_audit._environment import _INSTALL

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return {
        tool["slug"]
        for tool in catalog["tools"]
        if tool.get("adapter") == "implemented"
        # `_INSTALL` overrides the install command; anything absent from
        # it falls back to `pip install <slug>` in
        # `environment_work_order`. An override is only an exemption when
        # it leaves pip entirely — npm or brew. `fortitude` overrides to
        # `pip install fortitude-lint`, because the distribution and the
        # command it installs are spelled differently, and treating that
        # as an exemption would have dropped a pip-installable adapter
        # out of this sweep for a reason that has nothing to do with pip.
        and _INSTALL.get(tool["slug"], "pip install").startswith("pip install")
    }


def _expected_package(slug: str) -> str:
    """The distribution name CI must name, which is not always the slug."""
    from maintainability_audit._environment import _INSTALL

    override = _INSTALL.get(slug)
    return override.split()[-1] if override else slug


def test_the_catalog_still_has_pip_installable_adapters() -> None:
    """If this empties out, the sweep below proves nothing."""
    assert _pip_installable_adapters(), (
        "no implemented adapter installs via pip any more; has _INSTALL "
        "grown to cover everything, or has the catalog changed shape?"
    )


_YAML_KEY = re.compile(r"^[\w-]+:")


def _pip_installed_by_ci() -> set[str]:
    """Package names every `pip install` in the workflows actually names.

    Tokenised from the command text with comment-only lines dropped
    first, so a mention in a comment or a job name cannot stand in for
    an install -- which is exactly what the substring version accepted.

    Read as text rather than parsed as YAML on purpose: PyYAML is kept
    off the test extra so a catalog-regen parser does not land in every
    test install, and `test_pyproject_extras_are_accounted_for` enforces
    that. A check that needed a forbidden dependency would be a worse
    answer than the one it replaced.
    """
    installed: set[str] = set()
    for path in sorted(WORKFLOW.parent.glob("*.yml")):
        lines = [
            line for line in path.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("#")
        ]
        for index, line in enumerate(lines):
            if "pip install" not in line:
                continue
            words = line.split("pip install", 1)[1].split()
            # A folded `run: >` block continues the command across lines
            # until the next YAML key or list item.
            for following in lines[index + 1:]:
                stripped = following.strip()
                if (not stripped or stripped.startswith("- ")
                        or _YAML_KEY.match(stripped)):
                    break
                words += stripped.split()
            installed |= {
                word for word in words if word and not word.startswith("-")
            }
    return installed


@pytest.mark.parametrize("slug", sorted(_pip_installable_adapters()))
def test_ci_installs_every_pip_installable_adapter(slug: str) -> None:
    """An adapter CI never installs is an adapter CI never runs.

    Read out of the actual `pip install` commands rather than out of the
    file. The first version asked whether the slug appeared *anywhere* in
    the workflow text, which a comment satisfies: an audit deleted
    `flake8` from the install line, left `# flake8 is installed by this
    step` behind, and all fourteen of these passed while the adapter went
    uninstalled. A check a comment can satisfy is not a check.
    """
    installed = _pip_installed_by_ci()
    package = _expected_package(slug)
    assert package in installed, (
        f"{slug} has an implemented adapter and installs with pip (as "
        f"`{package}`), but no "
        f"CI step installs it -- so its tests skip and the adapter ships "
        f"having never been invoked. Installed by CI: {sorted(installed)}"
    )


def test_the_non_pip_adapters_are_exempt_by_name() -> None:
    """The Node and JVM tools are excluded on purpose, and it shows.

    Kept as an assertion rather than a comment so that moving one of
    these onto pip -- or adding an adapter in a new ecosystem --
    surfaces here instead of quietly widening the exemption.

    The exemption is *leaving pip*, not *having an override*. `fortitude`
    has an override and is still swept above, because it installs with
    pip under a different distribution name (`fortitude-lint`). Reading
    every override as an exemption would drop a pip-installable adapter
    out of the CI-install guard for a reason that has nothing to do with
    pip — the guard weakening itself as the pool grows.
    """
    from maintainability_audit._environment import _INSTALL

    non_pip = {
        slug for slug, command in _INSTALL.items()
        if not command.startswith("pip install")
    }
    assert non_pip == {"jscpd", "eslint", "pmd", "checkstyle", "spotbugs"}, (
        "the set of adapters exempt from the CI pool install changed; "
        f"confirm the new set is deliberate: {sorted(non_pip)}"
    )
    assert _INSTALL["fortitude"] == "pip install fortitude-lint"
    assert "fortitude" in _pip_installable_adapters(), (
        "a pip-installable adapter must stay in the CI-install sweep even "
        "when its distribution name differs from its command"
    )
