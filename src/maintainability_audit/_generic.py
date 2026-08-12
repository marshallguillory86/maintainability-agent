"""Adapters without bespoke code — ADR 006.

Ten hand-written adapters against a catalog of 759 tools implies 749 more to
write, which is not a plan. It is also unnecessary: most analyzers emit one of
a few standard formats, and a format needs one parser, not one per tool.

So a tool is added as **data** — a command line, a format name, the concerns
it covers — and the parsing is shared. Bespoke adapters remain for tools whose
output is genuinely their own (lizard's CSV column order, interrogate's
sentence), but they become the exception rather than the unit of work.

What still needs a human per tool is small and honest: how to invoke it, which
flag makes it emit a machine-readable format, and what it measures. That is a
few lines of declaration, not an afternoon of reverse engineering, and it
cannot be automated away entirely because a tool's own documentation is the
only source for it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from ._adapters import BaseAdapter, Extraction
from ._metrics_types import Finding
from ._runner import ToolResult


@dataclass(frozen=True)
class ToolSpec:
    """Everything needed to run and read one tool, as declaration.

    Adding a tool means adding one of these. No parser, no subclass, no
    change anywhere else — which is the difference between a catalog that
    can grow and one that cannot.
    """

    slug: str
    executable: str
    output_format: str  # "sarif" | "checkstyle" | "json-findings"
    concerns: tuple[str, ...]
    args: tuple[str, ...] = ()
    version_flag: str = "--version"
    exclude_flag: str = ""
    findings_exit_codes: tuple[int, ...] = (0, 1)
    # Where findings live in a JSON document, for the json-findings format:
    # a dotted path, plus the keys holding path, line and message.
    json_path: str = ""
    json_keys: tuple[str, str, str] = ("path", "line", "message")


# Tools name their rules under different keys, and a rule id is what
# makes a finding groupable and suppressible. pylint's `symbol` is
# preferred over its `message-id` because `missing-module-docstring`
# tells a reader more than `C0114`.
_RULE_KEYS = ("symbol", "rule", "code", "ruleId", "check_name", "message-id")


def _rule_id(item: dict[str, Any]) -> str | None:
    for key in _RULE_KEYS:
        value = item.get(key)
        if value:
            return str(value)
    return None


def _dig(payload: Any, dotted: str) -> Any:
    for part in filter(None, dotted.split(".")):
        if isinstance(payload, dict):
            payload = payload.get(part)
        else:
            return None
    return payload


def parse_sarif(text: str, slug: str, concern: str) -> Extraction:
    """SARIF 2.1.0 — the interchange format most modern analyzers speak.

    Worth supporting first because it is the only format a tool can adopt
    that costs this project nothing: no parser, no release coupling, no
    reverse engineering when the tool changes its text output.
    """
    payload = json.loads(text or "{}")
    findings = []
    for run in payload.get("runs", []):
        driver = run.get("tool", {}).get("driver", {}).get("name", slug)
        for result in run.get("results", []):
            locations = result.get("locations") or [{}]
            physical = (locations[0].get("physicalLocation") or {})
            region = physical.get("region") or {}
            findings.append(Finding(
                concept=concern,
                path=(physical.get("artifactLocation") or {}).get("uri", ""),
                line=region.get("startLine"),
                message=(result.get("message") or {}).get("text", ""),
                tool=driver,
                rule=result.get("ruleId"),
            ))
    return Extraction(findings=tuple(findings))


def parse_checkstyle(text: str, slug: str, concern: str) -> Extraction:
    """Checkstyle XML — what most JVM and PHP analyzers emit.

    PMD, Checkstyle, phpcs and several others share it, so one parser
    reaches a whole ecosystem the project currently cannot touch.
    """
    root = ElementTree.fromstring(text or "<checkstyle/>")  # noqa: S314 - tool output, not untrusted input
    findings = []
    for file_node in root.iter("file"):
        path = file_node.get("name", "")
        for error in file_node:
            findings.append(Finding(
                concept=concern,
                path=path,
                line=int(error.get("line") or 0) or None,
                message=error.get("message", ""),
                tool=slug,
                rule=error.get("source") or error.get("rule"),
            ))
    return Extraction(findings=tuple(findings))


def parse_json_findings(text: str, spec: ToolSpec, concern: str) -> Extraction:
    """A JSON array of findings, wherever the tool happens to put it.

    Covers the large middle ground of tools that emit structured output in
    their own shape: the declaration says where the array is and which
    keys hold the location, and no code is written.
    """
    payload = json.loads(text or "[]")
    items = _dig(payload, spec.json_path) if spec.json_path else payload
    if not isinstance(items, list):
        raise ValueError(
            f"{spec.slug}: expected a list at {spec.json_path or '<root>'}, "
            f"got {type(items).__name__}"
        )
    path_key, line_key, message_key = spec.json_keys
    findings = tuple(
        Finding(
            concept=concern,
            path=str(_dig(item, path_key) or ""),
            line=_dig(item, line_key),
            message=str(_dig(item, message_key) or ""),
            tool=spec.slug,
            rule=_rule_id(item),
        )
        for item in items
        if isinstance(item, dict)
    )
    return Extraction(findings=findings)


def parse_json_lines(text: str, spec: ToolSpec, concern: str) -> Extraction:
    """One JSON object per line — what mypy and several others emit.

    A distinct format from a JSON array and worth its own parser rather
    than a special case: streaming tools prefer it precisely because the
    document is never complete, so no array wrapper ever arrives.
    """
    path_key, line_key, message_key = spec.json_keys
    findings = []
    for raw in (text or "").splitlines():
        stripped = raw.strip()
        if not stripped.startswith("{"):
            # Summary lines and progress noise share the stream. Skipping
            # non-objects rather than failing keeps a chatty tool usable.
            continue
        item = json.loads(stripped)
        findings.append(Finding(
            concept=concern,
            path=str(_dig(item, path_key) or ""),
            line=_dig(item, line_key),
            message=str(_dig(item, message_key) or ""),
            tool=spec.slug,
            rule=_rule_id(item),
        ))
    return Extraction(findings=tuple(findings))


PARSERS = {"sarif", "checkstyle", "json-findings", "json-lines"}


class DeclaredAdapter(BaseAdapter):
    """An adapter built from a :class:`ToolSpec` rather than written."""

    def __init__(self, spec: ToolSpec) -> None:
        super().__init__(
            slug=spec.slug,
            # Standard formats carry findings, not per-unit metrics, so a
            # declared tool is a verdict emitter and can never contribute a
            # rate. Anything measuring a population needs a real adapter,
            # which is the honest boundary rather than a limitation.
            emits="verdict",
            executable=spec.executable,
            concepts=spec.concerns,
            version_flag=spec.version_flag,
            exclude_flag=spec.exclude_flag,
            findings_exit_codes=spec.findings_exit_codes,
            extra_args=spec.args,
        )
        self.spec = spec

    def _read(self, result: ToolResult) -> Extraction:
        text = result.stdout or result.stderr
        concern = self.spec.concerns[0] if self.spec.concerns else "style"
        if self.spec.output_format == "sarif":
            return parse_sarif(text, self.spec.slug, concern)
        if self.spec.output_format == "checkstyle":
            return parse_checkstyle(text, self.spec.slug, concern)
        if self.spec.output_format == "json-findings":
            return parse_json_findings(text, self.spec, concern)
        if self.spec.output_format == "json-lines":
            return parse_json_lines(text, self.spec, concern)
        raise ValueError(
            f"{self.spec.slug}: unknown output_format {self.spec.output_format!r}; "
            f"expected one of {sorted(PARSERS)}"
        )


# Declared tools. Each is a command line and a format — no parser, no
# subclass. Every entry here still needs a human to read the tool's own
# documentation once; nothing can be invented for them, and a guessed flag
# would produce a tool that runs and reports nothing.
#
# Empty until each is verified by running it, on the same rule the tiers
# follow: an entry is a promise the tool works.
DECLARED: dict[str, ToolSpec] = {
    # Verified by running each and reading real output, on the same rule
    # the tiers follow: an entry is a promise the tool works.
    "pylint": ToolSpec(
        slug="pylint", executable="pylint", output_format="json-findings",
        concerns=("style", "structure"),
        args=("--output-format=json", "--score=n"),
        exclude_flag="--ignore-paths",
        # pylint's exit status is a bitmask of message categories -- 1
        # fatal, 2 error, 4 warning, 8 refactor, 16 convention -- so any
        # value below 32 means "ran and found things". Only 32 (usage
        # error) is a real failure. Treating 16 as failure discarded every
        # finding from a run that worked perfectly.
        findings_exit_codes=tuple(range(32)),
    ),
    "mypy": ToolSpec(
        # Closes `types`, which nothing else in the pool examines.
        slug="mypy", executable="mypy", output_format="json-lines",
        concerns=("types",),
        args=("--output", "json", "--no-error-summary", "--ignore-missing-imports"),
        json_keys=("file", "line", "message"),
        exclude_flag="--exclude",
        findings_exit_codes=(0, 1, 2),
    ),
}


def declared_adapter(slug: str) -> DeclaredAdapter | None:
    spec = DECLARED.get(slug)
    return DeclaredAdapter(spec) if spec else None


def specs_by_format() -> dict[str, list[str]]:
    """Which declared tools use each parser, for the coverage report."""
    grouped: dict[str, list[str]] = {name: [] for name in sorted(PARSERS)}
    for spec in DECLARED.values():
        grouped.setdefault(spec.output_format, []).append(spec.slug)
    return {name: sorted(slugs) for name, slugs in grouped.items()}


def sarif_path_hint(root: Path) -> Path:
    """Where a tool asked to write SARIF should put it."""
    return root / ".maintainability" / "sarif"
