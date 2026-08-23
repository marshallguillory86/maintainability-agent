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
from collections import Counter
from pathlib import Path
from typing import Any

from ._metrics_types import KNOWN_SOURCE_SUFFIXES, FileMetric, FunctionMetric

# Moved down to the foundation layer so `_pressures` can make the same
# production/test split without a scoring module importing a scanner.
# Re-exported because `metrics.is_test_path` is the import path a dozen
# callers already use, and the move is not their business.
from ._metrics_types import is_test_path as is_test_path
from .declarations import DECLARATION_SUFFIXES, detect_functions
from .source import SourceIndex, index_or_new


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


def within(root: Path, path: Path) -> bool:
    """Whether a discovered path really lives under the granted root.

    `is_file()` follows symlinks, so a repository could point
    `linked.py` at a file outside the tree and have its contents read
    into the report — an audit did exactly that and got
    `TOP_SECRET_VALUE = 42` back in a findings payload (D36).
    `SECURITY.md` puts reads outside `--root` in scope, so this is a
    promise the code was breaking, not a new restriction.

    Symlinks *within* the root stay allowed: they resolve inside the
    grant, they are ordinary in real trees, and refusing them would
    drop first-party code the operator asked to be audited.
    """
    try:
        resolved = path.resolve()
    except OSError:
        return False
    return resolved == root or root in resolved.parents


def iter_files(root: Path, config: dict[str, Any], only_paths: set[str] | None = None) -> list[Path]:
    include_ext = set(config["paths"]["include_extensions"])
    excludes = config["paths"]["exclude_patterns"]
    resolved_root = root.resolve()
    out: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if not within(resolved_root, path):
            continue
        rel = str(path.relative_to(root)).replace(os.sep, "/")
        if is_excluded(rel, excludes):
            continue
        if only_paths is not None and rel not in only_paths:
            continue
        if path.suffix in include_ext:
            out.append(path)
    return sorted(out)


def unread_source(root: Path, config: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    """Source files present in the tree that the scan is not configured to read.

    Returns the per-suffix breakdown and the count of source files that
    *were* read, which together give the share of the repository the
    score actually describes.

    Exclusions are honoured, so vendored trees and build output do not
    count as unread code — the question is what of *this project's*
    source went unopened, not what was deliberately skipped.
    """
    include_ext = set(config["paths"]["include_extensions"])
    excludes = config["paths"]["exclude_patterns"]
    unread: Counter[str] = Counter()
    read = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in KNOWN_SOURCE_SUFFIXES:
            continue
        rel = str(path.relative_to(root)).replace(os.sep, "/")
        if is_excluded(rel, excludes):
            continue
        if path.suffix in include_ext:
            read += 1
        else:
            unread[path.suffix] += 1
    breakdown = [
        {"suffix": suffix, "language": KNOWN_SOURCE_SUFFIXES[suffix], "files": count}
        for suffix, count in sorted(unread.items(), key=lambda item: (-item[1], item[0]))
    ]
    return breakdown, read


def undetected_declarations(root: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Files the scan opened but cannot extract declarations from.

    A third state, between read and unread, and the one that produced a
    false sentence. `include_extensions` decides what is *opened* for
    length, duplication and risk; `DECLARATION_SUFFIXES` decides what is
    *parsed* for functions and classes. Adding `.java` to the first does
    not add it to the second.

    So a reader who follows the remedy the unread-source rule gives them
    lands here: forty files read, zero declarations, and the population
    floor announcing that the repository is smaller than anything the
    scale was calibrated on. It has forty files. It has no Java parser.
    Naming that is the difference between an honest withhold and a
    withheld score wearing the wrong explanation.
    """
    include_ext = set(config["paths"]["include_extensions"])
    excludes = config["paths"]["exclude_patterns"]
    # Only suffixes this project recognises as source. `.md` and `.css`
    # are in the include list on purpose and nobody expects declarations
    # from them; naming those would be noise, not honesty.
    blind = {
        suffix for suffix in include_ext
        if suffix in KNOWN_SOURCE_SUFFIXES and suffix not in DECLARATION_SUFFIXES
    }
    if not blind:
        return []

    counted: Counter[str] = Counter()
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in blind:
            continue
        rel = str(path.relative_to(root)).replace(os.sep, "/")
        if not is_excluded(rel, excludes):
            counted[path.suffix] += 1
    return [
        {"suffix": suffix, "language": KNOWN_SOURCE_SUFFIXES[suffix], "files": count}
        for suffix, count in sorted(counted.items(), key=lambda item: (-item[1], item[0]))
    ]


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
    excluded: set[str] | None = None,
) -> tuple[list[Path], list[FileMetric], list[FunctionMetric]]:
    """Measure every file the audit should score.

    `excluded` carries the relative paths the inventory classified as
    generated or vendored. They are dropped here rather than filtered
    later so they never reach a population, a rate or a finding: 10,759
    generated icon files moved a calibration constant, and code the team
    did not write must not move their score in either direction.
    """
    thresholds = config["thresholds"]
    source = index_or_new(index)
    files = iter_files(root, config, only_paths)
    if excluded:
        files = [
            path for path in files
            if str(path.relative_to(root)).replace(os.sep, "/") not in excluded
        ]
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
    # Any README, not specifically README.md. Django ships README.rst and
    # was reported as having none, which is the kind of finding that
    # teaches people the tool does not know what it is looking at.
    if hard.get("require_readme") and not any(root.glob("README*")):
        gates.append("A README is required but none was found.")
    if hard.get("require_test_command") and not expected_commands.get("test"):
        gates.append("A documented test command is required but missing from config.")
    if hard.get("require_clean_worktree") and git_status:
        gates.append("Worktree must be clean for this audit gate.")
    # Opt-in. Measured across the reference corpus these fired on every
    # single repository -- duplicate counts of 33 to 5,325 against a
    # default max of 20 -- so leaving them always-on made --fail-on-gate
    # useless out of the box and gave the gates score dimension zero
    # variance. Absent keys default to off.
    if hard.get("fail_on_duplicate_blocks") and duplicate_count > int(thresholds["max_duplicate_blocks"]):
        gates.append(f"Duplicate block count {duplicate_count} exceeds max {thresholds['max_duplicate_blocks']}.")
    if hard.get("fail_on_file_failures") and failed_files:
        gates.append(f"{len(failed_files)} files exceed max_file_lines.")
    if hard.get("fail_on_function_failures") and failed_functions:
        gates.append(f"{len(failed_functions)} functions exceed max function/complexity thresholds.")
    return gates
