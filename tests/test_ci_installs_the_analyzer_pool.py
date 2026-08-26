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
        # `_INSTALL` holds the non-pip overrides; anything absent from it
        # falls back to `pip install <slug>` in `environment_work_order`.
        and tool["slug"] not in _INSTALL
    }


def test_the_catalog_still_has_pip_installable_adapters() -> None:
    """If this empties out, the sweep below proves nothing."""
    assert _pip_installable_adapters(), (
        "no implemented adapter installs via pip any more; has _INSTALL "
        "grown to cover everything, or has the catalog changed shape?"
    )


@pytest.mark.parametrize("slug", sorted(_pip_installable_adapters()))
def test_ci_installs_every_pip_installable_adapter(slug: str) -> None:
    """An adapter CI never installs is an adapter CI never runs.

    `ruff` is a dev extra rather than a pool install and is accepted
    either way -- what matters is that the executable is present when the
    suite runs, not which line put it there.
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    assert slug in text, (
        f"{slug} has an implemented adapter and installs with pip, but CI "
        "never installs it -- so its tests skip and the adapter ships "
        "having never been invoked. Add it to the analyzer-pool step."
    )


def test_the_non_pip_adapters_are_exempt_by_name() -> None:
    """The Node and JVM tools are excluded on purpose, and it shows.

    Kept as an assertion rather than a comment so that moving one of
    these onto pip -- or adding a sixteenth adapter in a new ecosystem --
    surfaces here instead of quietly widening the exemption.
    """
    from maintainability_audit._environment import _INSTALL

    assert set(_INSTALL) == {"jscpd", "eslint", "pmd", "checkstyle", "spotbugs"}, (
        "the set of adapters exempt from the CI pool install changed; "
        f"confirm the new set is deliberate: {sorted(_INSTALL)}"
    )
