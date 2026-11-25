"""A Swift test is a test: `FooTests.swift`, and the `FooTests/` folder an Xcode test target lives in.

Found grading an iOS app (2026-11-25): 138 files in `Bible ReaderTests/`, every one named `SomethingTests.swift`
and importing `Testing`, were read as production code. Test presence scored 0.0, the testability
aspect 2.0, and the grade was held at C while the suite ran 1,116 tests. The
rules only knew `tests/`, `test_*` and `*_test`, which are the Python and JavaScript shapes, so the
language's own convention was invisible and the tool graded a tested repository as untested.

The two shapes added are Xcode's and XCTest's, and each is anchored so a production name cannot
match by accident: the suffix is a capitalised `Tests` or `Test` on a `.swift` file, and the folder
must end in a capitalised `Tests` and hold a `.swift` file. `Contest.swift`, `Latest.swift` and a
folder of `.py` files called `ApiTests/` are not touched.
"""

from __future__ import annotations

from pathlib import Path

from maintainability_audit._discovery import _is_test
from maintainability_audit._metrics_types import is_test_path
from maintainability_audit.config import load_config
from maintainability_audit.report import build_report

TESTS = [
    "Bible Reader/Bible ReaderTests/Services/StudyOwnershipTests.swift",   # the target folder, and the suffix
    "MaccyTests/ClipboardTests.swift",
    "FooUITests/LoginUITests.swift",
    "Sources/Foo/OrderTests.swift",                                        # beside the code, suffix only
    "Sources/Foo/OrderTest.swift",
    "Bible ReaderTests/Support/SourceFile.swift",                         # a helper inside the target folder
    "Tests/FooTests/BarTests.swift",                                      # SwiftPM, already read as tests
]
LOOK_ALIKES = [
    "Sources/Contest.swift",            # ends in "test", lower case
    "Sources/Latest.swift",
    "Sources/Protest/Handler.swift",
    "Sources/Attests/Handler.swift",    # a folder ending in lower-case "tests"
    "Sources/Testsuite.swift",          # starts with Test, does not end with it
    "Sources/Tests.swift",              # no name before the suffix
    "ApiTests/handler.py",              # the folder rule is for Swift files only
    "src/ContestTests.js",              # and the suffix rule too
]


def test_a_swift_test_is_a_test_and_a_look_alike_is_not() -> None:
    """One test holds both halves, so the guard cannot pass on its own without the fix.

    The look-alikes were production before this change and must stay so; asserted
    beside the names that are now tests, the test fails when the rule is removed.
    """
    for path in TESTS:
        assert is_test_path(path), f"{path} is a Swift test"
        assert _is_test(path), f"{path} is a Swift test to discovery too"
    for path in LOOK_ALIKES:
        assert not is_test_path(path), f"{path} only looks like a test"
        assert not _is_test(path), f"{path} only looks like a test to discovery"


def test_an_xcode_project_with_a_test_target_counts_its_tests(tmp_path: Path) -> None:
    """The closing test the defect asked for, on that app's own shape, through the report the score reads."""
    (tmp_path / "App").mkdir()
    (tmp_path / "App" / "Store.swift").write_text("struct Store {\n    func load() {}\n}\n", encoding="utf-8")
    suite = tmp_path / "AppTests"
    suite.mkdir()
    (suite / "StoreTests.swift").write_text(
        "import Testing\n@testable import App\nstruct StoreTests {\n    func loads() {}\n}\n", encoding="utf-8")

    summary = build_report(tmp_path, load_config(None), run_analyzers=False)["summary"]

    assert summary["test_file_count"] == 1, "the Xcode test target was counted as production"
