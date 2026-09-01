"""TypeScript type facts and operation-set evidence — ADR 003's first language.

Two kinds of raw material come from here, and neither is a finding yet:

* **Type facts** — diagnostics and typed boundaries, from a recorded,
  versioned analysis file or a locally installed `tsc`. Never installed,
  never fetched: an absent checker means *unknown* coverage, and
  `_semantic` reports it that way rather than as a clean run.
* **Operation sets** — string-literal populations read from the
  TypeScript source itself: the same closed name set appearing in
  dispatch comparisons, a capability membership check, and a
  description table. Pure text analysis, deliberately conservative —
  it nominates candidates and can prove nothing.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from ._runner import Invocation, locate, run
from .metrics import within

# Where a repository can check in its recorded type analysis. Versioned
# input, not cache: the recording names the tool and version so the
# same inputs reproduce the same findings byte for byte.
RECORDED_ANALYSIS = ".maintainability/type-analysis.json"

_TS_SUFFIXES = (".ts", ".tsx")
_SKIP_PARTS = {".git", "node_modules", "recordings"}

# tsc --noEmit --pretty false: `src/file.ts(8,16): error TS2345: message`
_DIAGNOSTIC = re.compile(
    r"^(?P<path>[^()\n]+)\((?P<line>\d+),(?P<column>\d+)\): error (?P<code>TS\d+): (?P<message>.*)$"
)
_ASSIGNABILITY = re.compile(
    r"Argument of type '(?P<actual>[^']+)' is not assignable to parameter of type '(?P<required>[^']+)'"
    r"|Type '(?P<actual2>[^']+)' is not assignable to type '(?P<required2>[^']+)'"
)

_DISPATCH = re.compile(r"===\s*\"([A-Za-z_][\w-]*)\"|case\s+\"([A-Za-z_][\w-]*)\"\s*:")
# Contents validated by `_names` afterwards; the bracket match itself is
# kept linear (no nested quantifiers) because it runs over arbitrary code.
_CAPABILITY_ARRAY = re.compile(r"\[([^\][]*)\]\s*\.includes\(")
_DESCRIPTION_KEY = re.compile(r"^\s*([A-Za-z_]\w*)\s*:\s*\"", re.MULTILINE)
_QUOTED = re.compile(r"\"([A-Za-z_][\w-]*)\"")


def recorded_type_analysis(root: Path) -> dict[str, Any] | None:
    """The checked-in recording, when the repository keeps one."""
    path = root / RECORDED_ANALYSIS
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return payload if isinstance(payload, dict) and payload.get("tool") else None


def local_tsc_analysis(root: Path) -> dict[str, Any] | None:
    """Diagnostics from an already-installed compiler, or nothing.

    Runs across the repository root *and* any workspace beneath it that
    carries a `tsconfig.json` — TS monorepos keep the config in `web/` or
    `packages/*`, not the root, and a root-only check went blind on exactly
    the repos this is for. Uses a `tsc` that is already present: the
    workspace's own `node_modules/.bin/tsc`, the root's, or one on the PATH.
    Never installs, never runs `npx --yes`, never touches the network — a
    project-local compiler is the standard install, not an acquisition.

    An absent checker, or a `tsc` that cannot run usably, leaves coverage
    *unknown*, not clean: a config error (FAILED, exit 3+) or a findings
    exit with an empty body (NOT_WORKING) both leave `stdout` empty, and
    reading that as a violation-free type check is the absence-as-a-pass
    the class ADR 001 forbids (Grok 63ab820 audit). Only a usable run
    counts; a RAN with no output is the real "compiled, no type errors".
    CLI output carries no boundary facts, so `typed_boundaries` is empty.
    """
    diagnostics: list[dict[str, Any]] = []
    ran = False
    for project in _tsconfig_project_dirs(root):
        tsc = _resolve_tsc(root, project)
        if tsc is None:
            continue
        result = run(
            "typescript",
            Invocation(argv=(tsc, "--noEmit", "--pretty", "false"),
                       findings_exit_codes=(0, 1, 2)),
            cwd=project,
        )
        if not result.usable:
            continue
        ran = True
        diagnostics.extend(
            _parse_diagnostics(result.stdout, project.relative_to(root)))
    if not ran:
        return None
    return {
        "tool": "typescript",
        "version": "local",
        "status": "available",
        "diagnostics": _dedup(diagnostics),
        "typed_boundaries": [],
    }


def _tsconfig_project_dirs(root: Path) -> list[Path]:
    """The root and every workspace beneath it that carries a `tsconfig.json`.

    `node_modules`/`.git`/recordings and hidden directories are pruned, and
    the walk stops at depth 3 so a large tree stays bounded.
    """
    dirs: list[Path] = []
    for current, subdirs, files in os.walk(root):
        depth = len(Path(current).relative_to(root).parts)
        subdirs[:] = [] if depth >= 3 else [
            name for name in subdirs
            if name not in _SKIP_PARTS and not name.startswith(".")
        ]
        if "tsconfig.json" in files:
            dirs.append(Path(current))
    return sorted(dirs)


def _resolve_tsc(root: Path, project: Path) -> str | None:
    """An already-installed `tsc`: the workspace's own, then the root's,
    then one on the PATH. Never installs and never fetches."""
    for base in (project, root):
        local = base / "node_modules" / ".bin" / "tsc"
        if local.is_file():
            return str(local)
    return "tsc" if locate("tsc") else None


def _parse_diagnostics(stdout: str, prefix: Path) -> list[dict[str, Any]]:
    """tsc's `path(line,col): error TSxxxx: message` lines, with paths
    re-rooted from the workspace `tsc` ran in back to the repository."""
    diagnostics: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        match = _DIAGNOSTIC.match(line.strip())
        if not match:
            continue
        types = _ASSIGNABILITY.search(match.group("message"))
        reported = match.group("path").replace("\\", "/")
        path = reported if str(prefix) == "." else (prefix / reported).as_posix()
        diagnostics.append({
            "code": match.group("code"),
            "path": path,
            "line": int(match.group("line")),
            "column": int(match.group("column")),
            "symbol": "",
            "actual_type": (types.group("actual") or types.group("actual2")) if types else "",
            "required_type": (types.group("required") or types.group("required2")) if types else "",
            "message": match.group("message"),
        })
    return diagnostics


def _dedup(diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One diagnostic per (code, path, line, column): nested project
    references can report the same error from two tsconfigs."""
    seen: set[tuple[str, str, int, int]] = set()
    unique: list[dict[str, Any]] = []
    for item in diagnostics:
        key = (item["code"], item["path"], item["line"], item["column"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def discover_type_analysis(root: Path) -> dict[str, Any] | None:
    """Recording first — it is versioned and reproducible — then local tsc."""
    return recorded_type_analysis(root) or local_tsc_analysis(root)


def _typescript_sources(root: Path) -> list[Path]:
    # `within` because `is_file()` follows symlinks: a `linked.ts`
    # pointing at a file outside the root would otherwise be read into a
    # semantic finding, the same escape D36 closed for `iter_files` and
    # `expand_files`. This walk builds its own file list from `rglob`
    # rather than reusing theirs, so the land check has to be repeated
    # here or it is not applied here at all.
    resolved_root = root.resolve()
    return sorted(
        path for path in root.rglob("*")
        if path.suffix in _TS_SUFFIXES
        and path.is_file()
        and within(resolved_root, path)
        and not (set(path.relative_to(root).parts[:-1]) & _SKIP_PARTS)
    )


def _names(fragment: str) -> frozenset[str]:
    return frozenset(_QUOTED.findall(fragment))


def operation_sets(root: Path) -> list[dict[str, Any]]:
    """Closed name sets that recur across three distinct roles in one file.

    All three roles, or nothing: a list of labels rendered into a menu
    is one descriptive role, and flagging it would be exactly the
    string-flagging ADR 003 option A rejects. Requiring dispatch *and*
    capability *and* description keeps this at the precision end —
    misses are accepted, nominations must be real.
    """
    found: list[dict[str, Any]] = []
    for path in _typescript_sources(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        dispatch = frozenset(
            name for pair in _DISPATCH.findall(text) for name in pair if name
        )
        if len(dispatch) < 2:
            continue
        capability: frozenset[str] = frozenset()
        for arrays in _CAPABILITY_ARRAY.findall(text):
            capability |= _names(arrays)
        description = frozenset(_DESCRIPTION_KEY.findall(text))
        if dispatch <= capability and dispatch <= description:
            found.append({
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "operation_names": sorted(dispatch),
                "roles": ["capability", "description", "dispatch"],
            })
    return found
