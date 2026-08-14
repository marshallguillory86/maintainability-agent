"""Java is never routed to the last-resort patterns.

`FUNC_PATTERNS` matches `def`, `function` and arrows. Aimed at Java it
finds nothing and reports a confident zero, and a zero produced by
looking in the wrong language is indistinguishable in the report from a
file that genuinely has no methods. That is worse than leaving Java
unscored, because it looks measured.

The AST helpers live in `_ast_reading`: `test_java_wiring` asks the same
questions of the same source, and the second copy tripped this project's
own duplicate-block gate.
"""

from __future__ import annotations

import pytest
from _ast_reading import (
    branch_calls,
    declaration_suffixes,
    default_include_extensions,
    dispatch_branches_for,
    java_range_functions,
)


@pytest.mark.skipif(
    bool(java_range_functions()),
    reason="a dedicated Java declaration-range detector now exists",
)
def test_java_is_not_enabled_before_a_range_detector_exists() -> None:
    assert ".java" not in declaration_suffixes()
    assert ".java" not in default_include_extensions()


def test_java_is_never_routed_to_the_last_resort_patterns() -> None:
    detectors = java_range_functions()
    branches = dispatch_branches_for(".java")

    for branch in branches:
        calls, names = branch_calls(branch)
        assert "_regex_function_ranges" not in calls
        assert "FUNC_PATTERNS" not in names
        assert calls & detectors, (
            "a .java dispatch branch must call the dedicated Java range detector"
        )

    if ".java" in declaration_suffixes():
        assert branches, (
            ".java is declaration-enabled but declaration_ranges has no Java branch"
        )
