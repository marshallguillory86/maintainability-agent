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
import logging
import os
import re
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path

from ._adapters import BaseAdapter, Extraction
from ._metrics_types import Measurement
from ._runner import Invocation, ToolResult


def _rows(text: str) -> list[list[str]]:
    return [row for row in csv.reader(io.StringIO(text)) if row]


SOURCE_SUFFIXES = (".py", ".js", ".mjs", ".cjs", ".ts", ".java", ".c", ".cpp",
                   ".h", ".go", ".rb", ".php")
# A file list has to fit on a command line. The old fixed cap of 400 was
# arbitrary and silent -- ~20 KB against an ARG_MAX of a megabyte -- so it
# truncated ordinary trees for no OS reason and said nothing (e88b429 #5).
# The budget is a quarter of the real ARG_MAX (room left for the exe, flags
# and env); beyond it a single invocation genuinely cannot name every file,
# and `expand_files` states the truncation through the logger, not silently.
_ARG_MAX = os.sysconf("SC_ARG_MAX") if hasattr(os, "sysconf") else 262144
_ARGV_BYTE_BUDGET = max(_ARG_MAX // 4, 131072)

logger = logging.getLogger(__name__)


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
    # The same boundary the built-in scan applies (D36). These paths
    # become analyzer argv, so a symlink out of the tree does not just
    # get read — it gets handed to a child process as a target.
    from .metrics import within

    skip = tuple(e.rstrip("/") for e in excludes)
    covers = getattr(excludes, "covers", lambda _relative: False)
    resolved_root = root.resolve()
    eligible = [
        str(path)
        for path in sorted(root.rglob("*"))
        if path.suffix in suffixes
        and path.is_file()
        and within(resolved_root, path)
        and not any(part in skip for part in path.parts)
        and not covers(path.relative_to(root).as_posix())
    ]
    kept: list[str] = []
    used = 0
    for name in eligible:
        used += len(name.encode("utf-8")) + 1  # +1 for the argv separator
        if used > _ARGV_BYTE_BUDGET and kept:
            break
        kept.append(name)
    if len(kept) < len(eligible):
        # Stated, not silent: a shortened file list is a shortened audit,
        # and the reader has to know the tool saw only part of the tree.
        logger.warning(
            "file list for %s truncated to %d of %d files (%d-byte argv budget); "
            "the remaining %d were not handed to the analyzer",
            root, len(kept), len(eligible), _ARGV_BYTE_BUDGET, len(eligible) - len(kept),
        )
    return tuple(kept)





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


class CohesionAdapter(BaseAdapter):
    """Per-class cohesion percentages — a measurement, never a gate.

    The one output shape in the pool that is genuinely its own: an
    indented text tree of files, classes and per-method scores. The
    per-class `Total:` is the reading kept; per-method lines are the
    working shown, and keeping them would treble the rows while saying
    nothing a class total does not.

    A metric emitter: it reports a value for every class it sees,
    threshold-free, which is what lets it sit in the corroboration
    machinery rather than the findings list.
    """

    _FILE = re.compile(r"^File:\s+(?P<path>.+)$")
    _CLASS = re.compile(r"^\s+Class:\s+(?P<name>\S+)\s+\((?P<line>\d+):\d+\)")
    _TOTAL = re.compile(r"^\s+Total:\s+(?P<value>[\d.]+)%")

    def __init__(self) -> None:
        super().__init__(
            slug="cohesion", emits="metric", executable="cohesion",
            concepts=("cohesion",), exclude_dialect="files",
            # Its CLI takes files or a directory and has no version flag,
            # so availability is answered from package metadata, the same
            # arrangement multimetric already uses.
            distribution="cohesion",
        )

    def invocation(
        self, root: Path, paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        # Explicit files: cohesion has no exclude flag, so what it must
        # not read is excluded by never being named — the same rule as
        # complexipy and multimetric.
        targets = tuple(paths) if paths else expand_files(root, excludes, suffixes=(".py",))
        return Invocation(argv=(self.executable, "--files", *targets))

    def _read(self, result: ToolResult) -> Extraction:
        measurements: list[Measurement] = []
        path, name, line = "", "", 0
        for text in result.stdout.splitlines():
            if found := self._FILE.match(text):
                path = found.group("path")
            elif found := self._CLASS.match(text):
                name, line = found.group("name"), int(found.group("line"))
            elif (found := self._TOTAL.match(text)) and name:
                measurements.append(Measurement(
                    concept="cohesion", unit=f"{path}::{name}",
                    value=float(found.group("value")), tool=self.slug,
                    path=path, line=line,
                ))
                name = ""  # a Total without a Class above it is the file's; skip
        return Extraction(measurements=tuple(measurements))


# Re-exported so `_metric_adapters.JscpdAdapter` keeps resolving: the
# split above is about file size, and breaking two test modules and the
# adapter registry to move a class would be a cost the split does not
# need to pay.
from ._ratio_adapters import (  # noqa: E402 - re-export after the split
    InterrogateAdapter as InterrogateAdapter,
)
from ._ratio_adapters import (  # noqa: E402 - re-export after the split
    JscpdAdapter as JscpdAdapter,
)
