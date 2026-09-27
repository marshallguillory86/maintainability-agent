"""A behaviour suite under `acceptance/` is test code, not production code.

Found auditing Scrollwork: more than sixty suites in `acceptance/<suite>/
run.mjs`, each importing and driving the production handlers, were
graded as production. 18 of 25 duplicate blocks and most oversized files
were in them, and 106 production files were reported unpaired while those
same suites covered `functions/` at 98% — worse debt and worse testing
from one misclassification.

The names added are the unambiguous ones: `acceptance`, `e2e`, `cypress`
and `playwright`. `integration` and `features` are left out on purpose,
because each is also an ordinary production package name — a feature-
flag module, an integrations layer — and misreading production as test
flatters the grade, which is the direction this project refuses.

There were also two lists. `_discovery` read `testing/` as test code and
`is_test_path` did not, so provenance and pairing disagreed about
lapack's `TESTING/`. One list now feeds both.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from maintainability_audit._discovery import _is_test
from maintainability_audit._metrics_types import TEST_DIRECTORY_NAMES, FileMetric, is_test_path
from maintainability_audit._test_pairing import describe_tdd

BEHAVIOUR_SUITES = ("acceptance", "e2e", "cypress", "playwright")


@pytest.mark.parametrize("directory", BEHAVIOUR_SUITES)
def test_a_behaviour_suite_directory_holds_tests(directory: str) -> None:
    path = f"{directory}/login/run.mjs"

    assert is_test_path(path)
    assert _is_test(path)


@pytest.mark.parametrize("path", [
    "integration/stripe.py",
    "features/flags.py",
    "src/acceptance_rules.py",
    "src/e2e_config.js",
])
def test_an_ambiguous_or_merely_similar_name_stays_production(path: str) -> None:
    """A whole path segment, and only a name that means tests everywhere."""
    assert not is_test_path(path)
    assert not _is_test(path)


def test_both_classifiers_read_one_list() -> None:
    """Provenance and pairing must agree on every directory name."""
    for name in TEST_DIRECTORY_NAMES:
        path = f"{name}/thing.py"
        assert is_test_path(path) == _is_test(path) is True, name
    assert "testing" in TEST_DIRECTORY_NAMES


@pytest.mark.parametrize("name", ["fixtures", "src", "lib", "integration", "features", "tools"])
def test_the_classifiers_agree_outside_the_list_too(name: str) -> None:
    """Agreement only over names already in the list cannot see a second list."""
    path = f"{name}/thing.py"

    assert is_test_path(path) == _is_test(path), name


def test_a_handler_driven_by_an_acceptance_suite_is_paired(tmp_path: Path) -> None:
    """The closing test the defect asked for, on Scrollwork's own shape."""
    suite = tmp_path / "acceptance" / "login"
    suite.mkdir(parents=True)
    (suite / "run.mjs").write_text(
        "import { handle } from '../../src/handler.js'\nhandle()\n", encoding="utf-8"
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "handler.js").write_text("export function handle() {}\n", encoding="utf-8")

    described = describe_tdd(
        tmp_path,
        [FileMetric(path="src/handler.js", lines=1, status="ok"),
         FileMetric(path="acceptance/login/run.mjs", lines=2, status="ok")],
        [],
    )

    assert described["production_files"] == 1, "the suite was counted as production"
    assert described["paired_production_files"] == 1
