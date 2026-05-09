from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .git_tools import run_git
from .scoring import score_report

FUNC_PATTERNS = [
    re.compile(r"^\s*def\s+([A-Za-z_][\w]*)\s*\("),
    re.compile(r"^\s*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\("),
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>"),
    re.compile(r"^\s*(?:export\s+default\s+)?class\s+([A-Za-z_$][\w$]*)\b"),
]

COMPLEXITY_RE = re.compile(r"\b(if|elif|for|while|except|case|catch)\b|&&|\|\||\?")


@dataclass
class FileMetric:
    path: str
    lines: int
    status: str


@dataclass
class FunctionMetric:
    path: str
    name: str
    start_line: int
    lines: int
    complexity: int
    status: str


@dataclass
class RiskFinding:
    path: str
    line: int
    name: str
    text: str


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


def detect_functions(root: Path, path: Path, lines: list[str], thresholds: dict[str, int]) -> list[FunctionMetric]:
    starts: list[tuple[int, str]] = []
    for idx, line in enumerate(lines, start=1):
        for pattern in FUNC_PATTERNS:
            match = pattern.search(line)
            if match:
                starts.append((idx, match.group(1)))
                break

    funcs: list[FunctionMetric] = []
    for index, (start, name) in enumerate(starts):
        end = starts[index + 1][0] - 1 if index + 1 < len(starts) else len(lines)
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


def duplicate_blocks(root: Path, files: list[Path], block_size: int) -> list[dict[str, Any]]:
    seen: dict[tuple[str, ...], list[str]] = {}
    for path in files:
        lines = [normalize_for_dup(line) for line in read_lines(path)]
        useful = [line for line in lines if line and not line.startswith(("//", "#", "/*", "*", '"', "'"))]
        for idx in range(0, max(0, len(useful) - block_size + 1)):
            block = tuple(useful[idx : idx + block_size])
            if len(set(block)) <= 1:
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


def report_summary(
    files: list[Path],
    file_metrics: list[FileMetric],
    function_metrics: list[FunctionMetric],
    duplicate_count: int,
    risk_count: int,
    gate_count: int,
) -> dict[str, int]:
    return {
        "files_scanned": len(files),
        "file_warnings": len([metric for metric in file_metrics if metric.status == "warn"]),
        "file_failures": len([metric for metric in file_metrics if metric.status == "fail"]),
        "function_warnings": len([metric for metric in function_metrics if metric.status == "warn"]),
        "function_failures": len([metric for metric in function_metrics if metric.status == "fail"]),
        "duplicate_blocks": duplicate_count,
        "risk_findings": risk_count,
        "hard_gate_failures": gate_count,
    }


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
    failed_files = [metric for metric in file_metrics if metric.status == "fail"]
    failed_functions = [metric for metric in function_metrics if metric.status == "fail"]
    gates = hard_gate_failures(root, config, git_status, failed_files, failed_functions, len(dupes))
    missing_files = [path for path in config.get("expected_files", []) if not (root / path).exists()]
    summary = report_summary(files, file_metrics, function_metrics, len(dupes), len(risks), len(gates))

    report = {
        "root": str(root),
        "git_branch": run_git(["branch", "--show-current"], root),
        "git_status_short": git_status,
        "mode": "changed-only" if only_paths is not None else "full",
        "changed_revspec": changed_revspec,
        "summary": summary,
        "hard_gate_failures": gates,
        "missing_files": missing_files,
        "largest_files": [asdict(metric) for metric in sorted(file_metrics, key=lambda metric: metric.lines, reverse=True)[:25]],
        "function_hotspots": [
            asdict(metric)
            for metric in sorted(function_metrics, key=lambda metric: (metric.status != "fail", -metric.complexity, -metric.lines))[:50]
            if metric.status in {"warn", "fail"}
        ],
        "duplicate_blocks": dupes[:25],
        "risk_findings": [asdict(finding) for finding in risks[:100]],
        "external_findings": external_findings or [],
    }
    report["score"] = score_report(report)
    return report
