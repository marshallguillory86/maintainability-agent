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
import re
from collections.abc import Iterable, Sequence
from pathlib import Path

from ._adapters import BaseAdapter, Extraction, _npx
from ._metric_adapters import expand_files
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
            exclude_dialect="vulture",
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
            exclude_dialect="gitignore",
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



class FortitudeAdapter(BaseAdapter):
    """Fortran lint rules, as located findings.

    The analyzer tier Fortran did not have. lizard does not read Fortran,
    so before this the language had a built-in scanner and nothing else,
    while every other claimed language had an external reading beside it.
    Fortitude is the closest thing Fortran has to ruff — Rust-fast,
    `pip install`-able, 100+ rules across correctness, obsolescent
    features, modernisation, portability and style.

    A verdict emitter: it contributes findings and never a rate. The
    findings are the point — "subroutine argument 'n' missing 'intent'
    attribute" names a line and a fix, which no aggregate does.

    **It does not claim `types`.** Its correctness rules are about
    declaring things explicitly — `implicit none`, `intent`, kind
    parameters — and a reader who saw `types` in a coverage record would
    take it to mean the code was type-checked. It is not; nothing
    type-checks Fortran here. Only `C191: unreachable-statement` maps
    off `style`, to `dead-code`, because unreachable code is exactly
    that.
    """

    def __init__(self) -> None:
        super().__init__(
            slug="fortitude", emits="verdict", executable="fortitude",
            concepts=("style", "dead-code"),
            findings_exit_codes=(0, 1), exclude_flag="--exclude",
            exclude_dialect="fnmatch",
            extra_args=("check", "--output-format", "json"),
        )

    def _read(self, result: ToolResult) -> Extraction:
        payload = json.loads(result.stdout or "[]")
        if not isinstance(payload, list):
            raise ValueError(
                f"expected a JSON array of diagnostics, got {type(payload).__name__}"
            )
        findings = tuple(
            Finding(
                concept=_fortitude_concept(item.get("code") or ""),
                path=item.get("filename", ""),
                # `line`, not ruff's `row`: the two tools ship the same
                # shape with one key renamed, and reading ruff's spelling
                # here would silently drop every line number.
                line=(item.get("location") or {}).get("line"),
                message=item.get("message", ""),
                tool=self.slug,
                rule=item.get("code"),
            )
            for item in payload
        )
        return Extraction(findings=findings)


# Fortitude groups its rules by prefix: C correctness, OB obsolescent,
# MOD modernisation, PORT portability, S style, E errors, T typing, FORT
# meta. This project's concern vocabulary has no "portability" or
# "correctness", and inventing one to hold them would put a word in the
# report that no other tool can fill. They are style findings about
# Fortran, reported with their own rule code and message intact, which is
# what a reader acts on.
_FORTITUDE_CONCEPTS = (("C191", "dead-code"),)


def _fortitude_concept(code: str) -> str:
    for prefix, concern in _FORTITUDE_CONCEPTS:
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
            exclude_flag="--match-dir", exclude_separator="|", exclude_dialect="files",
        )

    def invocation(
        self, root: Path, paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        """Explicit targets, because `--match-dir` cannot say "skip this".

        It is an *include* filter over directory names: handing it `lib`
        would tell pydocstyle to look only at directories called lib,
        which is the opposite of the intent and would also match
        `src/lib`. So the classified trees are honoured by choosing what
        to name instead, the same way the no-flag adapters do.

        `--match-dir` is dropped entirely rather than kept for the
        operator's patterns: the target list already honours those, and
        an include regex sitting beside an explicit file list can only
        narrow it further in ways nobody asked for.
        """
        targets = tuple(paths) if paths else expand_files(root, excludes, suffixes=(".py",))
        return Invocation(
            argv=(self.executable, *self.extra_args, *targets),
            findings_exit_codes=self.findings_exit_codes,
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

    Running under the project's own config was deliberate: their rule
    selection shapes their findings — that is their policy about their
    code — and cannot shape their score, because a verdict emitter
    contributes no rate.

    **Decision 9 ends that.** An eslint flat config is a JavaScript
    program, so honouring it is executing the audited tree, which this
    agent does not do. The flag below takes the adapter out of every
    selection; it is not deleted, because the reasoning above is still
    correct about *findings* and the adapter becomes usable again the
    day the tool can be invoked without the tree's config. JavaScript is
    not a v1.0 language (Decision 10), so nothing in scope loses
    coverage today.
    """

    #: Honouring this tool's configuration means running code from the
    #: tree under audit. Selection refuses any adapter that says so.
    executes_audited_configuration = True

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
        # eslint's ignore patterns are gitignore syntax, where a bare
        # `lib` matches any directory of that name at any depth — the
        # name-list behaviour again. A leading slash roots it.
        for tree in getattr(excludes, "trees", ()):
            ignore += ("--ignore-pattern", f"/{tree}", "--ignore-pattern", f"/{tree}/**")
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


class Flake8Adapter(BaseAdapter):
    """flake8's default line format, kept as located findings.

    Not a DeclaredAdapter, deliberately: flake8's stock output is
    `path:row:col: CODE message`, which is none of the four standard
    formats, and JSON output requires a plugin this project will not ask
    users to install. One small parser beats a prerequisite.

    A verdict emitter like ruff, and for the same reason: its output is
    shaped by the project's own selected rules, so it contributes
    findings and can never supply a rate (P2).
    """

    _LINE = re.compile(r"^(?P<path>.+?):(?P<row>\d+):\d+:\s+(?P<code>\S+)\s+(?P<text>.*)$")
    # flake8's rule families, on ruff's precedent: C9xx is mccabe
    # complexity, F401/F841 are unused code. Everything unmapped is
    # style, the honest default for a lint rule nobody classified.
    _CONCEPTS = (("C9", "complexity"), ("F401", "dead-code"), ("F841", "dead-code"))

    def __init__(self) -> None:
        super().__init__(
            slug="flake8", emits="verdict", executable="flake8",
            # `--isolated`: flake8 documents `[flake8:local-plugins]`,
            # which names `module:Checker` entries and a `paths` list
            # pointing into the tree, and imports them. That is running
            # the audited repository's Python, which Decision 9 forbids
            # and which eslint was refused for. An audit table in the
            # test suite asserted this tool "executes nothing" — written
            # from memory, never probed (D64).
            extra_args=("--isolated",),
            concepts=("style", "complexity", "dead-code"),
            findings_exit_codes=(0, 1), exclude_flag="--exclude",
            # flake8 matches each --exclude entry by fnmatch against the
            # normalised path, the same engine lizard uses.
            exclude_dialect="fnmatch",
        )

    def _read(self, result: ToolResult) -> Extraction:
        findings = []
        for line in result.stdout.splitlines():
            match = self._LINE.match(line)
            if not match:
                continue
            code = match.group("code")
            concept = next(
                (concern for prefix, concern in self._CONCEPTS if code.startswith(prefix)),
                "style",
            )
            findings.append(Finding(
                concept=concept, path=match.group("path"), line=int(match.group("row")),
                message=match.group("text"), tool=self.slug, rule=code,
            ))
        return Extraction(findings=tuple(findings))
