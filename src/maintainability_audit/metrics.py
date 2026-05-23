from __future__ import annotations

import ast
import fnmatch
import os
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ._metrics_types import (
    COMPLEXITY_RE,
    FUNC_PATTERNS,
    FileMetric,
    FunctionMetric,
    RiskFinding,
)
from .git_tools import run_git
from .scoring import score_report


def is_test_path(rel: str) -> bool:
    """Identify test files by conventional path/name shape.

    Used by ``report_summary`` and ``score_report`` so test-code pressure
    can be reported separately and excluded from ``testability`` /
    ``analyzability`` scoring: growing a test file should not lower the
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


def function_status(lines: int, complexity: int, thresholds: dict[str, int]) -> str:
    if lines > thresholds["max_function_lines"] or complexity > thresholds["max_complexity"]:
        return "fail"
    if lines > thresholds["warn_function_lines"] or complexity > thresholds["warn_complexity"]:
        return "warn"
    return "ok"


def _python_function_ranges(source: str) -> list[tuple[int, int, str]] | None:
    """Parse Python source and return (start_line, end_line, name) tuples for
    every top-level or nested function/class definition.

    Uses ``ast.end_lineno`` (Python 3.8+) so the body length reflects the
    actual indented block, not the distance to the next sibling definition.
    Returns ``None`` if the source cannot be parsed so the caller can fall
    back to the regex-based detector.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    ranges: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            end = getattr(node, "end_lineno", None) or node.lineno
            ranges.append((node.lineno, end, node.name))
    ranges.sort(key=lambda item: (item[0], item[1]))
    return ranges


def _regex_function_ranges(lines: list[str]) -> list[tuple[int, int, str]]:
    """Fallback detector for non-Python languages (and unparseable Python).

    Preserves the historical "next match minus one" heuristic for languages
    where we don't yet have an AST. It over-estimates body length but stays
    consistent with prior behavior for JS/TS/HTML.
    """
    starts: list[tuple[int, str]] = []
    for idx, line in enumerate(lines, start=1):
        for pattern in FUNC_PATTERNS:
            match = pattern.search(line)
            if match:
                starts.append((idx, match.group(1)))
                break
    ranges: list[tuple[int, int, str]] = []
    for index, (start, name) in enumerate(starts):
        end = starts[index + 1][0] - 1 if index + 1 < len(starts) else len(lines)
        ranges.append((start, max(end, start), name))
    return ranges


def detect_functions(root: Path, path: Path, lines: list[str], thresholds: dict[str, int]) -> list[FunctionMetric]:
    ranges: list[tuple[int, int, str]] | None = None
    if path.suffix == ".py":
        ranges = _python_function_ranges("\n".join(lines))
    if ranges is None:
        ranges = _regex_function_ranges(lines)

    funcs: list[FunctionMetric] = []
    for start, end, name in ranges:
        block = lines[start - 1 : end]
        complexity = 1 + sum(len(COMPLEXITY_RE.findall(line)) for line in block)
        count = max(1, len(block))
        funcs.append(
            FunctionMetric(
                path=str(path.relative_to(root)).replace(os.sep, "/"),
                name=name,
                start_line=start,
                lines=count,
                complexity=complexity,
                status=function_status(count, complexity, thresholds),
            )
        )
    return funcs


