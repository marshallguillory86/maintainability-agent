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
