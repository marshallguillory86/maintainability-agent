"""A version that merges ships before the next one does.

3.7.20 through 3.7.30 merged to `main` over two days and none was tagged,
so none reached PyPI. Among them was D211, the fix that stops an audited
tree redirecting a read out of itself: merged, reviewed, and delivered to
nobody who installed the package. 3.8.0 was the first release after
3.7.19 and carried all eleven at once.

Nothing noticed, and the reason is written into the only check on
tagging. `test_release_plan` accepts the plan's "Last tagged version" row
if it names *either* the newest tag *or* the version this tree is about to
ship — correctly, because demanding only the newest tag deadlocked the
v1.1.0 release in both directions. But `tools/stamp_version.py` writes the
about-to-ship version into that row on every bump, so the row always
satisfies the second clause, whether or not anything was ever tagged. The
check was measuring the stamp, not the release.

**The rule here is narrower than "every version is tagged", on purpose.**
Forty-seven releases between 1.1.0 and 3.7.5 are on PyPI with no tag in
this repository, because the 2026-09-16 history rewrite that removed a
work address from every historical tree left the old tags pointing at
commits that no longer exist. Those were removed deliberately and must not
be re-created — a re-pushed tag would republish an old version over a
newer one. A rule over all of history would fail on a decision.

What catches a backlog on its *first* step is one version back: the
release before the one this tree ships must already carry its tag. 3.7.21
could not have merged while 3.7.20 sat untagged.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from maintainability_audit import __version__ as VERSION

ROOT = Path(__file__).resolve().parents[1]
HEADING = re.compile(r"^## (\d+\.\d+\.\d+)\b", re.M)


def _changelog_versions() -> list[str]:
    """Every released version, newest first, as the changelog lists them."""
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    return HEADING.findall(text)


def _tags() -> set[str]:
    out = subprocess.run(
        ["git", "-C", str(ROOT), "tag", "--list", "v*"],
        capture_output=True, text=True, check=True,
    ).stdout
    return {line.strip() for line in out.splitlines() if line.strip()}


def test_the_changelog_leads_with_the_version_this_tree_ships() -> None:
    """The anchor the rule below counts back from. Vacuous without it."""
    versions = _changelog_versions()

    assert len(versions) >= 2, "fewer than two releases; nothing to look back at"
    assert versions[0] == VERSION, (
        f"the changelog's newest section is {versions[0]} and the package "
        f"ships {VERSION}; the previous release cannot be found from here"
    )


def test_the_release_before_this_one_carries_its_tag() -> None:
    """One step back is where a backlog starts, so one step back is checked.

    Fails rather than skips when no tag is visible at all. A shallow
    checkout has none, and reading "no tags" as "nothing to check" is how
    this would go vacuous in exactly the build that runs it — every CI job
    here fetches full history for that reason, `release.yml` included.
    """
    tags = _tags()
    assert tags, (
        "no version tags are visible — a shallow checkout. This check cannot "
        "run without history and will not pretend to pass; fetch with "
        "`fetch-depth: 0`"
    )

    previous = _changelog_versions()[1]

    assert f"v{previous}" in tags, (
        f"{previous} is the release before {VERSION} and was never tagged, so "
        "it never reached PyPI. Tag it before shipping another on top of it — "
        "3.7.20 through 3.7.30 stacked up this way, unreleased, including a "
        "security fix"
    )
