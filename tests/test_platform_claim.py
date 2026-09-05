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
import re
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


def _jobs(path: Path) -> list[tuple[str, list[str]]]:
    """Each job in a workflow, as ``(name, body lines)``.

    Read by indentation rather than with a YAML parser, because the suite
    is forbidden to import `yaml` — that dependency is for catalog regen,
    and keeping it off the test extra keeps a test install light. The same
    indentation walk `test_the_macos_runner_actually_runs_the_suite` uses
    below, which is also why it stays consistent with this file.

    A job is a key one level under `jobs:`; its body runs until the next
    line at or above its own indentation.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.rstrip() == "jobs:")
    except StopIteration:
        return []

    found: list[tuple[str, list[str]]] = []
    depth: int | None = None
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if depth is None and line.rstrip().endswith(":"):
            depth = indent
        if depth is None:
            continue
        if indent < depth:
            break  # out of `jobs:` entirely
        if indent == depth and line.rstrip().endswith(":"):
            found.append((line.strip().rstrip(":"), []))
        elif found:
            found[-1][1].append(line)
    return found


def _gates_on_windows(body: list[str]) -> bool:
    """Whether this job runs Windows *and* something depends on the result.

    `continue-on-error` is the whole distinction. A job carrying it gates
    no merge and stands behind nothing, so running an unclaimed platform
    there is a question — the only way to replace an unknown with a list
    without claiming the platform first. A job that gates something is an
    answer, and an answer needs the classifier to move with it.
    """
    runs_windows = any(
        "windows" in line.lower() for line in body if "runs-on:" in line
    )
    non_blocking = any(
        line.split(":", 1)[1].strip() == "true"
        for line in body if line.strip().startswith("continue-on-error:")
    )
    return runs_windows and not non_blocking


def test_ci_runs_only_platforms_the_package_claims() -> None:
    """If a Windows runner appears, the claim has to move with it —
    unless the job claims nothing at all. See `_gates_on_windows`."""
    workflows = list((ROOT / ".github" / "workflows").glob("*.yml"))
    assert workflows, "no workflows found; this check has nothing to read"
    runners = {
        line.split("runs-on:", 1)[1].strip()
        for path in workflows
        for line in path.read_text(encoding="utf-8").splitlines()
        if "runs-on:" in line
    }
    gating = sorted(
        f"{path.name}:{job}"
        for path in workflows
        for job, body in _jobs(path)
        if _gates_on_windows(body)
    )
    assert not gating, (
        f"{gating} run a platform outside {CLAIMED_PLATFORM} in a job that "
        "gates something. Either the classifier grows with the evidence "
        "behind it, or the job becomes `continue-on-error: true` — a probe, "
        "which claims nothing"
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
        # Not `"pytest" in joined`. That was the first spelling and an
        # audit named what it accepts: `echo pytest` passes, and so does
        # a pytest invocation naming one file, which would let the job
        # stop running the product's suite without this noticing. D77
        # had just taught the same lesson one job over -- a comment is
        # not an install (D87).
        runs = [
            line.split("run:", 1)[1].strip()
            for line in body if "run:" in line
        ]
        suite = [
            command for command in runs
            if re.fullmatch(r"(?:python3?\s+-m\s+)?pytest(?:\s+-\S+)*", command)
        ]
        assert suite, (
            "the macOS job never runs the whole test suite -- a command "
            "naming specific paths, or merely containing the word, leaves "
            f"the POSIX claim resting on a job that proves nothing: {runs}"
        )
