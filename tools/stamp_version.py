"""Write the release version into every document that must state it.

The number lives once in code (D198): `maintainability_audit.__version__`.
It cannot live once in *prose*. Four documents have to state it, each for
a reason that survived an audit:

* `README.md` names the shipped version — it sat at 1.0.0 through five
  releases before that line was guarded (D45).
* `README.md` pins the GitHub Action example — `action.yml` runs
  `pip install -e "$GITHUB_ACTION_PATH"`, so the pin is the version a
  reader actually gets. It named v1.0.0 from 1.0.1 to 3.7.5.
* `docs/release-plan.md` records the last tagged version, and the release
  build refuses a tag that disagrees with it.
* `SECURITY.md` names the supported line, which moves on a minor rather
  than a patch.

Their tests are right and stay. What was wrong is that a person typed the
number into each one, and v3.7.9 was tagged and failed its release
because the release plan's row was missed — a check that only fires once
the tag exists, which is after the point anyone would have noticed.

**This does not improve `change_coupling`.** Those files still move
together, because they must. It removes the chore, not the coupling, and
saying so is the point: a metric measuring enforced consistency cannot
tell it apart from duplication, and this repository has both.

Run before committing the release, then commit the result:

    python3 tools/stamp_version.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _version() -> str:
    """The single source, read as text so this needs no install."""
    source = (ROOT / "src" / "maintainability_audit" / "__init__.py").read_text(
        encoding="utf-8"
    )
    match = re.search(r'__version__ = "([^"]+)"', source)
    if not match:
        raise SystemExit("no __version__ literal in src/maintainability_audit/__init__.py")
    return match.group(1)


def _supported_line(version: str) -> str:
    """`3.7.18` -> `3.7.x`: the policy moves on a minor, not a patch."""
    return f"{version.rsplit('.', 1)[0]}.x"


def _rules(version: str) -> list[tuple[Path, str, str]]:
    """(file, pattern, replacement) for every document that states it."""
    return [
        (ROOT / "README.md", r"Version \*\*[0-9][^*]*\*\*\.", f"Version **{version}**."),
        (
            ROOT / "README.md",
            r"maintainability-agent@v[0-9][0-9.]*",
            f"maintainability-agent@v{version}",
        ),
        (
            ROOT / "docs" / "release-plan.md",
            r"\| Last tagged version \| v[0-9][0-9.]* \|",
            f"| Last tagged version | v{version} |",
        ),
        # Anchored to the table row, not the bare version. An unanchored
        # pattern rewrote this file's own history — "an audit found this
        # table still naming `0.1.x` eight release lines later" became
        # "naming `3.7.x`", erasing the evidence for the entry that
        # explains why the row is guarded at all.
        (
            ROOT / "SECURITY.md",
            r"\| `[0-9]+\.[0-9]+\.x` \| ✅ \|",
            f"| `{_supported_line(version)}` | ✅ |",
        ),
        (
            ROOT / "SECURITY.md",
            r"\| < `[0-9]+\.[0-9]+` \| ❌ \|",
            f"| < `{version.rsplit('.', 1)[0]}` | ❌ |",
        ),
    ]


def main() -> int:
    version = _version()
    changed: list[str] = []
    for path, pattern, replacement in _rules(version):
        before = path.read_text(encoding="utf-8")
        after, count = re.subn(pattern, replacement, before)
        if not count:
            # A document that no longer matches is one this tool would
            # silently stop stamping — the failure it exists to prevent.
            # Refuse rather than report success.
            print(f"no match for {pattern!r} in {path.name}", file=sys.stderr)
            return 1
        if after != before:
            path.write_text(after, encoding="utf-8")
            changed.append(f"{path.relative_to(ROOT)} ({count})")
    print(f"version {version}")
    print("updated: " + (", ".join(changed) if changed else "nothing, already current"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
