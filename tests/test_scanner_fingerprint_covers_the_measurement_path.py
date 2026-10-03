"""The scanner fingerprint covers every module a measurement passes through.

`measure.py --reuse` keeps a stored corpus row while its
`scanner_fingerprint` matches — a digest of `MEASUREMENT_PATH`, a list
typed by hand. The list named seven of the fifteen language scanners: a
change to the Kotlin, Shell, Swift, Go, Rust, PHP, Ruby or COBOL scanner
left the fingerprint unchanged, so a reused row measured by the old scanner
passed for a current one, and the constants were fitted to a corpus no
single instrument produced.

The rule is now derived rather than remembered: every package module
reachable by import from a fingerprinted module is itself fingerprinted.
Scoring and rendering stay out because nothing on the measurement path
imports them.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "maintainability_audit"
sys.path.insert(0, str(ROOT / "tools" / "calibration"))

import measure  # noqa: E402


def _imports(module: str) -> set[str]:
    path = PACKAGE / f"{module}.py"
    if not path.exists():
        return set()
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.level == 1:
            if node.module:
                found.add(node.module.split(".")[0])
            else:
                found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("maintainability_audit."):
            found.add(node.module.split(".")[1])
    return {name for name in found if (PACKAGE / f"{name}.py").exists()}


def _closure(roots: set[str]) -> set[str]:
    seen: set[str] = set()
    pending = list(roots)
    while pending:
        module = pending.pop()
        if module in seen:
            continue
        seen.add(module)
        pending.extend(_imports(module) - seen)
    return seen


def test_every_module_a_measurement_reaches_is_fingerprinted() -> None:
    listed = set(measure.MEASUREMENT_PATH)
    excused = set(measure.NOT_FINGERPRINTED)

    assert _closure(listed) - listed - excused == set()


def test_an_exclusion_is_stated_and_is_not_also_listed() -> None:
    """Leaving a module out is a claim that it cannot move a stored row."""
    assert all(reason.strip() for reason in measure.NOT_FINGERPRINTED.values())
    assert set(measure.NOT_FINGERPRINTED) & set(measure.MEASUREMENT_PATH) == set()


def test_every_language_scanner_is_fingerprinted() -> None:
    """The instance that exposed the class, pinned on its own."""
    scanners = {path.stem for path in PACKAGE.glob("_ranges_*.py")}

    assert scanners - set(measure.MEASUREMENT_PATH) == set()
