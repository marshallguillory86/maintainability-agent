"""D63: the platform this runs on is claimed only where it is demonstrated.

`pyproject` named no operating system, CI runs Linux only, and two
documents implied Windows worked because path separators are
normalized. Nothing had ever executed on Windows: seven test files
create symlinks with no platform guard, and `os.symlink` needs
Developer Mode there, so the suite cannot reach the point of reporting
whether the product works.

Found by asking what happens for Windows users — the fourth time in two
days that a claim turned out to rest on a check that only ran where the
claim was true. The rule applied to JavaScript applies here: claim what you can demonstrate.
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
    body = _under_jobs(path.read_text(encoding="utf-8").splitlines())
    if not body:
        return []
    depth = len(body[0]) - len(body[0].lstrip())

    found: list[tuple[str, list[str]]] = []
    for line in body:
        indent = len(line) - len(line.lstrip())
        if indent == depth and line.rstrip().endswith(":"):
            found.append((line.strip().rstrip(":"), []))
        elif found:
            found[-1][1].append(line)
    return found


def _under_jobs(lines: list[str]) -> list[str]:
    """The significant lines beneath `jobs:`, blanks and comments dropped.

    Split out so `_jobs` reads as one loop: finding the section, skipping
    noise and grouping by indentation were three concerns in one function,
    which put it over this project's own cognitive threshold (D103).
    """
    try:
        start = next(i for i, line in enumerate(lines) if line.rstrip() == "jobs:")
    except StopIteration:
        return []
    kept: list[str] = []
    for line in lines[start + 1:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if kept and (len(line) - len(line.lstrip())) < (len(kept[0]) - len(kept[0].lstrip())):
            break  # out of `jobs:` entirely
        kept.append(line)
    return kept


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


def _local_gate_commands() -> list[str]:
    """Commands in the local gate script, continuations joined, comments dropped."""
    path = ROOT / "tools" / "local-gate.sh"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8").replace("\\\n", " ")
    return [
        " ".join(line.split()) for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _runs_whole_suite(command: str) -> bool:
    """`pytest` with flags only: no paths, and `-n auto` is a worker count.

    The D81/D87 rule: `echo pytest` and `pytest tests/one_file.py` both fail.
    """
    worker_count = re.compile(r"\s+-n\s+\S+")
    return bool(re.fullmatch(
        r"(?:python3?\s+-m\s+)?pytest(?:\s+-\S+)*", worker_count.sub("", command)))


def _local_gate_runs_the_suite() -> bool:
    """macOS evidence (2026-10-15): the enforced local gate, not a CI runner.

    Both scripts must exist and the gate must run the whole suite.
    """
    if not (ROOT / "tools" / "install-local-gate.sh").is_file():
        return False
    return any(_runs_whole_suite(c) for c in _local_gate_commands())


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
    # 2026-10-15 decision: `verify-macos` left CI so each test runs once,
    # on Linux. macOS evidence is the enforced local pre-push gate, which
    # runs the full suite on the maintainer's Mac. Linux still needs a CI
    # runner that really runs pytest.
    families = {"linux": ("ubuntu",)}
    missing = sorted(
        name for name, images in families.items()
        if not any(image in runner.lower() for runner in runners for image in images)
    )
    if not _local_gate_runs_the_suite():
        missing.append("macos")
    assert not missing, (
        f"the package claims {CLAIMED_PLATFORM}, which covers {missing}, and "
        "no CI runner or enforced local gate exercises it -- the claim rests "
        "on a platform nobody has run"
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
    D70 says so. `echo pytest` passes a bare word search, and so does a
    pytest invocation naming one file (D77, D87); `-n auto` is a worker
    count, not a path, and is stripped before matching.

    2026-10-15: `verify-macos` was removed from CI (each test runs once,
    on Linux). macOS evidence is the enforced local gate, a pre-push hook
    running the local gate script on the maintainer's Mac, so the same
    "actually runs the suite" property is asserted against that script.
    """
    assert (ROOT / "tools" / "install-local-gate.sh").is_file(), (
        "no installer; the gate is not enforced, so the macOS claim is unbacked")
    commands = _local_gate_commands()
    assert commands, "the local gate script is missing or empty"
    assert any(_runs_whole_suite(c) for c in commands), (
        "the local gate never runs the whole test suite -- a command naming "
        "specific paths, or merely containing the word, leaves the macOS "
        f"claim resting on a gate that proves nothing: {commands}"
    )
