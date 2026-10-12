"""Analyzer output the developer's own pipeline wrote (Decision 17).

The catalog holds some 760 tools and this one runs a pinned handful. The
rest run where they already run — a .NET build runs the Roslyn analyzers,
and executes code from the repository it builds, which nothing here does —
and this reads the SARIF they wrote. Each file is declared in
`analyzers.pipeline_results` with the concerns it covers, because one file
can mix style, documentation and dead-code rules and only its owner knows
which they asked for.

A file becomes a coverage row of its own tier, `pipeline`: it examines its
declared concerns for the languages its results name, never the languages
it does not, and is never counted as a tool this run attempted. Its
findings are listed and do not score.
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

from ._analysis import Analysis, ToolCoverage
from ._catalog import PolicyError, settings_from
from ._discovery import CATALOG_LANGUAGE
from ._generic import parse_sarif
from ._metrics_types import KNOWN_SOURCE_SUFFIXES
from ._runner import Outcome
from .config import PathNotAllowed, read_operator_file, repository_path
from .git_tools import GitCommandFailed, run_git

#: Matches no catalog language, so a row carrying it examines nothing.
NO_LANGUAGE = ("unstated",)


def add_pipeline_results(analysis: Analysis, root: Path, config: dict[str, Any]) -> None:
    """Append one coverage row, and its findings, per declared file.

    Never raises, like `analyze`: a block it refuses is already recorded
    there as the analysis error, and must degrade the audit, not end it.
    """
    try:
        declarations = settings_from(config)["pipeline_results"]
    except PolicyError:
        return
    for declared in declarations:
        row, findings = _read_one(root, declared)
        analysis.coverage.append(row)
        analysis.findings.extend(findings)


def _read_one(root: Path, declared: dict[str, Any]) -> tuple[ToolCoverage, list]:
    named = declared["path"]
    covers = tuple(declared["covers"])
    try:
        path = repository_path(root, named, named)
        text = read_operator_file(path)
        extraction = parse_sarif(text, "pipeline", ", ".join(covers))
        payload = json.loads(text)
    except (PathNotAllowed, OSError, ValueError) as error:
        return ToolCoverage(
            slug=named, outcome=Outcome.FAILED.value, tier="pipeline", concepts=covers,
            languages=NO_LANGUAGE,
            detail=f"declared in analyzers.pipeline_results as {named}, and not read: {error}",
        ), []
    findings = list(extraction.findings)
    languages = _languages(payload, declared.get("languages") or ())
    stale = path.stat().st_mtime < _last_commit_time(root)
    detail = f"read from {named}, which your pipeline wrote"
    if stale:
        detail += "; the file is older than the last commit, so it may not describe this code"
    if languages == NO_LANGUAGE:
        detail += ("; it names no source file and declares no languages, so it examines "
                   "nothing — add `languages` to its declaration")
    tools = sorted({f.tool for f in findings}) or [_driver(payload) or named]
    return ToolCoverage(
        slug=", ".join(tools), outcome=Outcome.RAN.value, tier="pipeline", concepts=covers,
        findings=len(findings), languages=languages, stale=stale, detail=detail,
    ), findings


def _languages(payload: dict[str, Any], declared: Any) -> tuple[str, ...]:
    """Catalog languages of the source files the results and artifacts name."""
    names = {KNOWN_SOURCE_SUFFIXES.get(PurePosixPath(uri).suffix.lower())
             for uri in _uris(payload)} | set(declared)
    slugs = sorted({CATALOG_LANGUAGE[name] for name in names if name in CATALOG_LANGUAGE})
    return tuple(slugs) or NO_LANGUAGE


def _uris(payload: dict[str, Any]) -> list[str]:
    """Every file a result points at, and every artifact the run lists."""
    uris = []
    for run in payload.get("runs", []):
        for result in run.get("results", []):
            for location in result.get("locations") or []:
                physical = location.get("physicalLocation") or {}
                uris.append((physical.get("artifactLocation") or {}).get("uri", ""))
        for artifact in run.get("artifacts", []):
            uris.append((artifact.get("location") or {}).get("uri", ""))
    return uris


def _driver(payload: dict[str, Any]) -> str:
    runs = payload.get("runs") or [{}]
    return ((runs[0].get("tool") or {}).get("driver") or {}).get("name", "")


def _last_commit_time(root: Path) -> float:
    try:
        return float(run_git(["log", "-1", "--format=%ct"], root) or 0)
    except (GitCommandFailed, ValueError):
        return 0.0
