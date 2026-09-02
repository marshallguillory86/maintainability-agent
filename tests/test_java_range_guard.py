"""No claimed language is ever routed to the last-resort patterns.

`FUNC_PATTERNS` matches `def`, `function` and arrows. Aimed at Java it
finds nothing and reports a confident zero, and a zero produced by
looking in the wrong language is indistinguishable in the report from a
file that genuinely has no methods. That is worse than leaving a
language unscored, because it looks measured.

Written for Java, generalised in 1.1.0 when C arrived and the dispatch
became a table. The guard now reads that table and holds every claimed
language to the rule, so a language added without a scanner of its own
fails here rather than shipping a population nobody read.

The AST helpers live in `_ast_reading`: `test_java_wiring` asks the same
questions of the same source, and the second copy tripped this project's
own duplicate-block gate.
"""

from __future__ import annotations

import pytest
from _ast_reading import (
    declaration_suffixes,
    default_include_extensions,
    range_functions_for,
    scanner_registry,
)

# `.py` is parsed by `ast` and is the one language the last-resort
# patterns were written for, so it is deliberately not in the table.
PYTHON = {".py"}


@pytest.mark.skipif(
    bool(range_functions_for("java")),
    reason="a dedicated Java declaration-range detector now exists",
)
def test_java_is_not_enabled_before_a_range_detector_exists() -> None:
    assert ".java" not in declaration_suffixes()
    assert ".java" not in default_include_extensions()


def test_every_claimed_language_has_its_own_scanner() -> None:
    """The rule the table exists to make checkable, for all of them."""
    registry = scanner_registry()
    unrouted = sorted(declaration_suffixes() - PYTHON - set(registry))
    assert not unrouted, (
        f"{unrouted} are claimed as parsed but reach no scanner in "
        "declarations.SCANNERS, so they fall through to FUNC_PATTERNS — "
        "which matches `def`, `function` and arrows and would report a "
        "confident zero"
    )
    for suffix, scanner in sorted(registry.items()):
        assert scanner != "_regex_function_ranges", (
            f"{suffix} is routed to the last-resort patterns"
        )


def test_java_is_never_routed_to_the_last_resort_patterns() -> None:
    registry = scanner_registry()
    detectors = range_functions_for("java")

    if ".java" in declaration_suffixes():
        assert registry.get(".java") in detectors, (
            ".java is declaration-enabled but declarations.SCANNERS does "
            "not route it to the dedicated Java range detector"
        )


def test_c_is_never_routed_to_the_last_resort_patterns() -> None:
    """The same guard for 1.1.0's language, from the same table."""
    registry = scanner_registry()
    detectors = range_functions_for("c_declaration")

    for suffix in (".c", ".h"):
        if suffix in declaration_suffixes():
            assert registry.get(suffix) in detectors, (
                f"{suffix} is declaration-enabled but is not routed to the "
                "dedicated C range detector"
            )


def test_cpp_is_never_routed_to_the_last_resort_patterns() -> None:
    """And for 1.2.0's. Each language states its own routing so a wrong
    row — `.cpp` pointed at the C scanner — fails by name rather than
    passing the generic check that only asks for *some* scanner."""
    registry = scanner_registry()
    detectors = range_functions_for("cpp_declaration")

    for suffix in (".cpp", ".hpp", ".cc", ".cxx", ".hh"):
        if suffix in declaration_suffixes():
            assert registry.get(suffix) in detectors, (
                f"{suffix} is declaration-enabled but is not routed to the "
                "dedicated C++ range detector"
            )


def test_fortran_is_never_routed_to_the_last_resort_patterns() -> None:
    """1.4.0's language, and the one with no analyzer fallback at all:
    lizard does not read Fortran, so a wrong row here leaves a Fortran
    repository with no declaration population from any source."""
    registry = scanner_registry()
    detectors = range_functions_for("fortran_declaration")

    for suffix in (".f90", ".F90", ".f95", ".f03", ".f08", ".pf"):
        if suffix in declaration_suffixes():
            assert registry.get(suffix) in detectors, (
                f"{suffix} is declaration-enabled but is not routed to the "
                "dedicated Fortran range detector"
            )


def test_csharp_is_never_routed_to_the_last_resort_patterns() -> None:
    """And for 1.3.0's, completing the C family."""
    registry = scanner_registry()
    detectors = range_functions_for("csharp_declaration")

    if ".cs" in declaration_suffixes():
        assert registry.get(".cs") in detectors, (
            ".cs is declaration-enabled but is not routed to the dedicated "
            "C# range detector"
        )
