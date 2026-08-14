"""Adapters for tools that report only what breached their threshold.

Split out when ``_adapters`` reached 766 lines against this project's own
500-line limit — found by running the audit on itself with its own
configuration, which had never actually happened before.

The division is the one the whole design turns on. A verdict emitter reports only units failing *its own* configured
threshold, so its output encodes that threshold and can never become a
rate — measured on eslint: 1 finding at complexity 5, 0 at 15, on
identical code.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from pathlib import Path

from ._adapters import BaseAdapter, Extraction, _npx
from ._metrics_types import Finding
from ._runner import Invocation, ToolResult


class VultureAdapter(BaseAdapter):
    """Dead code, as located findings.

    A verdict emitter: it reports what it believes unused and says nothing
    about the population, so it can never supply a denominator.
    """

    def __init__(self) -> None:
        super().__init__(
            slug="vulture", emits="verdict", executable="vulture",
            concepts=("dead-code",), findings_exit_codes=(0, 3),
            extra_args=("--min-confidence", "80"), exclude_flag="--exclude",
        )

    def _read(self, result: ToolResult) -> Extraction:
        findings = []
        for line in result.stdout.splitlines():
            # path:line: unused function 'name' (90% confidence)
            parts = line.split(":", 2)
            if len(parts) < 3 or not parts[1].isdigit():
                continue
            findings.append(Finding(
                concept="dead-code", path=parts[0], line=int(parts[1]),
                message=parts[2].strip(), tool=self.slug,
            ))
        return Extraction(findings=tuple(findings))



class RuffAdapter(BaseAdapter):
    """~800 lint rules, as located findings.

    A verdict emitter, so it contributes findings and never a rate — but
    the findings are most of why anyone would run it. The goal is improving
    code, not only scoring it, and "unused import at line 12" is directly
    actionable in a way no aggregate is.

    A project's own rule selection therefore shapes its *findings*, which is
    correct: that is their policy about their code. It cannot shape their
    *score*, which is also correct: two repositories must be comparable
    regardless of how each configured its linter (P2).
    """

    def __init__(self) -> None:
        super().__init__(
            slug="ruff", emits="verdict", executable="ruff",
            concepts=("style", "complexity", "dead-code"),
            findings_exit_codes=(0, 1), exclude_flag="--exclude",
            extra_args=("check", "--output-format", "json", "--no-cache"),
        )

    def _read(self, result: ToolResult) -> Extraction:
        payload = json.loads(result.stdout or "[]")
        if not isinstance(payload, list):
            raise ValueError(f"expected a JSON array of diagnostics, got {type(payload).__name__}")
        findings = tuple(
            Finding(
                concept=_ruff_concept(item.get("code") or ""),
                path=item.get("filename", ""),
                line=(item.get("location") or {}).get("row"),
                message=item.get("message", ""),
                tool=self.slug,
                rule=item.get("code"),
            )
            for item in payload
        )
        return Extraction(findings=findings)


# Ruff rule prefixes mapped onto this project's concern vocabulary, so a
# finding lands under the concern a user asked about. Anything unmapped is
# style, which is the honest default for a linter rule nobody classified.
_RUFF_CONCEPTS = (("C90", "complexity"), ("F401", "dead-code"), ("F841", "dead-code"),
                  ("ERA", "dead-code"), ("D", "documentation"))


def _ruff_concept(code: str) -> str:
    for prefix, concern in _RUFF_CONCEPTS:
        if code.startswith(prefix):
            return concern
    return "style"



class PydocstyleAdapter(BaseAdapter):
    """Docstring convention violations, as located findings.

    Complements interrogate rather than repeating it: interrogate measures
    how *much* is documented, this reports where the documentation
    breaches convention. Coverage and conformance are different questions.
    """

    def __init__(self) -> None:
        super().__init__(
            slug="pydocstyle", emits="verdict", executable="pydocstyle",
            concepts=("documentation", "style"), findings_exit_codes=(0, 1),
            exclude_flag="--match-dir", exclude_separator="|",
        )

    def _read(self, result: ToolResult) -> Extraction:
        # Two lines per finding: "path:line in scope `name`:" then an
        # indented "Dxxx: message". Parsed as a pair rather than by regex
        # over the whole text, so a message containing a colon cannot
        # shift the location.
        findings = []
        lines = (result.stdout or result.stderr).splitlines()
        for index, line in enumerate(lines):
            if ":" not in line or line.startswith(" ") or index + 1 >= len(lines):
                continue
            head, _, _ = line.partition(" in ")
            path, _, number = head.rpartition(":")
            if not number.strip().isdigit():
                continue
            detail = lines[index + 1].strip()
            code, _, message = detail.partition(":")
            findings.append(Finding(
                concept="documentation", path=path, line=int(number),
                message=message.strip() or detail, tool=self.slug, rule=code.strip(),
            ))
        return Extraction(findings=tuple(findings))



class EslintAdapter(BaseAdapter):
    """JavaScript and TypeScript lint findings.

    A verdict emitter, and one that cannot run at all without a project
    configuration: eslint flat config is mandatory from v9, and invoked
    in a tree without one it exits having done nothing. That is reported
    as unavailable-no-config rather than as a clean result, which is the
    honest answer and the one that tells the user what to do.

    Running under the project's own config is deliberate. Their rule
    selection shapes their findings — that is their policy about their
    code — and cannot shape their score, because a verdict emitter
    contributes no rate.
    """

    _CONFIGS = (
        "eslint.config.js", "eslint.config.mjs", "eslint.config.cjs",
        "eslint.config.ts", ".eslintrc.json", ".eslintrc.js", ".eslintrc.yml",
    )
    _CONCEPTS = (("complexity", "complexity"), ("max-depth", "complexity"),
                 ("max-params", "structure"), ("max-lines", "structure"),
                 ("no-unused-vars", "dead-code"))

    def __init__(self) -> None:
        super().__init__(
            slug="eslint", emits="verdict", executable="eslint",
            concepts=("style", "complexity", "structure", "dead-code"),
            findings_exit_codes=(0, 1), exclude_flag="--ignore-pattern",
        )

    def version_argv(self) -> tuple[str, ...]:
        return _npx("eslint", "--version")

    def has_config(self, root: Path) -> bool:
        return any((root / name).exists() for name in self._CONFIGS)

    def invocation(
        self, root: Path, paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        ignore: tuple[str, ...] = ()
        for pattern in excludes:
            ignore += ("--ignore-pattern", f"{pattern.rstrip('/')}/**")
        targets = tuple(paths) if paths else (str(root),)
        return Invocation(
            argv=(*_npx("eslint"), *targets, "--format", "json", *ignore),
            findings_exit_codes=self.findings_exit_codes,
        )

    def _read(self, result: ToolResult) -> Extraction:
        payload = json.loads(result.stdout or "[]")
        if not isinstance(payload, list):
            raise ValueError(f"expected a JSON array of results, got {type(payload).__name__}")
        findings = tuple(
            Finding(
                concept=self._concept(message.get("ruleId") or ""),
                path=entry.get("filePath", ""),
                line=message.get("line"),
                message=message.get("message", ""),
                tool=self.slug,
                rule=message.get("ruleId"),
            )
            for entry in payload
            for message in entry.get("messages", [])
        )
        return Extraction(findings=findings)

    def _concept(self, rule: str) -> str:
        for prefix, concept in self._CONCEPTS:
            if rule.startswith(prefix):
                return concept
        return "style"