def normalize_for_dup(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


_TRIVIAL_IDENT_RE = re.compile(r"^[A-Za-z_][\w]*,?$")
_TRIVIAL_KWARG_RE = re.compile(r"^[A-Za-z_][\w]*\s*=\s*[A-Za-z_][\w.]*,?$")
_TRIVIAL_PUNCT_RE = re.compile(r"^[\s()\[\]{},;:]+$")


def _is_trivial_dup_line(line: str) -> bool:
    """Return True for low-information lines that should not anchor a
    duplicate-block match.

    Bare-identifier lines such as ``name,`` show up identically in
    SQL column lists and in function keyword-argument signatures. The
    shared ordering is often the architectural contract — flagging it
    as a duplicate creates noise and pressures developers to obscure
    the contract. Pure punctuation (closing brackets/parens) is
    similarly information-free.
    """
    if not line:
        return True
    if _TRIVIAL_PUNCT_RE.match(line):
        return True
    if _TRIVIAL_IDENT_RE.match(line):
        return True
    return bool(_TRIVIAL_KWARG_RE.match(line))


def duplicate_blocks(root: Path, files: list[Path], block_size: int) -> list[dict[str, Any]]:
    seen: dict[tuple[str, ...], list[str]] = {}
    for path in files:
        lines = [normalize_for_dup(line) for line in read_lines(path)]
        useful = [line for line in lines if line and not line.startswith(("//", "#", "/*", "*", '"', "'"))]
        for idx in range(0, max(0, len(useful) - block_size + 1)):
            block = tuple(useful[idx : idx + block_size])
            if len(set(block)) <= 1:
                continue
            # Skip blocks made entirely of low-information lines (bare
            # identifiers, kwarg passthroughs, pure punctuation). See
            # ``_is_trivial_dup_line`` docstring for the rationale.
            if all(_is_trivial_dup_line(item) for item in block):
                continue
            seen.setdefault(block, []).append(f"{path.relative_to(root)}:{idx + 1}")

    dupes = []
    for block, locations in seen.items():
        unique_locations = sorted(set(locations))
        if len(unique_locations) > 1:
            dupes.append({"locations": unique_locations[:10], "count": len(unique_locations), "sample": list(block)})
    return sorted(dupes, key=lambda item: item["count"], reverse=True)


def risk_findings(root: Path, files: list[Path], config: dict[str, Any]) -> list[RiskFinding]:
    findings: list[RiskFinding] = []
    for rule in config.get("risk_patterns", []):
        pattern = re.compile(rule["pattern"], re.IGNORECASE)
        allowed = set(rule.get("extensions", []))
        for path in files:
            if allowed and path.suffix not in allowed:
                continue
            for idx, line in enumerate(read_lines(path), start=1):
                if pattern.search(line):
                    findings.append(
                        RiskFinding(
                            path=str(path.relative_to(root)).replace(os.sep, "/"),
                            line=idx,
                            name=rule["name"],
                            text=line.strip()[:180],
                        )
                    )
    return findings


def collect_metrics(
    root: Path,
    config: dict[str, Any],
    only_paths: set[str] | None,
) -> tuple[list[Path], list[FileMetric], list[FunctionMetric]]:
    thresholds = config["thresholds"]
    files = iter_files(root, config, only_paths)
    file_metrics: list[FileMetric] = []
    function_metrics: list[FunctionMetric] = []
    for path in files:
        lines = read_lines(path)
        rel = str(path.relative_to(root)).replace(os.sep, "/")
        file_metrics.append(FileMetric(path=rel, lines=len(lines), status=file_status(len(lines), thresholds)))
        if path.suffix in {".py", ".js", ".jsx", ".ts", ".tsx", ".html"}:
            function_metrics.extend(detect_functions(root, path, lines, thresholds))
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


def _count_status(metrics: list, status: str) -> int:
    return sum(1 for metric in metrics if metric.status == status)


def _split_by_test_path(metrics: list) -> tuple[list, list]:
    prod = [metric for metric in metrics if not is_test_path(metric.path)]
    test = [metric for metric in metrics if is_test_path(metric.path)]
    return prod, test


def report_summary(
    files: list[Path],
    file_metrics: list[FileMetric],
    function_metrics: list[FunctionMetric],
    duplicate_count: int,
    risk_count: int,
    gate_count: int,
) -> dict[str, int]:
    prod_files, test_files = _split_by_test_path(file_metrics)
    prod_funcs, test_funcs = _split_by_test_path(function_metrics)
    return {
        "files_scanned": len(files),
        "file_warnings": _count_status(file_metrics, "warn"),
        "file_failures": _count_status(file_metrics, "fail"),
        "function_warnings": _count_status(function_metrics, "warn"),
        "function_failures": _count_status(function_metrics, "fail"),
        "production_file_warnings": _count_status(prod_files, "warn"),
        "production_file_failures": _count_status(prod_files, "fail"),
        "production_function_warnings": _count_status(prod_funcs, "warn"),
        "production_function_failures": _count_status(prod_funcs, "fail"),
        "test_file_count": len(test_files),
        "test_function_warnings": _count_status(test_funcs, "warn"),
        "test_function_failures": _count_status(test_funcs, "fail"),
        "duplicate_blocks": duplicate_count,
        "risk_findings": risk_count,
        "hard_gate_failures": gate_count,
    }


def _compute_gates_and_summary(
    root: Path,
    config: dict[str, Any],
    git_status: str,
    files: list[Path],
    file_metrics: list[FileMetric],
    function_metrics: list[FunctionMetric],
    duplicate_count: int,
    risk_count: int,
) -> tuple[list[str], dict[str, int]]:
    # The gate list shown to users still includes every failure
    # (prod + test). But scoring uses a production-only gate count so
    # a long test function never drags testability/analyzability down.
    failed_files = [metric for metric in file_metrics if metric.status == "fail"]
    failed_functions = [metric for metric in function_metrics if metric.status == "fail"]
    prod_failed_files = [metric for metric in failed_files if not is_test_path(metric.path)]
    prod_failed_functions = [metric for metric in failed_functions if not is_test_path(metric.path)]
    gates = hard_gate_failures(root, config, git_status, failed_files, failed_functions, duplicate_count)
    production_gates = hard_gate_failures(
        root, config, git_status, prod_failed_files, prod_failed_functions, duplicate_count
    )
    summary = report_summary(files, file_metrics, function_metrics, duplicate_count, risk_count, len(gates))
    summary["production_hard_gate_failures"] = len(production_gates)
    return gates, summary


def _function_hotspots(function_metrics: list[FunctionMetric]) -> list[dict[str, Any]]:
    flagged = [metric for metric in function_metrics if metric.status in {"warn", "fail"}]
    flagged.sort(key=lambda metric: (metric.status != "fail", -metric.complexity, -metric.lines))
    return [asdict(metric) for metric in flagged[:50]]


def build_report(
    root: Path,
    config: dict[str, Any],
    only_paths: set[str] | None = None,
    changed_revspec: str | None = None,
    external_findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    files, file_metrics, function_metrics = collect_metrics(root, config, only_paths)
    thresholds = config["thresholds"]
    dupes = duplicate_blocks(root, files, int(thresholds["duplicate_block_lines"]))
    risks = risk_findings(root, files, config)
    git_status = run_git(["status", "--short"], root)
    gates, summary = _compute_gates_and_summary(
        root, config, git_status, files, file_metrics, function_metrics, len(dupes), len(risks)
    )
    missing_files = [path for path in config.get("expected_files", []) if not (root / path).exists()]
    largest_files = sorted(file_metrics, key=lambda metric: metric.lines, reverse=True)[:25]

    report = {
        "root": str(root),
        "git_branch": run_git(["branch", "--show-current"], root),
        "git_status_short": git_status,
        "mode": "changed-only" if only_paths is not None else "full",
        "changed_revspec": changed_revspec,
        "summary": summary,
        "hard_gate_failures": gates,
        "missing_files": missing_files,
        "largest_files": [asdict(metric) for metric in largest_files],
        "function_hotspots": _function_hotspots(function_metrics),
        "duplicate_blocks": dupes[:25],
        "risk_findings": [asdict(finding) for finding in risks[:100]],
        "external_findings": external_findings or [],
    }
    report["score"] = score_report(report)
    return report
