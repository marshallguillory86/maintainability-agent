"""Private helpers that nothing in the repository references.

Agents leave debris: a helper written for an approach that was abandoned
two prompts later, still sitting in the file. It compiles, it is tested
by nothing, and the next reader has to work out whether it matters.

Finding unreferenced code is easy to do badly. A naive "no callers"
scan reports a library's entire public surface, every framework hook,
every dynamic dispatch target, and every interface implementation — all
of which are called, just not from anywhere this scanner can see. A
finding class that is mostly wrong is worse than no finding at all,
because it teaches people to skim past the report.

So the scope is deliberately narrow: **only declarations the language
itself marks as internal** are ever candidates.

- Python: a leading underscore, which is the convention for "not part of
  the API". Dunder methods are excluded — they are called by the runtime.
- JS/TS: a declaration with no ``export`` keyword, so it cannot be
  imported elsewhere.

A private helper that nothing references is dead by construction: no
external consumer can reach it, because privacy is exactly the claim
that none exists. Everything else — public functions, decorated
declarations, test files — is left alone, and this under-reports on
purpose.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from .declarations import DECLARATION_SUFFIXES, declaration_ranges
from .metrics import is_test_path, read_lines

_IDENTIFIER_RE = re.compile(r"[A-Za-z_$][\w$]*")

# Names the runtime or a framework calls without any visible reference.
_DUNDER_RE = re.compile(r"^__\w+__$")


# A C-family declaration must bind a name to be a candidate. An
# object-literal method — `beforeBreadcrumb(crumb) { … }` inside a config
# object — binds nothing and is invoked by whoever receives the object.
# Sentry's callback in a real repo was reported dead for exactly this
# reason. Requiring a binding keyword or an arrow excludes the whole
# class, along with class methods, which callers reach through instances.
_BINDING_RE = re.compile(r"\b(?:function|const|let|var)\b|=>")


def _is_private(name: str, suffix: str, declaration_line: str) -> bool:
    """Whether the language marks this declaration as internal.

    Privacy is the load-bearing assumption: it is the author's own claim
    that nothing outside this repository calls the thing, which is what
    makes "no references here" sufficient evidence that it is dead.
    """
    if _DUNDER_RE.match(name):
        return False
    if suffix == ".py":
        return name.startswith("_")
    if not _BINDING_RE.search(declaration_line):
        return False
    return "export" not in declaration_line


def _is_decorated(lines: list[str], start: int) -> bool:
    """Whether a decorator sits immediately above the declaration.

    A decorator usually means something else calls this — a route table,
    a fixture registry, an event hook. The reference exists; it is just
    not a call site this scanner can follow.
    """
    for number in range(start - 1, 0, -1):
        text = lines[number - 1].strip()
        if not text:
            continue
        return text.startswith("@")
    return False


def reference_counts(files: list[Path]) -> Counter[str]:
    """How often each identifier appears across the repository.

    Counted over the **raw** source, deliberately. The masked copy was
    tried first and was wrong: an f-string interpolation is live code,
    so blanking string literals erased real call sites. Flask's
    ``_get_werkzeug_version`` is called from inside an f-string and was
    reported dead.

    Counting raw text means a name appearing only in a comment or a
    string also reads as a reference. That hides a dead function rather
    than inventing one — the direction this tool always errs in.
    """
    counts: Counter[str] = Counter()
    for path in files:
        for line in read_lines(path):
            counts.update(_IDENTIFIER_RE.findall(line))
    return counts


def _scannable(root: Path, files: list[Path]) -> list[tuple[Path, str]]:
    """Files that can hold a dead private declaration, with their rel paths."""
    out = []
    for path in files:
        if path.suffix not in DECLARATION_SUFFIXES:
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        if not is_test_path(rel):
            out.append((path, rel))
    return out


def _dead_in_file(path: Path, rel: str, counts: Counter[str]) -> list[dict[str, Any]]:
    lines = read_lines(path)
    ranges, _ = declaration_ranges(path, lines)
    findings = []
    for decl in ranges:
        declaration_line = lines[decl.start - 1] if decl.start <= len(lines) else ""
        # One occurrence is the definition itself; anything more is a use.
        unreferenced = counts[decl.name] <= 1
        if (
            unreferenced
            and _is_private(decl.name, path.suffix, declaration_line)
            and not _is_decorated(lines, decl.start)
        ):
            findings.append(
                {
                    "path": rel,
                    "name": decl.name,
                    "kind": decl.kind,
                    "start_line": decl.start,
                    "lines": decl.end - decl.start + 1,
                }
            )
    return findings


def dead_declarations(root: Path, files: list[Path]) -> list[dict[str, Any]]:
    """Private declarations whose names appear nowhere but their own definition."""
    counts = reference_counts(files)
    findings: list[dict[str, Any]] = []
    for path, rel in _scannable(root, files):
        findings.extend(_dead_in_file(path, rel, counts))
    findings.sort(key=lambda item: (-item["lines"], item["path"]))
    return findings
