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

    # The half this test was missing. Forbidding a Windows runner is not
    # a demonstration that POSIX works -- `Operating System :: POSIX`
    # covers macOS and Linux, and for as long as this check existed the
    # evidence behind it was one Linux image. An audit walked straight
    # through that: the claim was wider than the thing checking it, the
    # fourth time this project has shipped that shape.
    families = {"linux": ("ubuntu",), "macos": ("macos",)}
    missing = sorted(
        name for name, images in families.items()
        if not any(image in runner.lower() for runner in runners for image in images)
    )
    assert not missing, (
        f"the package claims {CLAIMED_PLATFORM}, which covers {missing}, and "
        "no CI runner exercises it -- the claim rests on a platform nobody "
        "has run"
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


def test_the_macos_runner_actually_runs_the_suite() -> None:
    """D81: a `runs-on` line is not a demonstration.

    `test_ci_runs_only_platforms_the_package_claims` requires a runner
    whose image name contains `macos`. An audit pointed out what that
    accepts: `runs-on: macos-latest` with `run: true` satisfies it, and
    POSIX is "demonstrated" by a job that does nothing. Same shape as
    the 292-result baseline this project spent a day removing -- a green
    box whose contents do not mean the claim.

    What the second platform is *for* is running the suite, so that is
    what is checked. Deliberately not lint, coverage or CVE scanning:
    those are properties of the project rather than of the platform, and
    D70 says so.
    """
    text = (ROOT / ".github" / "workflows" / "quality-gates.yml").read_text(
        encoding="utf-8")
    lines = text.splitlines()

    starts = [
        index for index, line in enumerate(lines)
        if "runs-on:" in line and "macos" in line.lower()
    ]
    assert starts, "no macOS runner; the claim rests on one platform again"

    for start in starts:
        # The job body runs until the next line at or below the depth of
        # the `runs-on:` key itself.
        depth = len(lines[start]) - len(lines[start].lstrip())
        body: list[str] = []
        for line in lines[start + 1:]:
            if line.strip() and (len(line) - len(line.lstrip())) < depth:
                break
            body.append(line)
        joined = "\n".join(body)
        assert "pytest" in joined, (
            "the macOS job never runs the test suite, so the POSIX claim "
            f"rests on a job that proves nothing:\n{joined[:400]}"
        )
