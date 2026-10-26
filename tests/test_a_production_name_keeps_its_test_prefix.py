"""A production file whose name starts with `test` keeps its whole name (D233).

`subject_stem` applied pFUnit's camelCase rule — `testFooBar_mod.F90`
covers `fooBar_mod.F90` — to every file in every language. A production
file named `test-rp.mjs`, `testing.mjs` or `tester.py` lost its first four
letters, so its stem never met the test that covers it: the file was
reported as an unpaired fail-band unit, the import route missed it too
(it compares against the same stem), and on the repository where it was
found it alone held testability at its 4.0 cap while the work order asked
for a test that already existed.

The rule is pFUnit's, so it applies only to a Fortran file that is itself
a test. Every other name is left whole.
"""

from __future__ import annotations

import pytest

from maintainability_audit._test_pairing import subject_stem


@pytest.mark.parametrize(("production", "covering_test"), [
    ("scripts/test-rp.mjs", "tests/test-rp.test.mjs"),
    ("src/tester.py", "tests/test_tester.py"),
    ("src/testing.mjs", "src/testing.spec.mjs"),
    ("lib/testbed.ts", "lib/testbed.test.ts"),
])
def test_a_production_file_named_test_something_pairs_with_its_test(production: str, covering_test: str) -> None:
    assert subject_stem(production) == subject_stem(covering_test)


@pytest.mark.parametrize(("path", "stem"), [
    ("scripts/test-rp.mjs", "test-rp"),
    ("src/tester.py", "tester"),
    ("src/testing.mjs", "testing"),
    # A Fortran *production* file is not a pFUnit test either.
    ("src/testing_mod.f90", "testing"),
])
def test_the_stem_of_a_production_file_is_its_own_name(path: str, stem: str) -> None:
    assert subject_stem(path) == stem


def test_the_pfunit_convention_still_pairs() -> None:
    """The rule that caused it keeps working where it belongs."""
    assert subject_stem("tests/testFooBar_mod.F90") == "foobar"
    assert subject_stem("tests/testGravity_mod.F90") == subject_stem("src/gravity_mod.f90")
