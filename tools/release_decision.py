#!/usr/bin/env python3
"""Decide whether this run of `release.yml` releases, and whether it cuts the tag.

A merge to main that changes `__version__` is the release: nobody pushes a
tag by hand. Until 5.1.2 the tag push was the only trigger, so a merged
version bump shipped nothing until someone ran `git push origin vX.Y.Z`,
and that step needed a person every time.

Two workflows read it. `cut-release.yml` runs on every merge and runs no
tests (a merge runs only the deploy); when the merge bumped the version it
dispatches `release.yml` on main, because a dispatch is the one event a
GITHUB_TOKEN can start another workflow with. `release.yml` reads it again
to decide what that run does.

The table, one row per way either workflow can start:

- push to main, `v<version>` not tagged yet: release (`cut-release.yml`
  dispatches it).
- push to main, `v<version>` already tagged: nothing. Every merge that
  does not bump the version lands here.
- `workflow_dispatch` on main, `v<version>` not tagged yet: release, then
  cut the tag after PyPI has accepted the upload. This is the merged bump.
- `workflow_dispatch` on main, already tagged: publish again without
  tagging; PyPI skips a version it already has (recovery).
- `workflow_dispatch` on any other ref: release is attempted, never
  tagged, and the build refuses a commit that is not on main.
- push of a tag that matches the packaged version: release the existing
  tag, which is how an interrupted release is re-run.
- push of a tag that does not match: refuse, naming both numbers. PyPI
  uploads cannot be replaced, so the wrong number must stop before a build.
- any other push: nothing.

Run from the workflow it reads `GITHUB_EVENT_NAME`, `GITHUB_REF`, the
version literal and the remote's tags, and writes `release`, `create_tag`
and `tag` to `GITHUB_OUTPUT`. The tags come from `git ls-remote`, not from
the checkout, because a shallow clone has none and would release forever.
"""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "maintainability_audit" / "__init__.py"
MAIN = "refs/heads/main"
TAG_PREFIX = "refs/tags/"


def decide(event: str, ref: str, version: str, tags: Iterable[str]) -> dict[str, object]:
    """The release decision for one workflow run. Pure, so the table is testable."""
    tag = f"v{version}"
    if event == "workflow_dispatch":
        return {"release": True, "create_tag": ref == MAIN and tag not in set(tags), "tag": tag}
    if event == "push" and ref.startswith(TAG_PREFIX):
        pushed = ref[len(TAG_PREFIX):]
        if pushed != tag:
            raise ValueError(f"tag {pushed} does not match the packaged version {version}")
        return {"release": True, "create_tag": False, "tag": tag}
    if event == "push" and ref == MAIN and tag not in set(tags):
        return {"release": True, "create_tag": True, "tag": tag}
    return {"release": False, "create_tag": False, "tag": tag}


def packaged_version() -> str:
    """The one version literal (D198), read before anything is built."""
    match = re.search(r'__version__ = "([^"]+)"', SOURCE.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"no __version__ literal in {SOURCE}")
    return match.group(1)


def remote_tags() -> list[str]:
    """Tag names on origin. A failure to ask raises: unknown is not untagged."""
    listing = subprocess.run(
        ["git", "ls-remote", "--tags", "--refs", "origin"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    return [line.split(TAG_PREFIX, 1)[1] for line in listing.splitlines() if TAG_PREFIX in line]


def main() -> int:
    try:
        decision = decide(
            os.environ["GITHUB_EVENT_NAME"], os.environ["GITHUB_REF"], packaged_version(), remote_tags(),
        )
    except ValueError as error:
        print(f"::error::{error}")
        return 1
    lines = [f"{key}={str(value).lower() if isinstance(value, bool) else value}" for key, value in decision.items()]
    print("\n".join(lines))
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
