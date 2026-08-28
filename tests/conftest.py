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
from collections.abc import Iterator
from pathlib import Path

import pytest

from maintainability_audit import _formula

CORPUS = Path(__file__).resolve().parent.parent / "tools" / "calibration" / "corpus.json"

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
    settings = (("gc.auto", "0"), ("maintenance.auto", "false"))
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
