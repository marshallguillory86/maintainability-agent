"""Walking the repo: which files count, how big they are, what gates trip.

The audit's per-file layer. Everything measured here is a property of a
path or of a whole file. The three modules split out of this one on
2026-08-06 sit above it: ``declarations`` measures inside a file,
``duplication`` compares files against each other, and ``report``
assembles all of it. They import ``metrics``; ``metrics`` imports none of
them, which is what keeps the graph acyclic.
"""
from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Any

from ._metrics_types import FileMetric, FunctionMetric
from .declarations import DECLARATION_SUFFIXES, detect_functions
from .source import SourceIndex, index_or_new


def is_test_path(rel: str) -> bool:
    """Identify test files by conventional path/name shape.

    Used by ``report.report_summary`` and ``score_report`` so test-code
    pressure can be reported separately and excluded from ``testability``
    / ``analyzability`` scoring: growing a test file should not lower the
    score of how testable the production code is.
    """
    normalized = rel.replace("\\", "/").lower()
    parts = normalized.split("/")
    if any(segment in {"tests", "test", "__tests__", "spec", "specs"} for segment in parts[:-1]):
        return True
    name = parts[-1]
    if name.startswith(("test_", "test.")):
        return True
    stem = name.rsplit(".", 1)[0]
    return stem.endswith(("_test", ".test", ".spec", "_spec"))


def is_excluded(rel: str, patterns: list[str]) -> bool:
    normalized = rel.replace("\\", "/").replace(os.sep, "/")
    for raw_pattern in patterns:
        pattern = raw_pattern.replace("\\", "/")
        if pattern.endswith("/") and (normalized == pattern[:-1] or normalized.startswith(pattern)):
            return True
        if fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(Path(normalized).name, pattern):
            return True
        if not any(char in pattern for char in "*?[]") and f"/{pattern.rstrip('/')}/" in f"/{normalized}/":
            return True
    return False


def iter_files(root: Path, config: dict[str, Any], only_paths: set[str] | None = None) -> list[Path]:
    include_ext = set(config["paths"]["include_extensions"])
    excludes = config["paths"]["exclude_patterns"]
    out: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root)).replace(os.sep, "/")
        if is_excluded(rel, excludes):
            continue
        if only_paths is not None and rel not in only_paths:
            continue
        if path.suffix in include_ext:
            out.append(path)
    return sorted(out)


def read_lines(path: Path) -> list[str]:
    """Read one file, tolerating undecodable bytes.

    Kept as the standalone entry point. Within an audit the same read is
    served from ``SourceIndex`` instead, so a file is not read once per
    scanner — see ``source``.
    """
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()


def file_status(lines: int, thresholds: dict[str, int]) -> str:
    if lines > thresholds["max_file_lines"]:
        return "fail"
    if lines > thresholds["warn_file_lines"]:
        return "warn"
    return "ok"


def collect_metrics(
    root: Path,
    config: dict[str, Any],
    only_paths: set[str] | None,
    index: SourceIndex | None = None,
) -> tuple[list[Path], list[FileMetric], list[FunctionMetric]]:
    thresholds = config["thresholds"]
    source = index_or_new(index)
    files = iter_files(root, config, only_paths)
    file_metrics: list[FileMetric] = []
    function_metrics: list[FunctionMetric] = []
    for path in files:
        lines = source.lines(path)
        rel = str(path.relative_to(root)).replace(os.sep, "/")
        file_metrics.append(FileMetric(path=rel, lines=len(lines), status=file_status(len(lines), thresholds)))
        if path.suffix in DECLARATION_SUFFIXES:
            function_metrics.extend(detect_functions(root, path, lines, thresholds, source.declarations(path)))
    return files, file_metrics, function_metrics


def hard_gate_failures(
    root: Path,
    config: dict[str, Any],
    git_status: str,
    failed_files: list[FileMetric],
    failed_functions: list[FunctionMetric],
    duplicate_count: int,
) -> list[str]:
    thresholds = config["thresholds"]
    expected_commands = config.get("expected_commands", {})
    hard = config.get("hard_gates", {})
    gates: list[str] = []
    if hard.get("require_readme") and not (root / "README.md").exists():
        gates.append("README.md is required but missing.")
    if hard.get("require_test_command") and not expected_commands.get("test"):
        gates.append("A documented test command is required but missing from config.")
    if hard.get("require_clean_worktree") and git_status:
        gates.append("Worktree must be clean for this audit gate.")
    if duplicate_count > int(thresholds["max_duplicate_blocks"]):
        gates.append(f"Duplicate block count {duplicate_count} exceeds max {thresholds['max_duplicate_blocks']}.")
    if failed_files:
        gates.append(f"{len(failed_files)} files exceed max_file_lines.")
    if failed_functions:
        gates.append(f"{len(failed_functions)} functions exceed max function/complexity thresholds.")
    return gates
