"""TDD-shaped structure: path pairing and constructs.

Not chronology and not quality. A production file is paired when a
test-shaped file shares its subject stem. Constructs are counts of
known test APIs in those files. Effectiveness stays unscored unless
the operator opted into suite execution.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ._metrics_types import FileMetric, FunctionMetric, is_test_path
from .source import SourceIndex, index_or_new

# HTML/CSS/Markdown are not "a page with no test" in the TS/Python sense.
PAIRABLE = frozenset({".py", ".java", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"})

_STEM_SUFFIXES = (".test", ".spec", "_test")
_CONSTRUCTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("pytest", re.compile(r"\bpytest\b|def test_")),
    ("unittest", re.compile(r"\bunittest\b")),
    ("describe_it", re.compile(r"\b(?:describe|it|test)\s*\(")),
    ("parametrize", re.compile(r"pytest\.mark\.parametrize")),
    ("given_when_then", re.compile(r"(?:#|//)\s*(?:given|when|then)\b", re.I)),
)


def subject_stem(rel: str) -> str:
    """The production name a test file claims to cover, or the file's own stem."""
    stem = Path(rel.replace("\\", "/")).name.rsplit(".", 1)[0].lower()
    for suffix in _STEM_SUFFIXES:
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    if stem.startswith("test_"):
        return stem[5:]
    if stem.startswith("test."):
        return stem[5:]
    return stem


def _suffix(rel: str) -> str:
    return Path(rel.replace("\\", "/")).suffix.lower()


def _partition_files(
    file_metrics: list[FileMetric],
) -> tuple[set[str], list[str], list[FileMetric]]:
    """Test subject stems and paths, and the pairable production files."""
    test_stems: set[str] = set()
    test_paths: list[str] = []
    production: list[FileMetric] = []
    for metric in file_metrics:
        if is_test_path(metric.path):
            test_stems.add(subject_stem(metric.path))
            test_paths.append(metric.path)
        elif _suffix(metric.path) in PAIRABLE:
            production.append(metric)
    return test_stems, test_paths, production


def _count_constructs(root: Path, test_paths: list[str], index: SourceIndex) -> dict[str, int]:
    """How many test files use each known test API. Counts, never quality."""
    constructs = {name: 0 for name, _pattern in _CONSTRUCTS}
    for rel in test_paths:
        text = "\n".join(index.lines(root / rel))
        for name, pattern in _CONSTRUCTS:
            if pattern.search(text):
                constructs[name] += 1
    return constructs


def _unpaired_fail_band(
    function_metrics: list[FunctionMetric],
    production: list[FileMetric],
    unpaired_paths: set[str],
) -> list[dict[str, Any]]:
    """Fail-band units in unpaired production: the failing declarations
    first, then any warn/fail whole file not already named by one of them."""
    fail_band: list[dict[str, Any]] = []
    seen: set[str] = set()
    for fn in function_metrics:
        if fn.status != "fail" or is_test_path(fn.path) or fn.path not in unpaired_paths:
            continue
        fail_band.append({
            "kind": "declaration", "path": fn.path, "name": fn.name,
            "line": fn.start_line, "lines": fn.lines,
        })
        seen.add(fn.path)
    for metric in production:
        if metric.status not in {"warn", "fail"} or metric.path in seen:
            continue
        if metric.path not in unpaired_paths:
            continue
        fail_band.append({
            "kind": "file", "path": metric.path, "name": Path(metric.path).name,
            "line": None, "lines": metric.lines,
        })
    return fail_band


def describe_tdd(
    root: Path,
    file_metrics: list[FileMetric],
    function_metrics: list[FunctionMetric],
    source: SourceIndex | None = None,
) -> dict[str, Any]:
    """Pairing, constructs, and fail-band production units with no pair."""
    index = index_or_new(source)
    test_stems, test_paths, production = _partition_files(file_metrics)
    constructs = _count_constructs(root, test_paths, index)
    paired = [m for m in production if subject_stem(m.path) in test_stems]
    unpaired_paths = {m.path for m in production if subject_stem(m.path) not in test_stems}
    return {
        "production_files": len(production),
        "paired_production_files": len(paired),
        "detected": len(paired) > 0 or any(constructs.values()),
        "constructs": constructs,
        "unpaired_fail_band": _unpaired_fail_band(function_metrics, production, unpaired_paths),
    }
