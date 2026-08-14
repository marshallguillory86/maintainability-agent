"""Adapters for tools that measure every unit.

Split out when ``_adapters`` reached 766 lines against this project's own
500-line limit — found by running the audit on itself with its own
configuration, which had never actually happened before.

The division is the one the whole design turns on. A metric emitter reports a value for *every* unit, threshold-free, so it
can supply the denominators a verdict emitter never can.
"""

from __future__ import annotations

import csv
import io
import json
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path

from ._adapters import BaseAdapter, Extraction, _npx
from ._metrics_types import Finding, Measurement
from ._runner import Invocation, ToolResult


def _rows(text: str) -> list[list[str]]:
    return [row for row in csv.reader(io.StringIO(text)) if row]


SOURCE_SUFFIXES = (".py", ".js", ".mjs", ".cjs", ".ts", ".java", ".c", ".cpp",
                   ".h", ".go", ".rb", ".php")
# A tool asked about thousands of files still has to fit on a command line.
# Beyond this the list is capped -- and the cap is a stated limit rather
# than a silent truncation, because a shortened file list is a shortened
# audit.
MAX_EXPANDED_FILES = 400


def expand_files(
    root: Path, excludes: Sequence[str], suffixes: Sequence[str] = SOURCE_SUFFIXES
) -> tuple[str, ...]:
    """Explicit file paths, honouring exclusions without a tool flag.

    Some analyzers have no `--exclude` at all. Handing them a directory
    means they walk `.venv` and `node_modules` and report vendored code as
    the user's, so the exclusion is applied here by choosing what to name.
    """
    # Two inputs, two matchers. Config patterns are names, matched
    # against any component; inventory paths are locations, matched as
    # bounded prefixes by `Exclusions.covers`. Running both through one
    # `part in skip` loop is what made `lib` mean every directory called
    # lib and quietly dropped first-party `src/lib/owned.py`.
    skip = tuple(e.rstrip("/") for e in excludes)
    covers = getattr(excludes, "covers", lambda _relative: False)
    return tuple(
        str(path)
        for path in sorted(root.rglob("*"))
        if path.suffix in suffixes
        and path.is_file()
        and not any(part in skip for part in path.parts)
        and not covers(path.relative_to(root).as_posix())
    )[:MAX_EXPANDED_FILES]





class LizardAdapter(BaseAdapter):
    """Cyclomatic complexity, length and parameter count, for every function.

    The workhorse: one binary covering C, C++, C#, Java, Fortran, Go, Rust,
    Kotlin, Swift, PHP, Ruby, Scala, JS and TS with no per-language setup, and
    the same four metrics everywhere. Threshold-free, so it supplies the
    denominators verdict emitters cannot.
    """

    def __init__(self) -> None:
        super().__init__(
            slug="lizard", emits="metric", executable="lizard",
            concepts=("cyclomatic_complexity", "declaration_lines", "parameters"),
            # `--exclude` is fnmatch over the full pathname, not a regex: a
            # `^lib(/|$)` pattern matches no filename at all, so the tree
            # was never excluded and only `ours_only` hid it.
            extra_args=("--csv",), exclude_flag="--exclude",
            exclude_dialect="fnmatch",
        )

    def _read(self, result: ToolResult) -> Extraction:
        measurements: list[Measurement] = []
        for row in _rows(result.stdout):
            # nloc,ccn,token,param,length,location,file,name,args,start,end
            if len(row) < 8:
                continue
            path, name = row[6], row[7]
            unit = f"{path}::{name}"
            # `cyclomatic_complexity`, not `complexity`: complexipy
            # measures *cognitive* complexity, and averaging a branch count
            # with a nesting-weighted score produces a number about
            # neither. Emitted under one family name they looked
            # corroborated on 812 units with 107% disagreement, which is
            # the data saying the model is wrong.
            # `nloc`, not `metrics`: radon and multimetric report a
            # maintainability *index* per file under that name, and pooling
            # a per-function line count with a per-file index repeats the
            # error one level down. A concept is one measurement, not a
            # family.
            # `declaration_lines`, not `nloc`: the scoring bridge fails a
            # declaration on lines the same way `function_status` does, and
            # it looks the concept up by name. Emitting a synonym meant the
            # criterion silently never fired while a unit test that
            # fabricated the right name passed.
            #
            # And it comes from `length` (index 4), not `nloc` (index 0).
            # Renaming the concept was only half the fix: `nloc` excludes
            # blanks and comments, while `max_function_lines` thresholds a
            # declaration's line *span* — which is what the built-in
            # detector counts and what the config reads as meaning. On the
            # corpus, `length` matches the built-in count on 780 of 781
            # flask declarations; `nloc` on 162. Feeding a span threshold a
            # non-blank count made the analyzer path fire far less often
            # and produced a corpus ratio of 0.49 that described two
            # definitions of "lines" rather than the code.
            for concept, index in (
                ("cyclomatic_complexity", 1), ("declaration_lines", 4), ("parameters", 3),
            ):
                measurements.append(Measurement(
                    concept=concept, unit=unit, value=float(row[index]),
                    tool=self.slug, path=path,
                    line=int(row[9]) if len(row) > 9 and row[9].isdigit() else None,
                ))
        return Extraction(measurements=tuple(measurements))



