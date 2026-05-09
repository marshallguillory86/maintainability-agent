from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "paths": {
        "include_extensions": [".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".md"],
        "exclude_patterns": [
            ".git/",
            "node_modules/",
            ".venv/",
            "venv/",
            "dist/",
            "build/",
            "coverage/",
            "__pycache__/",
        ],
    },
    "thresholds": {
        "max_file_lines": 800,
        "warn_file_lines": 400,
        "max_function_lines": 80,
        "warn_function_lines": 50,
        "max_complexity": 15,
        "warn_complexity": 10,
        "max_duplicate_blocks": 20,
        "duplicate_block_lines": 6,
    },
    "hard_gates": {
        "require_test_command": False,
        "require_readme": True,
        "require_clean_worktree": False,
    },
    "expected_files": ["README.md"],
    "expected_commands": {"test": [], "lint": []},
    "risk_patterns": [],
    "instruction_pack": {
        "project_name": "this repository",
        "strictness": "high",
        "test_policy": "tests for meaningful behavior changes",
        "architecture_notes": [],
    },
}


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


def deep_update(base: dict[str, Any], override: dict[str, Any]) -> None:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value


def load_config(path: str | None) -> dict[str, Any]:
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    if not path:
        return config
    with open(path, "r", encoding="utf-8") as f:
        user_config = json.load(f)
    deep_update(config, user_config)
    return config


def run_git(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def is_excluded(rel: str, patterns: list[str]) -> bool:
    normalized = rel.replace(os.sep, "/")
    for pattern in patterns:
        if pattern.endswith("/") and normalized.startswith(pattern):
            return True
        if fnmatch.fnmatch(normalized, pattern):
            return True
        if f"/{pattern.rstrip('/')}/" in f"/{normalized}/":
            return True
    return False


def iter_files(root: Path, config: dict[str, Any], only_paths: set[str] | None = None) -> list[Path]:
    include_ext = set(config["paths"]["include_extensions"])
    excludes = config["paths"]["exclude_patterns"]
    out: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root))
        if is_excluded(rel, excludes):
            continue
        if only_paths is not None and rel.replace(os.sep, "/") not in only_paths:
            continue
        if path.suffix in include_ext:
            out.append(path)
    return sorted(out)


def changed_paths(root: Path, revspec: str) -> set[str]:
    output = run_git(["diff", "--name-only", revspec], root)
    if not output:
        return set()
    return {line.strip().replace(os.sep, "/") for line in output.splitlines() if line.strip()}


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
    for i, (start, name) in enumerate(starts):
        end = len(lines)
        if i + 1 < len(starts):
            end = starts[i + 1][0] - 1
        block = lines[start - 1 : end]
        complexity = 1 + sum(len(COMPLEXITY_RE.findall(line)) for line in block)
        count = max(1, len(block))
        funcs.append(
            FunctionMetric(
                path=str(path.relative_to(root)),
                name=name,
                start_line=start,
                lines=count,
                complexity=complexity,
                status=function_status(count, complexity, thresholds),
            )
        )
    return funcs


def normalize_for_dup(line: str) -> str:
    line = line.strip()
    line = re.sub(r"\s+", " ", line)
    return line


def duplicate_blocks(root: Path, files: list[Path], block_size: int) -> list[dict[str, Any]]:
    seen: dict[tuple[str, ...], list[str]] = {}
    for path in files:
        lines = [normalize_for_dup(line) for line in read_lines(path)]
        useful = [line for line in lines if line and not line.startswith(("//", "#", "/*", "*"))]
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
                            path=str(path.relative_to(root)),
                            line=idx,
                            name=rule["name"],
                            text=line.strip()[:180],
                        )
                    )
    return findings


def finding_fingerprints(report: dict[str, Any]) -> set[str]:
    fingerprints: set[str] = set()
    for item in report.get("largest_files", []):
        if item["status"] == "fail":
            fingerprints.add(f"file-lines:{item['path']}")
    for item in report.get("function_hotspots", []):
        if item["status"] == "fail":
            fingerprints.add(f"function:{item['path']}:{item['name']}:{item['start_line']}")
    for item in report.get("risk_findings", []):
        fingerprints.add(f"risk:{item['path']}:{item['line']}:{item['name']}")
    for item in report.get("duplicate_blocks", []):
        locations = ",".join(item["locations"][:5])
        fingerprints.add(f"duplicate:{locations}")
    return fingerprints


