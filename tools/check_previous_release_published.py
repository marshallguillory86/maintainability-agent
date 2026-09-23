#!/usr/bin/env python3
"""Refuse to publish a release over one that never reached PyPI.

Run by `release.yml` before the publish step. 3.7.2 was tagged and its
build failed, so it was never published; 3.7.3 fixed the build and shipped
over the gap without anything noting that a version was missing. The
suite cannot see this — it runs without network access by design — so
the check lives here, where the release build can reach the index.

It looks one version back, the same rule as
`test_the_previous_release_was_tagged`, and for the same reason: old gaps
are recorded decisions (see docs/release-plan.md) and must not be
"repaired" by republishing an old version over a newer one.

Exit 0 when the previous release is on PyPI, 1 with the reason otherwise —
including when PyPI could not be asked, because a check that passes when it
cannot run is not a check.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

HEADING = re.compile(r"^## (\d+\.\d+\.\d+)\b", re.M)
PACKAGE = "maintainability-agent"


def previous_version(changelog: str, version: str) -> str | None:
    """The release immediately before `version`, as the changelog lists it."""
    versions = HEADING.findall(changelog)
    if len(versions) < 2 or versions[0] != version:
        return None
    return versions[1]


def verdict(
    changelog: str, version: str, published: Callable[[str], bool | None]
) -> str | None:
    """What is wrong with shipping `version` now, or `None`.

    `published` answers whether a version is on the index: `True`, `False`,
    or `None` when the index could not be asked.
    """
    previous = previous_version(changelog, version)
    if previous is None:
        return (
            f"the changelog does not lead with {version}, the version being "
            "released, so the release before it cannot be identified"
        )
    answer = published(previous)
    if answer is None:
        return (
            f"could not ask PyPI whether {previous} was published; refusing "
            "rather than passing a check that did not run"
        )
    if not answer:
        return (
            f"{previous} is the release before {version} and never reached "
            f"PyPI. Re-run the v{previous} release rather than shipping "
            f"{version} over the gap — 3.7.2 was lost this way."
        )
    return None


def on_pypi(version: str) -> bool | None:
    """Whether PyPI has this version: True, False, or None if unreachable."""
    url = f"https://pypi.org/pypi/{PACKAGE}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=20) as response:  # noqa: S310
            return json.load(response).get("info", {}).get("version") == version
    except urllib.error.HTTPError as error:
        return False if error.code == 404 else None
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from maintainability_audit import __version__

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    complaint = verdict(changelog, __version__, on_pypi)
    if complaint:
        print(f"::error::{complaint}")
        return 1
    print(f"the release before {__version__} is on PyPI")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
