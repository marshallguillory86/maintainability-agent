"""Shared fixtures.

The population floors (ADR 005) are deliberately **not** configurable in
production: a floor a repository could lower is not a floor, and P2 promises
one rubric applied identically everywhere. That leaves tests of rubric
mechanics — rollup arithmetic, grade gating, evidence states — needing trees
larger than the corpus minimum for reasons that have nothing to do with what
they are testing.

So the floors are lifted for the suite by default and restored explicitly
where the floors themselves are the subject. Two guards keep that from
becoming a hole big enough to hide a regression in:

* `test_population_floors.py` and `test_scan_scope.py` opt back in via the
  `real_population_floors` fixture and exercise the shipped values;
* `test_the_shipped_floors_are_the_corpus_minima` asserts the production
  defaults are what the corpus says, so lifting them in tests cannot drift
  the values that ship.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from maintainability_audit import _formula

CORPUS = Path(__file__).resolve().parent.parent / "tools" / "calibration" / "corpus.json"

# The real one, captured at import before `_git_ignores_developer_configuration`
# replaces `HOME`. Read afterwards it would return the empty session home, and
# the guard below would assert nothing while appearing to pass.
DEVELOPER_HOME = Path(os.path.expanduser("~")).resolve()

# Captured at import, before any fixture touches the table, so the assertions
# below compare against what the package actually ships.
SHIPPED_FLOORS = dict(_formula.POPULATION_FLOORS)


@pytest.fixture(autouse=True)
def _isolate_user_config(tmp_path, monkeypatch):
    """No test may read or write the developer's real XDG config or state."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg-state"))


@pytest.fixture(autouse=True)
def _lift_population_floors(request, monkeypatch):
    """Let rubric tests use small trees, unless they asked for the real floors."""
    if "real_population_floors" in request.fixturenames:
        return
    monkeypatch.setattr(
        _formula, "POPULATION_FLOORS", dict.fromkeys(SHIPPED_FLOORS, 0), raising=True
    )


@pytest.fixture
def real_population_floors(monkeypatch):
    """Restore the shipped floors for tests that are about the floors."""
    monkeypatch.setattr(_formula, "POPULATION_FLOORS", dict(SHIPPED_FLOORS), raising=True)
    return SHIPPED_FLOORS


def test_the_shipped_floors_are_the_corpus_minima() -> None:
    """The suite lifts the floors; this pins what it lifted.

    Without it, a floor could be raised above a calibration member's
    population and no test would notice, because every other test runs
    with the floors disabled.
    """
    repos = json.loads(CORPUS.read_text(encoding="utf-8"))["repos"]
    assert SHIPPED_FLOORS["files_scanned"] <= min(r["source_files"] for r in repos)
    assert SHIPPED_FLOORS["declarations_scanned"] <= min(r["declarations"] for r in repos)
    assert all(value > 0 for value in SHIPPED_FLOORS.values()), (
        "a zero floor ships nothing; the hello-world A+ comes straight back"
    )


@pytest.fixture(scope="session", autouse=True)
def _git_never_maintains_the_fixtures() -> Iterator[None]:
    """Stop git's background maintenance writing into fixture repos.

    Several tests assert that an audit leaves the tree it audited byte
    for byte unchanged. `git commit` schedules `git maintenance run
    --auto`, which **detaches**, so the maintenance a fixture's own
    commit scheduled lands milliseconds later -- inside the window
    between those tests' before and after snapshots -- and writes
    `.git/objects/maintenance.lock`.

    That is the fixture's git, not the product's. D71 stopped the
    product from triggering maintenance (`run_git` prepends the same two
    settings to every command it builds), and macOS CI kept failing
    afterwards because the commit that *set up* the repository had
    already scheduled it. Same commit, three CI runs, two failures and
    one pass: a race, not a regression.

    Session-scoped and via `GIT_CONFIG_*` so it reaches every git in the
    suite, including the ones spawned deep inside the product, without
    each fixture having to remember. `git_env()` does not scrub these --
    it scrubs the location overrides (`GIT_DIR` and siblings), which
    redirect a command at another repository; these only turn off
    housekeeping.
    """
    # Settings that must hold no matter what any configuration file says,
    # which is why they go through `GIT_CONFIG_COUNT` -- the one layer no
    # config file can outrank. Each is here for its own reason:
    #
    # * `gc.auto` and `maintenance.auto` are on by git's *built-in
    #   defaults* (6700 and true), not by a config file, so isolating
    #   configuration cannot turn them off. See this docstring.
    # * `commit.gpgsign` and `tag.gpgsign` are not about the developer's
    #   machine -- `_git_ignores_developer_configuration` already handles
    #   that class. They are here because a fixture repository has no
    #   signing key, so an attempted signature cannot succeed, it can only
    #   abort the command. A test that supplies its own hostile global
    #   config to exercise something else should not have to know that.
    settings = (
        ("gc.auto", "0"),
        ("maintenance.auto", "false"),
        ("commit.gpgsign", "false"),
        ("tag.gpgsign", "false"),
    )
    previous = {
        name: os.environ.get(name)
        for name in ("GIT_CONFIG_COUNT", *(
            f"GIT_CONFIG_{part}_{index}"
            for index in range(len(settings)) for part in ("KEY", "VALUE")
        ))
    }
    os.environ["GIT_CONFIG_COUNT"] = str(len(settings))
    for index, (key, value) in enumerate(settings):
        os.environ[f"GIT_CONFIG_KEY_{index}"] = key
        os.environ[f"GIT_CONFIG_VALUE_{index}"] = value
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