def load_baseline(path: str | None) -> set[str]:
    if not path:
        return set()
    baseline_path = Path(path)
    if not baseline_path.exists():
        return set()
    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    return set(data.get("findings", []))


def write_baseline(path: str, report: dict[str, Any]) -> None:
    data = {
        "version": 1,
        "root": report["root"],
        "findings": sorted(finding_fingerprints(report)),
    }
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sarif_level(status: str) -> str:
    if status == "fail":
        return "error"
    if status == "warn":
        return "warning"
    return "note"


def sarif_result(rule_id: str, message: str, path: str, line: int = 1, level: str = "warning") -> dict[str, Any]:
    return {
        "ruleId": rule_id,
        "level": level,
        "message": {"text": message},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": path},
                    "region": {"startLine": max(1, line)},
                }
            }
        ],
    }


def report_to_sarif(report: dict[str, Any]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for item in report.get("largest_files", []):
        if item["status"] in {"warn", "fail"}:
            results.append(
                sarif_result(
                    "maintainability.file_size",
                    f"{item['path']} has {item['lines']} lines ({item['status']}).",
                    item["path"],
                    level=sarif_level(item["status"]),
                )
            )
    for item in report.get("function_hotspots", []):
        results.append(
            sarif_result(
                "maintainability.function_hotspot",
                f"{item['name']} has {item['lines']} lines and complexity {item['complexity']} ({item['status']}).",
                item["path"],
                item["start_line"],
                sarif_level(item["status"]),
            )
        )
    for item in report.get("risk_findings", []):
        results.append(sarif_result(f"maintainability.risk.{item['name']}", item["text"], item["path"], item["line"]))
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "maintainability-agent",
                        "informationUri": "https://github.com/",
                        "rules": [],
                    }
                },
                "results": results,
            }
        ],
    }


