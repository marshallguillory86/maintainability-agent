"""Practice level: is anything *preventing* the next regression — ADR 007 §2.

Read from configuration and CI, never from source. That separation is the
whole point. A source scan can tell you the code is clean today; it cannot
tell you whether anything stops tomorrow's merge from being terrible. The
hello-world that scored 5.0/A+ had genuinely clean source and no linter, no
CI and no gates, and the second fact was invisible because nothing looked
for it.

The levels, and what each requires:

1. **Nothing detectable.** No linter config, no CI, no gates.
2. **Intent.** Configuration exists on disk, so someone chose standards —
   but nothing runs them, so nothing is binding.
3. **Enforcement.** CI runs a checker. A bad change can fail a build.
4. **Gates.** CI holds a numeric line: a coverage threshold, complexity
   limits, a duplication budget.
5. **Discipline.** Gates plus the practices that keep them honest —
   recorded decisions, pre-commit hooks, type checking.

**Configuration without CI is capped at 2**, and that cap is the rule that
keeps this measurement honest. A repository can hold every config file
ever written and still merge anything; a lint config nobody runs is a
preference, not an enforcement.

Every signal names the file that proves it. A maturity level a reader
cannot check is a grade with no marking scheme, and this one is going to
be argued with — correctly, since it is a judgment about someone's
engineering practice made from the outside.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._operator_reads import open_regular_file
from .metrics import is_excluded

# A repository holding config but running none of it. See the module
# docstring: intent is not enforcement, and the gap between them is the
# single most useful thing this measurement reports.
MAX_WITHOUT_CI = 2

# Where continuous integration lives, across the hosts people actually
# use. Recognising only GitHub Actions would score every GitLab shop at
# level 2 for choosing a different host, which is a statement about this
# tool rather than about them.
CI_LOCATIONS: tuple[str, ...] = (
    ".github/workflows",
    ".gitlab-ci.yml",
    ".circleci/config.yml",
    "Jenkinsfile",
    "azure-pipelines.yml",
    ".travis.yml",
    "bitbucket-pipelines.yml",
    ".drone.yml",
    "buildkite.yml",
    ".woodpecker.yml",
)

# Configuration that declares a standard. Presence is level-2 evidence;
# being invoked from CI is what lifts it to 3.
LINTER_CONFIGS: tuple[str, ...] = (
    ".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml",
    "eslint.config.js", "eslint.config.mjs", "biome.json",
    ".flake8", ".pylintrc", "ruff.toml", ".ruff.toml",
    ".rubocop.yml", "checkstyle.xml", ".golangci.yml", ".golangci.yaml",
    "clippy.toml", ".clang-tidy", "phpcs.xml", ".swiftlint.yml", "detekt.yml",
    # Fortran had no entry in any of these lists, so a Fortran project
    # that configured and ran a linter scored as though it had neither.
    # Measured on a tree with `fortitude.toml`, `.fprettify.rc` and a CI
    # job running both: level 2, zero signals.
    "fortitude.toml", ".fortitude.toml",
)
FORMATTER_CONFIGS: tuple[str, ...] = (
    ".prettierrc", ".prettierrc.json", ".prettierrc.yml", ".editorconfig",
    "rustfmt.toml", ".clang-format", ".scalafmt.conf",
    ".fprettify.rc", "fprettify.ini",
)
TYPE_CONFIGS: tuple[str, ...] = ("mypy.ini", ".mypy.ini", "tsconfig.json", "pyrightconfig.json")
DUPLICATION_CONFIGS: tuple[str, ...] = (".jscpd.json", "jscpd.json", ".cpd.xml")

# Command fragments that mean "a checker runs here".
LINT_COMMANDS = re.compile(
    r"\b(ruff|eslint|pylint|flake8|rubocop|golangci-lint|clippy|checkstyle|"
    r"detekt|swiftlint|phpcs|clang-tidy|biome|fortitude|lint)\b", re.IGNORECASE)
TYPE_COMMANDS = re.compile(r"\b(mypy|pyright|tsc|flow)\b", re.IGNORECASE)
DUPLICATION_COMMANDS = re.compile(r"\b(jscpd|cpd|duplication)\b", re.IGNORECASE)

# A numeric line held in CI, which is the difference between running a
# tool and refusing a change.
COVERAGE_GATES = (
    re.compile(r"--cov-fail-under[= ]\s*(\d+)"),
    re.compile(r"fail_under\s*[:=]\s*(\d+)"),
    re.compile(r"--fail-under[= ]\s*(\d+)"),
    re.compile(r"minimum_coverage\s*[:=]\s*(\d+)"),
    re.compile(r"coverageThreshold"),
)
COMPLEXITY_GATES = (
    re.compile(r"max-complexity\s*[:=]\s*\d+"),
    re.compile(r"\bxenon\b"),
    re.compile(r"max_complexity"),
    re.compile(r"cognitive-complexity"),
)

# Configuration files worth reading for a gate even when CI does not name
# one inline; a threshold in pyproject is still a threshold.
GATE_MANIFESTS: tuple[str, ...] = (
    "pyproject.toml", "setup.cfg", "package.json", "jest.config.js",
    ".coveragerc", "codecov.yml", ".codecov.yml", "tox.ini",
    # A Fortran project declares its build, its tests and — since
    # fortitude 0.9 — its lint settings in `fpm.toml`. Without it, a gate
    # written there was invisible for the same reason one in
    # `pyproject.toml` would have been.
    "fpm.toml",
)


@dataclass
class Practice:
    """A repository's enforcement maturity, and why."""

    level: int
    summary: str
    signals: list[dict[str, str]] = field(default_factory=list)
    # Rules that held the level down, stated so the reader knows what to
    # change. A level without its ceiling explained is a grade, not advice.
    caps: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "summary": self.summary,
            "signals": self.signals,
            "caps": self.caps,
        }


