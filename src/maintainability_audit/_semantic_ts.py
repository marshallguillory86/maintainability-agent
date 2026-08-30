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

    Only when the repository carries a tsconfig and `tsc` is already on
    the PATH — this module never installs, never runs `npx --yes`, and
    never touches the network. CLI output carries no boundary facts, so
    `typed_boundaries` is empty and policy checks simply find nothing,
    which is weaker coverage, not a violation-free result.
    """
    if not (root / "tsconfig.json").is_file() or not locate("tsc"):
        return None
    result = run(
        "typescript",
        Invocation(argv=("tsc", "--noEmit", "--pretty", "false"),
                   findings_exit_codes=(0, 1, 2)),
        cwd=root,
    )
    # `usable` is the only signal that means "tsc ran": a config error
    # (FAILED, exit 3+) or a findings exit that produced an empty body
    # (NOT_WORKING) both leave `exit_code` set and `stdout` empty, so the
    # old `exit_code is None` guard let them through and reported an empty
    # `diagnostics` list as a clean type check -- absence read as a pass,
    # the class ADR 001 forbids (Grok 63ab820 audit). A RAN with no output
    # is the real "compiled, no type errors".
    if not result.usable:
        return None
    diagnostics = []
    for line in result.stdout.splitlines():
        match = _DIAGNOSTIC.match(line.strip())
        if not match:
            continue
        types = _ASSIGNABILITY.search(match.group("message"))
        diagnostics.append({
            "code": match.group("code"),
            "path": match.group("path").replace("\\", "/"),
            "line": int(match.group("line")),
            "column": int(match.group("column")),
            "symbol": "",
            "actual_type": (types.group("actual") or types.group("actual2")) if types else "",
            "required_type": (types.group("required") or types.group("required2")) if types else "",
            "message": match.group("message"),
        })
    return {
        "tool": "typescript",
        "version": "local",
        "status": "available",
        "diagnostics": diagnostics,
        "typed_boundaries": [],
    }


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