class RadonAdapter(BaseAdapter):
    """Maintainability Index per file — the academic MI formula.

    A different concept from cyclomatic complexity and worth keeping
    separate: MI folds volume, complexity and comment ratio into one number,
    so it disagrees with raw CCN in informative ways.
    """

    def __init__(self) -> None:
        super().__init__(
            slug="radon", emits="metric", executable="radon",
            concepts=("maintainability_index",), extra_args=("mi", "-j"),
        )

    def invocation(
        self, root: Path, paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        targets = tuple(paths) if paths else (str(root),)
        # radon takes comma-separated glob *patterns*, so a bare directory
        # name has to become one or it matches nothing.
        # A classified tree is a location, so it becomes `lib/*` and the
        # exact path — never the bare token, which as a radon pattern
        # would be `lib*` and also ignore `library.py` and `src/lib`.
        trees = getattr(excludes, "trees", ())
        patterns = tuple(f"{e.rstrip('/')}*" for e in excludes)
        patterns += tuple(f"{tree}/*" for tree in trees) + tuple(trees)
        ignore = ("-i", ",".join(patterns)) if patterns else ()
        return Invocation(argv=(self.executable, "mi", "-j", *ignore, *targets))

    def _read(self, result: ToolResult) -> Extraction:
        payload = json.loads(result.stdout or "{}")
        measurements = [
            Measurement(concept="maintainability_index", unit=path,
                        value=float(entry["mi"]), tool=self.slug, path=path)
            for path, entry in payload.items()
            if isinstance(entry, dict) and "mi" in entry
        ]
        return Extraction(measurements=tuple(measurements))



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
        payload = json.loads(raw or "{}")
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



class ComplexipyAdapter(BaseAdapter):
    """Cognitive complexity per function — nesting-weighted reading cost.

    A different measurement from cyclomatic complexity, not a second
    opinion on it: cyclomatic counts branches and is blind to nesting, so
    five guard clauses and five levels of nesting score the same under it.
    Keeping both is the point — where they disagree is informative.

    Writes its JSON to a fixed filename in the working directory, so the
    invocation runs from a scratch directory to avoid dropping a file into
    the tree under audit.
    """

    def __init__(self) -> None:
        super().__init__(
            slug="complexipy", emits="metric", executable="complexipy",
            concepts=("cognitive_complexity",), findings_exit_codes=(0, 1),
        )
        self._work = Path(tempfile.mkdtemp(prefix="complexipy-"))

    def invocation(
        self, root: Path, paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        # complexipy has no exclusion flag, so the filtering is done by
        # naming files rather than handing it a directory. Without this it
        # walks .venv and attributes vendored complexity to the user.
        targets = tuple(paths) if paths else expand_files(root.resolve(), excludes)
        return Invocation(
            argv=(self.executable, *targets, "--output-format", "json", "--quiet"),
            findings_exit_codes=self.findings_exit_codes,
            cwd=self._work,
        )

    def _read(self, result: ToolResult) -> Extraction:
        report = self._work / "complexipy-results.json"
        if not report.exists():
            raise ValueError("complexipy wrote no results file")
        entries = json.loads(report.read_text(encoding="utf-8"))
        measurements = tuple(
            Measurement(
                concept="cognitive_complexity",
                unit=f"{entry['path']}::{entry['function_name']}",
                value=float(entry["complexity"]),
                tool=self.slug, path=entry["path"],
            )
            for entry in entries
            if isinstance(entry, dict) and "complexity" in entry
        )
        return Extraction(measurements=measurements)



class MultimetricAdapter(BaseAdapter):
    """Halstead, maintainability index and comment ratio, multi-language.

    Twenty-five metrics over C, C++, Java, JavaScript, Go, Ruby, PHP and
    Python. Only the ones this project has a concern for are lifted; the
    rest stay in the retained raw output where a reader can still use them.
    """

    # Each metric keeps its own concept. `maintainability_index` is the
    # one radon also reports, so these two genuinely corroborate: same
    # measurement, same unit granularity, independent implementations.
    _WANTED = (
        ("maintainability_index", "maintainability_index"),
        ("cyclomatic_complexity", "file_cyclomatic_complexity"),
        ("comment_ratio", "documentation"),
        ("halstead_difficulty", "halstead_difficulty"),
    )

    # Takes file paths, not a directory: given a directory it returns a
    # single meaningless entry for the directory itself, which parsed as
    # "ran, found nothing".

    def __init__(self) -> None:
        super().__init__(
            slug="multimetric", emits="metric", executable="multimetric",
            concepts=("maintainability_index", "file_cyclomatic_complexity",
                      "documentation", "halstead_difficulty"),
            version_flag="--help", distribution="multimetric",
        )

    def invocation(
        self, root: Path, paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        targets = tuple(paths) if paths else expand_files(root, excludes)
        return Invocation(argv=(self.executable, *targets))

    def _read(self, result: ToolResult) -> Extraction:
        payload = json.loads(result.stdout or "{}")
        measurements = []
        for path, metrics in (payload.get("files") or {}).items():
            for key, concept in self._WANTED:
                if key in metrics:
                    measurements.append(Measurement(
                        # Unit is the file, not file::metric: radon names
                        # the same file, and a per-metric suffix would keep
                        # two readings of one thing from ever meeting.
                        concept=concept, unit=path,
                        value=float(metrics[key]), tool=self.slug, path=path,
                    ))
        if not measurements:
            # A metric emitter that produced nothing examined nothing. The
            # earlier version accepted this whenever an `overall` key was
            # present, which turned "given a directory it cannot read" into
            # a clean result -- absence-as-value, one more time.
            raise ValueError(
                "multimetric returned no per-file metrics; it takes file paths "
                "rather than a directory"
            )
        return Extraction(measurements=tuple(measurements))
