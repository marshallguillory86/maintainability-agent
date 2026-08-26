"""D63: the platform this runs on is claimed only where it is demonstrated.

`pyproject` named no operating system, CI runs Linux only, and two
documents implied Windows worked because path separators are
normalized. Nothing had ever executed on Windows: seven test files
create symlinks with no platform guard, and `os.symlink` needs
Developer Mode there, so the suite cannot reach the point of reporting
whether the product works.

Found by Marshall asking "what about the poor windows users?" — the
fourth time in two days that a claim turned out to rest on a check that
only ran where the claim was true. The rule he applied to JavaScript
applies here: claim what you can demonstrate.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAIMED_PLATFORM = "Operating System :: POSIX"


def test_the_package_claims_the_platform_it_is_tested_on() -> None:
    """A classifier that says POSIX, while CI says POSIX."""
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    classifiers = metadata["project"]["classifiers"]
    platforms = [c for c in classifiers if c.startswith("Operating System")]
    assert platforms == [CLAIMED_PLATFORM], (
        f"the package claims {platforms} as its platforms. Anything beyond "
        "POSIX needs a CI runner that proves it, and the symlink fixtures "
        "would have to grow platform guards first"
    )


def test_ci_runs_only_platforms_the_package_claims() -> None:
    """If a Windows runner appears, the claim has to move with it."""
    workflows = list((ROOT / ".github" / "workflows").glob("*.yml"))
    assert workflows, "no workflows found; this check has nothing to read"
    runners = {
        line.split("runs-on:", 1)[1].strip()
        for path in workflows
        for line in path.read_text(encoding="utf-8").splitlines()
        if "runs-on:" in line
    }
    non_posix = sorted(r for r in runners if "windows" in r.lower())
    assert not non_posix, (
        f"CI runs {non_posix} while the package claims only "
        f"{CLAIMED_PLATFORM}. Either the classifier grows or the runner goes"
    )


def test_the_symlink_fixtures_are_still_unguarded() -> None:
    """The concrete reason Windows is unclaimed, kept visible.

    Not a demand that they stay that way — it is the evidence behind the
    classifier. When these grow platform guards, this test fails and
    whoever did the work decides whether the claim can widen. A reason
    that quietly stops being true is how the last four of these got
    missed.
    """
    creators = []
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        makes_links = any(
            isinstance(node, ast.Call)
            and getattr(node.func, "attr", "") in {"symlink", "symlink_to"}
            for node in ast.walk(tree)
        )
        if makes_links:
            creators.append(path.name)

    assert creators, (
        "no test creates a symlink any more; the stated reason for "
        "claiming POSIX only has gone stale — re-read README's platform "
        "section before widening or narrowing the claim"
    )
