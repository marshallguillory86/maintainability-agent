"""Competing libraries for one concern, in the same repository.

Three HTTP clients means three error shapes, three retry stories, three
sets of behaviour to learn. The cost is not duplication — each call site
may be perfectly written — it is that no single mental model covers the
codebase. A reader who has learned how requests fail still does not know
how *these* requests fail.

This is the failure mode of independent generation: each answer is
locally reasonable, and nothing reconciles them.

**This detector needs a curated list, and that is a real cost.** There is
no structural way to know that ``moment`` and ``date-fns`` compete while
``react`` and ``react-dom`` do not; it requires knowing what the packages
do. The list below is therefore deliberately small and restricted to
concerns whose alternatives are well known and change slowly. It is
incomplete by construction. Extend it per-repo with ``idiom_groups`` in
config rather than waiting for this file to grow.

Four conservatisms keep it quiet, three of them added after the first
run against the reference corpus reported nothing but false positives:

- **Only real source files are read.** The first version scanned every
  included extension, so a package named in a fenced code block inside a
  Markdown skill document counted as an import. Two of three findings on
  one repository came from documentation prose.
- **Standalone scripts are excluded.** ``black`` was reported as running
  two HTTP clients: ``aiohttp`` in the ``blackd`` daemon and ``urllib3``
  in a CI helper under ``scripts/``. Those are separate programs that
  happen to share a repository, not one codebase with two mental models.
- **Test files are excluded.** Test code legitimately reaches for
  whatever a case needs, and a test helper using a second HTTP client is
  not architectural drift.
- **A repository's own package never counts against it.** ``httpx``
  imports ``httpx``; that is not divergence.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from .declarations import DECLARATION_SUFFIXES
from .metrics import is_test_path, read_lines

# Concerns where using two at once genuinely means two mental models.
# Deliberately short: every entry is a claim that these alternatives are
# mutually redundant, and a wrong claim costs a false finding.
#
# Test frameworks are absent on purpose — pytest runs unittest cases, and
# a project supporting both is normal rather than divergent.
DEFAULT_IDIOM_GROUPS: dict[str, list[str]] = {
    "http client": [
        "requests", "httpx", "aiohttp", "urllib3",
        "axios", "got", "superagent", "node-fetch", "ky",
    ],
    "date handling": ["moment", "dayjs", "date-fns", "luxon", "arrow", "pendulum"],
    "client state": ["redux", "@reduxjs/toolkit", "zustand", "jotai", "recoil", "mobx", "valtio"],
    "schema validation": [
        "zod", "yup", "joi", "ajv", "superstruct",
        "pydantic", "marshmallow", "cerberus", "voluptuous",
    ],
    "orm": [
        "sqlalchemy", "peewee", "tortoise",
        "prisma", "typeorm", "sequelize", "drizzle-orm", "knex",
    ],
    "web framework": ["flask", "fastapi", "bottle", "sanic", "express", "koa", "fastify", "hapi"],
}

_PY_IMPORT_RE = re.compile(r"^\s*(?:from\s+([A-Za-z_][\w.]*)|import\s+([A-Za-z_][\w.]*))")
_JS_IMPORT_RE = re.compile(r"""(?:from|require\s*\()\s*['"]([^'"]+)['"]""")

_PY_SUFFIX = ".py"

# Imports only ever appear in code. Markdown, CSS and HTML are excluded
# because a package named in a documentation code block is not a
# dependency of the program.
_SOURCE_SUFFIXES = DECLARATION_SUFFIXES - {".html"}

# Directory names that hold programs separate from the codebase proper.
# A release helper reaching for a different HTTP client is not the
# architectural drift this measures.
_STANDALONE_DIRS = frozenset({"scripts", "script", "tools", "tooling", "bin", "examples", "example", "benchmarks"})


def _is_standalone(rel: str) -> bool:
    return any(part.lower() in _STANDALONE_DIRS for part in rel.split("/")[:-1])


def _root_package(module: str) -> str:
    """Reduce an import path to the distribution it comes from."""
    module = module.strip()
    if module.startswith("."):
        return ""
    if module.startswith("@"):
        parts = module.split("/")
        return "/".join(parts[:2])
    return module.split("/")[0].split(".")[0]


def imported_packages(path: Path, lines: list[str]) -> set[str]:
    """Third-party packages imported by one file, relative imports dropped."""
    found: set[str] = set()
    pattern_is_python = path.suffix == _PY_SUFFIX
    for line in lines:
        if pattern_is_python:
            match = _PY_IMPORT_RE.match(line)
            names = [group for group in (match.groups() if match else ()) if group]
        else:
            names = _JS_IMPORT_RE.findall(line)
        for name in names:
            root = _root_package(name)
            if root:
                found.add(root.lower())
    return found


def _own_package_names(root: Path) -> set[str]:
    """Names this repository publishes, which cannot be divergence.

    Taken from the directory names under a ``src`` layout plus the repo
    directory itself — enough to stop ``httpx`` reporting itself.
    """
    names = {root.name.lower().replace("-", "_"), root.name.lower()}
    source = root / "src"
    if source.is_dir():
        names.update(child.name.lower() for child in source.iterdir() if child.is_dir())
    return names


def idiom_groups(config: dict[str, Any]) -> dict[str, list[str]]:
    """Configured groups, falling back to the shipped list."""
    configured = config.get("idiom_groups")
    return configured if isinstance(configured, dict) and configured else DEFAULT_IDIOM_GROUPS


def divergent_idioms(root: Path, files: list[Path], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Concerns served by more than one library in production code."""
    groups = idiom_groups(config)
    membership = {
        member.lower(): concern for concern, members in groups.items() for member in members
    }
    own = _own_package_names(root)
    users: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    for path in files:
        if path.suffix not in _SOURCE_SUFFIXES:
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        if is_test_path(rel) or _is_standalone(rel):
            continue
        for package in imported_packages(path, read_lines(path)):
            concern = membership.get(package)
            if concern and package not in own:
                users[concern][package].add(rel)

    findings = []
    for concern, packages in users.items():
        if len(packages) < 2:
            continue
        detail = sorted(
            ({"package": name, "files": len(paths), "example": sorted(paths)[0]} for name, paths in packages.items()),
            key=lambda item: -item["files"],
        )
        findings.append({"concern": concern, "packages": detail, "count": len(detail)})
    findings.sort(key=lambda item: -item["count"])
    return findings