@pytest.fixture(scope="session", autouse=True)
def _git_ignores_developer_configuration(tmp_path_factory) -> Iterator[None]:
    """No git in this suite reads the developer's own configuration.

    The suite creates fixture repositories and commits into them. Every one
    of those commands inherited whatever the developer had configured
    globally, so the suite's result depended on the machine it ran on. CI
    never noticed, because a runner has almost no global configuration —
    which is exactly why this went unseen until a correctly configured
    laptop ran it.

    Two ambient settings were observed breaking it, and they are worth
    naming because they are different in kind:

    * `commit.gpgsign=true` made every fixture commit attempt a signature:
      175 failures and 28 errors.
    * `init.templateDir` installed the developer's own `pre-commit` hook
      into every repository `git init` created, and that hook rejected the
      `t@t` address the fixtures commit under. It fires *before* signing,
      so fixing signing alone left the suite red.

    `docs/machine-setup.md` section 2 instructs developers to turn on
    global signing, so following this project's own setup guide broke its
    own build. That is the defect, and patching the two settings named
    above would only have been the two instances of it — `core.hooksPath`,
    `core.excludesfile`, `commit.template` and an aliased `commit` all
    reach a fixture the same way.

    So this isolates the *class* rather than the two instances: an empty
    `HOME` for the session, so git's global lookup finds nothing, and
    `GIT_CONFIG_NOSYSTEM` for the system file. Environment rather than
    command arguments, because it reaches the gits spawned deep inside the
    product without each of the suite's 37 commit sites having to remember;
    session scope, because a fixture repository outlives a single test.

    **`HOME`, deliberately, and not `GIT_CONFIG_GLOBAL`.** Pointing
    `GIT_CONFIG_GLOBAL` at an empty file isolates just as well but does not
    *compose*: it outranks `HOME`, so a test that sets up its own fake home
    and runs `git config --global` writes into this session's shared file
    instead of its own, and every test after it inherits the setting. That
    is not hypothetical — it is what `test_fixture_commits_ignore_ambient_
    global_signing` did, turning signing back on mid-session and failing 166
    tests while each file passed alone. Isolating at `HOME` leaves the
    override that tests actually use free to nest.

    `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` are cleared rather than set,
    for the same reason: either one arriving from an outer environment would
    outrank `HOME` and silently defeat all of this.

    `test_no_git_in_this_suite_reads_developer_configuration` below fails
    if this stops holding.
    """
    home = tmp_path_factory.mktemp("git-isolation-home")
    names = ("HOME", "USERPROFILE", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM",
             "GIT_CONFIG_NOSYSTEM")
    previous = {name: os.environ.get(name) for name in names}
    os.environ["HOME"] = str(home)
    os.environ["USERPROFILE"] = str(home)
    os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
    os.environ.pop("GIT_CONFIG_GLOBAL", None)
    os.environ.pop("GIT_CONFIG_SYSTEM", None)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def test_no_git_in_this_suite_reads_developer_configuration(tmp_path: Path) -> None:
    """The isolation above holds, for any setting rather than a listed few.

    Asserting on the *origin* of every setting is what makes this a guard
    against the class. A test that only checked `commit.gpgsign` would pass
    while `init.templateDir` was still installing hooks — which is precisely
    how the first attempt at this fix was wrong.
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