def read_sarif_inputs(paths: list[str] | None) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in paths or []:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for run in data.get("runs", []):
            tool = run.get("tool", {}).get("driver", {}).get("name", "sarif")
            for result in run.get("results", []):
                location = (result.get("locations") or [{}])[0]
                physical = location.get("physicalLocation", {})
                artifact = physical.get("artifactLocation", {})
                region = physical.get("region", {})
                findings.append(
                    {
                        "tool": tool,
                        "rule_id": result.get("ruleId", "unknown"),
                        "level": result.get("level", "warning"),
                        "message": result.get("message", {}).get("text", ""),
                        "path": artifact.get("uri", ""),
                        "line": region.get("startLine", 1),
                    }
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
        rel = str(path.relative_to(root))
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

    return {
        "root": str(root),
        "git_branch": run_git(["branch", "--show-current"], root),
        "git_status_short": git_status,
        "mode": "changed-only" if only_paths is not None else "full",
        "changed_revspec": changed_revspec,
        "summary": report_summary(files, file_metrics, function_metrics, len(dupes), len(risks), len(gates)),
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


def summary_table(summary: dict[str, int]) -> list[str]:
    return [
        "| Metric | Count |",
        "|---|---:|",
        f"| Files scanned | {summary['files_scanned']} |",
        f"| File warnings | {summary['file_warnings']} |",
        f"| File failures | {summary['file_failures']} |",
        f"| Function warnings | {summary['function_warnings']} |",
        f"| Function failures | {summary['function_failures']} |",
        f"| Duplicate blocks | {summary['duplicate_blocks']} |",
        f"| Risk findings | {summary['risk_findings']} |",
        f"| Hard gate failures | {summary['hard_gate_failures']} |",
    ]


def markdown_table(title: str, headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    lines = [f"## {title}", "", "| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    lines.append("")
    return lines


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Maintainability CI Report",
        "",
        f"Root: `{report['root']}`",
        f"Branch: `{report.get('git_branch') or '(unknown)'}`",
        "",
        "## Summary",
        "",
        *summary_table(summary),
        "",
    ]
    if report["hard_gate_failures"]:
        lines.extend(["## Hard Gate Failures", ""])
        lines.extend(f"- {gate}" for gate in report["hard_gate_failures"])
        lines.append("")

    file_rows = [[f"`{i['path']}`", str(i["lines"]), i["status"]] for i in report["largest_files"]]
    lines.extend(markdown_table("Largest Files", ["File", "Lines", "Status"], file_rows))

    hot_rows = [
        [f"`{i['path']}`", f"`{i['name']}`", str(i["start_line"]), str(i["lines"]), str(i["complexity"]), i["status"]]
        for i in report["function_hotspots"]
    ]
    lines.extend(markdown_table("Function Hotspots", ["File", "Function", "Line", "Lines", "Complexity", "Status"], hot_rows))
    lines.extend(render_risk_markdown(report))
    lines.extend(render_duplicate_markdown(report))
    lines.extend(render_external_markdown(report))

    return "\n".join(lines)


def render_risk_markdown(report: dict[str, Any]) -> list[str]:
    rows = []
    for item in report["risk_findings"]:
        rows.append([f"`{item['path']}`", str(item["line"]), item["name"], item["text"].replace("|", "\\|")])
    return markdown_table("Risk Pattern Findings", ["File", "Line", "Rule", "Text"], rows)


def render_duplicate_markdown(report: dict[str, Any]) -> list[str]:
    if not report["duplicate_blocks"]:
        return []
    lines = ["## Duplicate Blocks", ""]
    for item in report["duplicate_blocks"][:10]:
        lines.append(f"- Count {item['count']}: " + ", ".join(f"`{loc}`" for loc in item["locations"][:5]))
    lines.append("")
    return lines


def render_external_markdown(report: dict[str, Any]) -> list[str]:
    rows = []
    for item in report.get("external_findings", [])[:50]:
        location = f"{item.get('path', '')}:{item.get('line', 1)}"
        message = str(item.get("message", "")).replace("|", "\\|")
        rows.append([item.get("tool", ""), f"`{item.get('rule_id', '')}`", item.get("level", ""), f"`{location}`", message])
    return markdown_table("External Findings", ["Tool", "Rule", "Level", "Location", "Message"], rows)


def render_ai_prompt(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# AI Remediation Prompt",
        "",
        "You are working in a git repository that has just produced a maintainability audit.",
        "",
        "Your task is to fix the highest-value maintainability issues in a small, reviewable change.",
        "",
        "Rules:",
        "",
        "- Do not rewrite the whole codebase.",
        "- Do not change public behavior unless a finding explicitly requires it.",
        "- Prefer existing architecture, naming, and local patterns.",
        "- Add or update tests for meaningful behavior before changing production code where practical.",
        "- Keep unrelated refactors out of scope.",
        "- If a finding is a false positive, explain why and leave the code unchanged.",
        "- After changes, run the repo's native tests/lints and this maintainability audit again.",
        "",
        "Audit summary:",
        "",
        f"- Files scanned: {summary['files_scanned']}",
        f"- File failures: {summary['file_failures']}",
        f"- Function failures: {summary['function_failures']}",
        f"- Duplicate blocks: {summary['duplicate_blocks']}",
        f"- Risk findings: {summary['risk_findings']}",
        f"- Hard gate failures: {summary['hard_gate_failures']}",
        "",
    ]

    lines.extend(prompt_focus_sections(report))
    lines.extend(prompt_deliverable())
    return "\n".join(lines)


def prompt_focus_sections(report: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    lines.extend(bulleted_section("Start with these hard gates:", report["hard_gate_failures"]))
    hotspot_lines = [
        f"`{i['path']}:{i['start_line']}` `{i['name']}` has {i['lines']} lines and approximate complexity {i['complexity']} ({i['status']})."
        for i in report["function_hotspots"][:10]
    ]
    lines.extend(bulleted_section("Function hotspots to inspect first:", hotspot_lines))
    large_files = [f"`{i['path']}` has {i['lines']} lines ({i['status']})." for i in report["largest_files"][:10] if i["status"] in {"warn", "fail"}]
    lines.extend(bulleted_section("Large files to inspect for responsibility splits:", large_files))
    risks = [f"`{i['path']}:{i['line']}` {i['name']}: {i['text']}" for i in report["risk_findings"][:20]]
    lines.extend(bulleted_section("Risk pattern findings to verify:", risks))
    dupes = [f"Repeated block appears {i['count']} times near: {', '.join(i['locations'][:5])}" for i in report["duplicate_blocks"][:5]]
    lines.extend(bulleted_section("Duplicate blocks to inspect:", dupes))
    return lines


def bulleted_section(title: str, items: list[str]) -> list[str]:
    if not items:
        return []
    return [title, "", *[f"- {item}" for item in items], ""]


def prompt_deliverable() -> list[str]:
    return [
        "Deliverable:",
        "",
        "1. Briefly restate which findings you will fix.",
        "2. Make the smallest coherent patch.",
        "3. Add or update tests when behavior changes or when the current code is hard to verify.",
        "4. Report commands run and results.",
        "5. Leave any larger architectural recommendations as follow-up items, not hidden extra changes.",
    ]


def render_pr_comment(report: dict[str, Any]) -> str:
    summary = report["summary"]
    status = "failed" if report["hard_gate_failures"] else "passed"
    lines = [
        "## Maintainability Audit",
        "",
        f"Status: **{status}**",
        f"Mode: `{report.get('mode', 'full')}`",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Files scanned | {summary['files_scanned']} |",
        f"| File failures | {summary['file_failures']} |",
        f"| Function failures | {summary['function_failures']} |",
        f"| Duplicate blocks | {summary['duplicate_blocks']} |",
        f"| Risk findings | {summary['risk_findings']} |",
        f"| Hard gate failures | {summary['hard_gate_failures']} |",
        "",
    ]
    if report["hard_gate_failures"]:
        lines.extend(["### Hard Gates", ""])
        lines.extend(f"- {gate}" for gate in report["hard_gate_failures"])
        lines.append("")
    if report["function_hotspots"]:
        lines.extend(["### Top Function Hotspots", ""])
        for item in report["function_hotspots"][:5]:
            lines.append(
                f"- `{item['path']}:{item['start_line']}` `{item['name']}` "
                f"({item['lines']} lines, complexity {item['complexity']}, {item['status']})"
            )
        lines.append("")
    lines.append("See `maintainability-report.md` and `maintainability-remediation-prompt.md` artifacts for details.")
    return "\n".join(lines)


def render_agent_instructions(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Maintainability Remediation Instructions",
            "",
            "Use these instructions when asking an AI coding agent to fix audit findings.",
            "",
            "## Operating Rules",
            "",
            "- Treat maintainability as disciplined engineering, not cosmetic cleanup.",
            "- Work from the audit findings, not from broad refactor instinct.",
            "- Keep the patch small, bounded, and reviewable.",
            "- Preserve existing architecture unless a finding proves the boundary is wrong.",
            "- Add tests for behavior changes and for risky untested paths.",
            "- Do not chase unrelated style churn.",
            "- Mark false positives explicitly with rationale.",
            "- Run native repo verification and rerun the maintainability audit before closeout.",
            "",
            "## Current Audit Context",
            "",
            f"- Mode: `{report.get('mode', 'full')}`",
            f"- Files scanned: {report['summary']['files_scanned']}",
            f"- Hard gate failures: {report['summary']['hard_gate_failures']}",
            f"- Function failures: {report['summary']['function_failures']}",
            f"- File failures: {report['summary']['file_failures']}",
            "",
            "Start with hard gates and failed hotspots. Leave larger architecture notes as follow-up recommendations.",
        ]
    )


def instruction_body(target: str, config: dict[str, Any]) -> str:
    pack = config.get("instruction_pack", {})
    project = pack.get("project_name", "this repository")
    test_policy = pack.get("test_policy", "tests for meaningful behavior changes")
    notes = pack.get("architecture_notes", [])
    lines = [
        "# Maintainability Standards for AI-Assisted Code",
        "",
        f"Project: {project}",
        f"Target: {target}",
        "",
        "## Prime Directive",
        "",
        "Write code that is easy for the next developer to understand, test, debug, and safely change.",
        "Do not optimize for passing numeric thresholds while making the implementation less clear.",
        "",
        "## Defaults",
        "",
        "- Keep changes small, bounded, and reviewable.",
        "- Preserve existing architecture, naming, and module boundaries.",
        "- Prefer boring, obvious code over clever abstractions.",
        "- Separate business logic from UI and infrastructure where the repo supports that boundary.",
        f"- Follow the repo test policy: {test_policy}.",
        "- Add tests around meaningful behavior and edge cases, not implementation trivia.",
        "- Make failure modes visible and debuggable.",
        "- Avoid broad rewrites unless explicitly requested.",
        "- Explain false positives or justified complexity instead of contorting code.",
        "",
        "## Maintainability Targets",
        "",
        "- Functions should generally stay below 50 lines; 80+ requires strong justification.",
        "- Approximate complexity above 10 deserves review; above 15 needs refactor or justification.",
        "- Large files should have a clear reason to stay large.",
        "- Duplicate policy/business logic should be consolidated before it drifts.",
        "- Public docs, comments, tests, and code should describe the same behavior.",
        "",
    ]
    if notes:
        lines.extend(["## Project Architecture Notes", ""])
        lines.extend(f"- {note}" for note in notes)
        lines.append("")
    lines.extend(
        [
            "## Before Closeout",
            "",
            "- Run native tests/lints.",
            "- Run the maintainability audit.",
            "- Report commands and results.",
            "- Keep follow-up recommendations separate from the completed patch.",
        ]
    )
    return "\n".join(lines)


def instruction_path_for_target(target: str, output_dir: Path) -> Path:
    mapping = {
        "generic": "AI-MAINTAINABILITY.md",
        "claude-code": "CLAUDE.md",
        "codex": "AGENTS.md",
        "cursor": ".cursor/rules/maintainability.mdc",
        "copilot": ".github/copilot-instructions.md",
        "windsurf": ".windsurf/rules/maintainability.md",
    }
    return output_dir / mapping.get(target, f"{target}-maintainability.md")


def write_instruction_pack(targets: list[str], output_dir: Path, config: dict[str, Any]) -> list[str]:
    written: list[str] = []
    for target in targets:
        path = instruction_path_for_target(target, output_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(instruction_body(target, config) + "\n", encoding="utf-8")
        written.append(str(path))
    return written


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", default=".", help="Repository root to scan.")
    parser.add_argument("--config", help="Path to JSON config.")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--output", help="Output file. Defaults to stdout.")
    parser.add_argument("--prompt-output", help="Optional Markdown prompt for AI-assisted remediation.")
    parser.add_argument("--comment-output", help="Optional Markdown body suitable for a PR comment.")
    parser.add_argument("--agent-instructions-output", help="Optional reusable instructions for AI coding agents.")
    parser.add_argument("--sarif-output", help="Optional SARIF output path for GitHub code scanning.")
    parser.add_argument("--sarif-input", action="append", help="Optional external SARIF file to summarize in reports. Repeatable.")
    parser.add_argument("--changed-only", help="Audit only files changed in a git revspec, for example main...HEAD.")
    parser.add_argument("--baseline", help="Existing baseline JSON. With --fail-on-new, only new findings fail.")
    parser.add_argument("--write-baseline", help="Write current findings to a baseline JSON file.")
    parser.add_argument("--fail-on-new", action="store_true", help="Fail only when findings are not in --baseline.")
    parser.add_argument("--fail-on-gate", action="store_true", help="Exit 1 when hard gates fail.")
    parser.add_argument("--init-agent-standards", action="store_true", help="Write model/tool-specific instruction files.")
    parser.add_argument(
        "--target",
        action="append",
        choices=["generic", "claude-code", "codex", "cursor", "copilot", "windsurf"],
        help="Instruction target. Repeatable. Used with --init-agent-standards.",
    )
    parser.add_argument("--instructions-output-dir", default=".", help="Directory for generated instruction files.")


def write_outputs(args: argparse.Namespace, report: dict[str, Any], rendered: str) -> None:
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    if args.prompt_output:
        Path(args.prompt_output).write_text(render_ai_prompt(report) + "\n", encoding="utf-8")
    if args.comment_output:
        Path(args.comment_output).write_text(render_pr_comment(report) + "\n", encoding="utf-8")
    if args.agent_instructions_output:
        Path(args.agent_instructions_output).write_text(render_agent_instructions(report) + "\n", encoding="utf-8")
    if args.write_baseline:
        write_baseline(args.write_baseline, report)
    if args.sarif_output:
        Path(args.sarif_output).write_text(json.dumps(report_to_sarif(report), indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    config = load_config(args.config)
    if args.init_agent_standards:
        targets = args.target or ["generic", "claude-code", "codex", "cursor", "copilot", "windsurf"]
        write_instruction_pack(targets, Path(args.instructions_output_dir).resolve(), config)
        return 0

    only_paths = changed_paths(root, args.changed_only) if args.changed_only else None
    external_findings = read_sarif_inputs(args.sarif_input)
    report = build_report(root, config, only_paths=only_paths, changed_revspec=args.changed_only, external_findings=external_findings)
    rendered = json.dumps(report, indent=2, sort_keys=True) if args.format == "json" else render_markdown(report)
    write_outputs(args, report, rendered)

    if args.fail_on_new:
        baseline = load_baseline(args.baseline)
        current = finding_fingerprints(report)
        new_findings = current - baseline
        if new_findings:
            return 1
    if args.fail_on_gate and report["hard_gate_failures"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