def _read(path: Path, limit: int = 200_000) -> str:
    """A bounded read of a repository file, through a checked handle.

    The head only, so this stays cheap on a large tree — but read
    *through* a checked handle rather than by name, so a FIFO refuses
    instead of stopping the audit dead (D145). `path.open()` on one waits
    for a writer that never comes, and the previous `except OSError`
    could not have caught that: there is no error to catch, only a
    process that never returns.

    Practice detection reads whatever the tree names as CI and toolchain
    configuration, so every path here is repository-controlled.
    """
    try:
        handle = open_regular_file(
            path,
            "Practice detection reads CI and toolchain files from the "
            "audited tree; a device, socket or FIFO would block the audit "
            "rather than describe a practice.",
        )
    except OSError:
        return ""
    try:
        with os.fdopen(handle, "r", encoding="utf-8", errors="replace", closefd=False) as opened:
            return opened.read(limit)
    finally:
        os.close(handle)


def _ci_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for location in CI_LOCATIONS:
        target = root / location
        if target.is_dir():
            found.extend(p for p in sorted(target.rglob("*")) if p.is_file())
        elif target.is_file():
            found.append(target)
    return found


def _present(root: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        target = root / name
        if target.exists():
            return target
    return None


def _pyproject_declares(root: Path, needle: str) -> Path | None:
    """A tool section in a shared manifest, which is config all the same."""
    for name in ("pyproject.toml", "setup.cfg", "package.json"):
        target = root / name
        if target.exists() and needle in _read(target):
            return target
    return None


def _config_signals(root: Path) -> list[dict[str, str]]:
    """Standards declared on disk. Intent, not yet enforcement."""
    signals: list[dict[str, str]] = []
    checks = (
        ("linter-config", LINTER_CONFIGS, "[tool.ruff"),
        ("formatter-config", FORMATTER_CONFIGS, "[tool.black"),
        ("type-config", TYPE_CONFIGS, "[tool.mypy"),
        ("duplication-config", DUPLICATION_CONFIGS, "jscpd"),
    )
    for name, files, needle in checks:
        found = _present(root, files) or _pyproject_declares(root, needle)
        if found:
            signals.append({
                "signal": name,
                "evidence": found.relative_to(root).as_posix(),
            })
    if (root / ".pre-commit-config.yaml").exists():
        signals.append({"signal": "pre-commit", "evidence": ".pre-commit-config.yaml"})
    recorded = _recorded_decisions(root)
    if recorded is not None:
        signals.append({
            "signal": "recorded-decisions",
            "evidence": recorded.relative_to(root).as_posix(),
        })
    return signals


# The conventions a team records decisions under. `adr*` was the only one
# recognised, so `docs/decisions/` — the same practice under a different
# name — was missed and cost the level a discipline signal (Class 3).
_DECISION_GLOBS: tuple[str, ...] = (
    "doc*/adr*", "doc*/**/adr*", "doc*/decision*", "doc*/**/decision*",
    ".adr", ".adr/*",
)


def _recorded_decisions(root: Path) -> Path | None:
    """A decision record on disk under any of the known conventions, or None.
    The folder is never renamed to be found — the detector widens instead."""
    for pattern in _DECISION_GLOBS:
        matches = sorted(root.glob(pattern))
        if matches:
            return matches[0]
    return None


# What CI running a checker looks like, and what holding a numeric line
# looks like. Kept as data so `_ci_signals` stays a loop rather than a
# ladder of conditionals — it reached complexity 21 against this
# project's own limit of 15, found by the tool auditing itself.
CI_COMMAND_SIGNALS: tuple[tuple[str, Any], ...] = (
    ("lint-in-ci", LINT_COMMANDS),
    ("types-in-ci", TYPE_COMMANDS),
    ("duplication-in-ci", DUPLICATION_COMMANDS),
)
CI_GATE_SIGNALS: tuple[tuple[str, tuple[Any, ...]], ...] = (
    ("coverage-gate", COVERAGE_GATES),
    ("complexity-gate", COMPLEXITY_GATES),
)


def _first_match(signals: list[dict[str, str]], name: str) -> bool:
    """Whether this signal is already recorded. One entry per kind."""
    return any(signal["signal"] == name for signal in signals)


def _scan_ci_file(body: str, where: str, signals: list[dict[str, str]]) -> None:
    """One CI file's contribution, appended in place."""
    for name, pattern in CI_COMMAND_SIGNALS:
        found = None if _first_match(signals, name) else pattern.search(body)
        if found:
            signals.append({"signal": name, "evidence": f"{where}: {found.group(0)}"})
    for name, patterns in CI_GATE_SIGNALS:
        if _first_match(signals, name):
            continue
        if any(pattern.search(body) for pattern in patterns):
            signals.append({"signal": name, "evidence": where})


def _gate_manifests(root: Path, excludes: list[str]) -> list[tuple[str, Path]]:
    """Every gate manifest anywhere in the tree, shallowest first so a root
    gate is cited before a nested one, and skipping what discovery would
    not score: `node_modules/**/package.json` is someone else's gate, not
    this repository's (plan-81dc6870 Class 3)."""
    found: list[tuple[str, Path]] = []
    for name in GATE_MANIFESTS:
        for path in root.rglob(name):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if is_excluded(rel, excludes):
                continue
            found.append((rel, path))
    return sorted(found, key=lambda item: (item[0].count("/"), item[0]))


def _manifest_gates(root: Path, signals: list[dict[str, str]], excludes: list[str]) -> None:
    """A threshold declared in a manifest, which CI need not spell out.

    `pytest --cov` picks up `fail_under` from `pyproject.toml` — the root
    one or a nested `api/pyproject.toml` — without the workflow naming it,
    and a gate that holds is a gate however it is wired. Nested manifests
    are read too; vendored ones are not (Class 3).
    """
    manifests = [(rel, _read(path)) for rel, path in _gate_manifests(root, excludes)]
    for name, patterns in CI_GATE_SIGNALS:
        if _first_match(signals, name):
            continue
        for rel, text in manifests:
            if any(pattern.search(text) for pattern in patterns):
                signals.append({"signal": name, "evidence": rel})
                break


def _ci_signals(root: Path, ci: list[Path], excludes: list[str]) -> list[dict[str, str]]:
    """What CI actually runs, and which numeric lines it holds."""
    signals: list[dict[str, str]] = []
    for path in ci:
        _scan_ci_file(_read(path), path.relative_to(root).as_posix(), signals)
    _manifest_gates(root, signals, excludes)
    return signals


def practice_level(root: Path, config: dict[str, Any] | None = None) -> Practice:
    """How much of this repository's quality is actually enforced.

    Never reads source. `test_practice_reads_configuration_and_never_source`
    holds that structurally by scoring a tidy tree and an awful one with
    identical configuration and requiring the same answer — if practice
    drifted with code quality it would be the condition score under a
    second name, and the matrix that makes the pair useful would collapse.

    `config` supplies the exclude patterns so a nested gate manifest under
    a vendored directory is not read as this repository's gate (Class 3).
    """
    excludes = list(((config or {}).get("paths") or {}).get("exclude_patterns", []))
    ci = _ci_files(root)
    signals = _config_signals(root)
    caps: list[str] = []

    if not ci:
        return _without_ci(signals, caps)

    signals += _ci_signals(root, ci, excludes)
    level, summary, capped = _level_with_ci({signal["signal"] for signal in signals})
    return Practice(level=level, summary=summary, signals=signals, caps=caps + capped)


def _without_ci(signals: list[dict[str, Any]], caps: list[str]) -> Practice:
    """The ceiling when nothing runs the checks on a change.

    Configuration without CI is a standard nobody enforces, so it earns
    one level for existing and no more. The cap is stated rather than
    implied: a repository at level 2 with a full linter config is being
    told what to fix, not just what it scored.
    """
    if signals:
        caps = [*caps, (
            "no CI configuration found, so nothing runs these checks on a "
            f"change; capped at level {MAX_WITHOUT_CI}"
        )]
        summary = "standards are configured but nothing runs them on a change"
    else:
        summary = "no enforcement detected: no linter configuration, no CI"
    return Practice(
        level=min(MAX_WITHOUT_CI, 1 + (1 if signals else 0)),
        summary=summary, signals=signals, caps=caps,
    )


def _level_with_ci(kinds: set[str]) -> tuple[int, str, list[str]]:
    """Level, summary and any cap, for a repository that has CI.

    The ladder in one place: a gate plus discipline plus checks that
    actually run is 5; a numeric gate alone is 4; checks that run but
    cannot fail is 3, and says so; CI that runs no checks is the
    no-enforcement ceiling.
    """
    checks_run = bool(kinds & {"lint-in-ci", "types-in-ci", "duplication-in-ci"})
    gates = kinds & {"coverage-gate", "complexity-gate"}
    discipline = kinds & {"pre-commit", "recorded-decisions", "type-config"}

    if gates and checks_run and len(discipline) >= 2:
        return 5, "gated in CI, with recorded decisions and local enforcement", []
    if gates:
        return 4, "CI holds a numeric quality gate", []
    if checks_run:
        return 3, "CI runs quality checks on every change", [
            "no coverage or complexity gate found; a check that cannot fail is advisory"
        ]
    return MAX_WITHOUT_CI, "CI exists but runs no quality checks", [
        "CI runs no linter, type checker or duplication check"
    ]
