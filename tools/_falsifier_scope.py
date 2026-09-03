"""What the falsifier gate proves, separated from how it proves it.

`prove_falsifiers.py` crossed this project's 500-line file gate when the
third selector arrived, and the seam it wanted was already there: deciding
*which* tests a change is answerable for is a different job from reverting
a tree and running them. The selectors live here; the proving machinery,
the register reading and the CLI stay next door.

Three routes reach the gate, and each one exists because work arrived by a
path the previous route could not see:

1. Register entries citing their closing tests — the original.
2. Added `tests/*_class.py` population falsifiers.
3. Test files a change adds, and tests it adds to files that already
   existed. The languages shipped through neither of the first two: C,
   C++, C#, Fortran and fixed-form Fortran arrived as feature increments
   with roughly 300 tests CI never watched fail.

Everything here reads git and returns paths or pytest node ids. Nothing
here runs a test, so it is cheap to call and safe to call twice.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TESTS = "tests/"

#: Marks a test that deliberately covers behaviour older than this change.
#: Such a test cannot fail at the base and saying so is honest; leaving the
#: gate to infer it is not.
COVERS_EXISTING = "Covers existing behaviour:"


def git(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(  # noqa: S603 - argv list, never a shell
        ["git", *args], cwd=cwd, text=True, capture_output=True, check=False,
        timeout=120,
    )
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def is_class_falsifier(path: str) -> bool:
    """A ``tests/*_class.py`` population-derived falsifier file."""
    return path.startswith(TESTS) and path.endswith("_class.py")


def _is_test_module(path: str) -> bool:
    return (
        path.startswith(TESTS)
        and Path(path).name.startswith("test_")
        and path.endswith(".py")
    )


def added_class_falsifiers(base: str) -> list[str]:
    """`tests/*_class.py` files this change adds, in sorted order."""
    added = git("diff", "--name-only", "--diff-filter=A", base, "HEAD").splitlines()
    return sorted(path for path in added if is_class_falsifier(path))


def added_test_files(base: str) -> list[str]:
    """Every ``tests/test_*.py`` this change adds, class falsifiers aside.

    Added files only: a modified file may defend a fix older than this
    base, and proving it would be a false accusation.
    """
    added = git("diff", "--name-only", "--diff-filter=A", base, "HEAD").splitlines()
    return sorted(
        path for path in added
        if _is_test_module(path) and not is_class_falsifier(path)
    )


def added_tests_in_modified_files(base: str) -> list[str]:
    """Test functions this change adds to a test file that already existed.

    The third hole, and the one this gate walked into itself. The
    added-files-only rule above is right about the tests already in a
    modified file — they may defend older work. It is not right about a
    test the diff *adds* to that file, which is exactly as new as one
    arriving in a new file.

    1.8.2 added a guard to an existing `tests/test_readme_claims.py`. CI
    printed a pass for this gate while proving nothing about it, and the
    guard was mutation-tested by hand instead — the manual step this gate
    exists to replace. Worse, the hand mutation spliced a state that never
    existed in history and appeared to prove a guard that did not falsify.

    Read from the diff rather than by comparing whole files, so a function
    that merely moved does not read as new.
    """
    modified = git("diff", "--name-only", "--diff-filter=M", base, "HEAD").splitlines()
    node_ids: list[str] = []
    for path in sorted(modified):
        if not _is_test_module(path) or is_class_falsifier(path):
            continue
        diff = git("diff", "--unified=0", base, "HEAD", "--", path)
        node_ids += [
            f"{path}::{match.group(1)}"
            for match in re.finditer(r"^\+\s*(?:async\s+)?def (test_\w+)\b", diff, re.M)
        ]
    return sorted(set(node_ids))


def function_source(source: str, name: str) -> str:
    """The text of one test function, for reading its own exemption."""
    body = re.search(
        rf"^\s*(?:async\s+)?def {re.escape(name)}\b.*?(?=^\s*(?:async\s+)?def |\Z)",
        source,
        re.M | re.S,
    )
    return body.group() if body else ""


def tests_in(source: str, filename: str) -> list[str]:
    """Every ``test_`` function a file defines, as pytest node ids."""
    return [
        f"{TESTS}{filename}::{match.group(1)}"
        for match in re.finditer(r"^\s*(?:async\s+)?def (test_\w+)\b", source, re.M)
    ]
