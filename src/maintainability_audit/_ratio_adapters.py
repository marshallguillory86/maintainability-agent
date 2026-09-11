"""Analyzers that report a rate for the whole tree, not a reading per unit.

Split from `_metric_adapters` when that module sat at exactly 500 lines
— this project's own `max_file_lines` — where any added line fails the
gate. Three modules were in that state at once, which is the shape of a
limit satisfied by trimming to the boundary rather than by splitting.

The seam is one both these adapters already state in their own
docstrings. jscpd emits "a duplication *ratio* over the whole tree" and
interrogate "docstring coverage as a percentage — a rate the tool
computes itself". Everything left behind in `_metric_adapters` reports a
measurement **per declaration**, which the scorer turns into a rate
itself.

That difference matters beyond tidiness: a rate the tool computed is
taken on trust and cannot be recomputed against a different population,
so it can never be split into the production-only view the scorer keeps
for analyzability and testability. Two kinds of number, two modules.
"""
from __future__ import annotations

import json
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path

from ._adapters import BaseAdapter, Extraction, _npx
from ._metrics_types import Finding, Measurement
from ._runner import Invocation, ToolResult


def _without_format_tag(name: str) -> str:
    """`docs/api/formik.md:javascript` -> `docs/api/formik.md`.

    For a fenced code block inside Markdown, jscpd names the file and
    then the language it detected inside it. A finding carrying that
    string points at a path that does not exist, and a finding that
    cannot be opened is worse than no finding — it teaches a reader to
    stop checking.

    Only a bare trailing word is stripped: a segment containing `/`, `.`
    or nothing at all is part of the path, and `pkgs/v1.2/b.js` has to
    survive unchanged.
    """
    head, separator, tail = name.rpartition(":")
    if separator and head and tail.isalnum():
        return head
    return name


class JscpdAdapter(BaseAdapter):
    """Copy-paste detection across ~150 formats.

    Emits both: a duplication *ratio* over the whole tree, which is a rate,
    and each clone as a located finding.
    """

    def __init__(self) -> None:
        super().__init__(
            slug="jscpd", emits="both", executable="jscpd",
            concepts=("duplication",),
        )
        # jscpd writes its JSON to a file rather than stdout, so the adapter
        # picks the destination when it builds the invocation and reads it
        # back when parsing. A scratch directory rather than the scanned
        # tree: writing into the repository under audit would change what
        # the next tool sees.
        self._report_dir = Path(tempfile.mkdtemp(prefix="jscpd-"))

    def version_argv(self) -> tuple[str, ...]:
        return _npx("jscpd", "--version")

    def invocation(
        self, root: Path, paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        # Directory patterns end in "/", file and glob patterns do not, and
        # wrapping a file in `**/name/**` produces a glob that can never
        # match. The self-audit found 254 duplication findings in a
        # generated data file that was in the exclude list the whole time.
        patterns = []
        for exclude in excludes:
            if exclude.endswith("/"):
                patterns.append(f"**/{exclude.rstrip('/')}/**")
            else:
                patterns.extend((exclude, f"**/{exclude}"))
        # Root-anchored, with no `**/` prefix: a classified tree is one
        # place, not a name to hunt for.
        for tree in getattr(excludes, "trees", ()):
            patterns.extend((tree, f"{tree}/**"))
        ignore = ("--ignore", ",".join(patterns)) if patterns else ()
        return Invocation(
            argv=(*_npx("jscpd"), str(root), "--reporters", "json", "--silent",
                  *ignore, "--output", str(self._report_dir)),
        )

    def _read(self, result: ToolResult) -> Extraction:
        report = self._report_dir / "jscpd-report.json"
        raw = report.read_text(encoding="utf-8") if report.exists() else result.stdout
        if not raw.strip():
            # No report file and no stdout is "ran, produced nothing",
            # which the old `or "{}"` default read as zero duplicates --
            # absence as clean (e88b429 #13). A real clean jscpd run still
            # writes a report with a statistics block; nothing at all is a
            # parse failure, not a clean tree.
            raise ValueError(
                "jscpd produced neither a report file nor output; "
                "a run that wrote nothing is not zero duplicates"
            )
        payload = json.loads(raw)
        totals = payload.get("statistics", {}).get("total", {})
        measurements = []
        if "percentage" in totals:
            measurements.append(Measurement(
                concept="duplication", unit="<tree>",
                value=float(totals["percentage"]), tool=self.slug, path="",
            ))
        findings = tuple(
            Finding(concept="duplication",
                    path=_without_format_tag(clone.get("firstFile", {}).get("name", "")),
                    line=clone.get("firstFile", {}).get("start"),
                    message=f"{clone.get('lines', '?')} duplicated lines",
                    tool=self.slug)
            for clone in payload.get("duplicates", [])
        )
        return Extraction(measurements=tuple(measurements), findings=findings)



class InterrogateAdapter(BaseAdapter):
    """Docstring coverage as a percentage — a rate the tool computes itself."""

    def __init__(self) -> None:
        super().__init__(
            slug="interrogate", emits="metric", executable="interrogate",
            concepts=("documentation",), findings_exit_codes=(0, 1),
            exclude_flag="--exclude", exclude_separator=" ",
            exclude_dialect="abspath",
        )

    def _read(self, result: ToolResult) -> Extraction:
        # "RESULT: FAILED (minimum: 80.0%, actual: 63.3%)". The exit code is
        # the tool's own pass/fail against *its* default threshold and is
        # deliberately ignored -- the rubric owns thresholds, not the tool.
        text = result.stdout + result.stderr
        marker = "actual:"
        if marker not in text:
            raise ValueError("no coverage percentage in interrogate output")
        actual = text.split(marker, 1)[1].split("%", 1)[0].strip()
        return Extraction(measurements=(Measurement(
            concept="documentation", unit="<tree>",
            value=float(actual), tool=self.slug, path="",
        ),))
