"""The suite's own isolation, tested where the tests actually run.

Every assertion here is about the harness rather than the product: that a
fixture repository cannot read the developer's git configuration, and that
a spawned subprocess imports the same package this process did. Both are
properties of `conftest.py`, and both were *written* in `conftest.py` —
where pytest never collected them, because a conftest is a plugin module
and not a test module. `python_files` defaults to `test_*.py` and
`*_test.py`; `conftest.py` matches neither.

So the guard for the git-isolation fixture, with its careful docstring
about how the first attempt at that fix had been too narrow, had never
run once. It is the failure mode this project keeps meeting in new
costumes — a check narrower than the promise, a guard that reads one
direction, an assertion nothing executes — and the cheapest of the three
to miss, because a test that is never collected cannot go red.

`test_the_isolation_guards_are_collected` below is the guard on the
guards: it fails if these move back somewhere pytest will not look.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

DEVELOPER_HOME = Path(os.path.expanduser("~")).resolve()
"""Captured at import, which is before the session fixture moves `HOME`.

Reading it later would return the fixture's temporary home and the leak
check below would compare against the wrong string — passing always, which
is the same defect as not being collected.
"""


def test_no_git_in_this_suite_reads_developer_configuration(tmp_path: Path) -> None:
    """The isolation holds, for any setting rather than a listed few.

    Asserting on the *origin* of every setting is what makes this a guard
    against the class. A test that only checked `commit.gpgsign` would pass
    while `init.templateDir` was still installing hooks — which is precisely
    how the first attempt at that fix was wrong.
    """
    repo = tmp_path / "probe"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

    origins = subprocess.run(
        ["git", "config", "--list", "--show-origin"],
        cwd=repo, text=True, capture_output=True, check=True,
    ).stdout
    leaked = [line for line in origins.splitlines() if str(DEVELOPER_HOME) in line]
    assert not leaked, f"developer configuration reached a fixture git: {leaked}"

    hooks = repo / ".git" / "hooks"
    installed = [entry.name for entry in hooks.iterdir() if entry.suffix != ".sample"]
    assert not installed, (
        f"init.templateDir installed hooks into a fixture repository: {installed}"
    )

    # Not "unset": `_git_never_maintains_the_fixtures` sets these to false
    # unconditionally. The requirement is that a fixture never *tries* to
    # sign, whichever layer delivers that.
    for setting in ("commit.gpgsign", "tag.gpgsign"):
        value = subprocess.run(
            ["git", "config", "--get", setting],
            cwd=repo, text=True, capture_output=True, check=False,
        ).stdout.strip()
        assert value in ("", "false"), (
            f"a fixture repository would attempt to sign: {setting}={value}"
        )


def test_a_spawned_child_imports_the_same_package_this_process_did() -> None:
    """Parent and child agree on which copy is under test.

    The suite makes assertions about CLI behaviour by spawning
    `python -m maintainability_audit`. Those assertions are only about this
    working tree if the child resolves the same package the test process
    imported, and for a while nothing checked that:

    - Where the package is installed with `pip install --user`, the `HOME`
      move in `conftest` deleted the child's route to it entirely. Tests
      failed with `No module named maintainability_audit` — a message that
      names imports, in tests whose subject is not imports, on a laptop
      while CI stayed green because a virtualenv's site-packages is not
      `HOME`-derived.
    - The quieter half is that a child could instead have found a
      *different* copy — a stale wheel, an older `pip install` — and
      passed. Every subprocess assertion would then have described a build
      the rest of the suite never measured.

    Comparing the resolved file rather than the version catches both: two
    copies of the same version are still two copies.
    """
    child = subprocess.run(
        [sys.executable, "-c",
         "import maintainability_audit as m; print(m.__file__)"],
        text=True, capture_output=True, check=False,
    )

    assert child.returncode == 0, (
        "a spawned child could not import the package under test:\n"
        f"{child.stderr}"
    )

    import maintainability_audit

    assert Path(child.stdout.strip()) == Path(maintainability_audit.__file__), (
        "a spawned subprocess imported a different copy of the package than "
        f"this test process: child {child.stdout.strip()!r}, parent "
        f"{maintainability_audit.__file__!r}"
    )


def test_the_isolation_guards_are_collected() -> None:
    """No isolation guard may live where pytest does not collect it.

    The guard on the guards, and the reason this file exists. Both tests
    above sat in `conftest.py` and never ran; the suite was green for
    months with its own harness unverified. Asserting that `conftest.py`
    defines no `test_`-prefixed function encodes the rule rather than the
    instance, so the next one written in the convenient place fails loudly
    instead of silently never running.
    """
    conftest = Path(__file__).with_name("conftest.py").read_text()
    stranded = [
        line.split("(")[0].removeprefix("def ").strip()
        for line in conftest.splitlines()
        if line.startswith("def test_")
    ]

    assert not stranded, (
        f"{stranded} are defined in conftest.py, which pytest loads as a "
        "plugin and never collects as a test module, so they cannot fail. "
        "Move them into a test_*.py file."
    )
