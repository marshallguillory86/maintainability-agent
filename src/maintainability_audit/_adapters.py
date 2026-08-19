"""Turning analyzer output into measurements and findings — ADR 006, ADR 008.

An adapter knows one tool: how to ask for its version, how to invoke it, and
how to read what comes back. It knows nothing about the rubric, scores or
thresholds, for the same reason scanners may not import scoring — an adapter
that could see the rubric would eventually be tuned to it.

**Two shapes, and the difference decides what a tool may contribute.**

*Metric emitters* report a value for every unit, threshold-free: lizard gives
cyclomatic complexity for every function, radon a maintainability index for
every file. They can supply numerators **and denominators**.

*Verdict emitters* report only units that breached the tool's own configured
threshold. Measured on eslint: the same one-function file at complexity 11
yields 1 finding at threshold 5 and **0 findings at threshold 15**. At the
higher threshold nothing in the output reveals that a function exists at all,
so no denominator can be formed from it — and consuming those verdicts would
make the score a function of the repository's lint config, which falsifies
P2. So a verdict emitter contributes located findings and never a rate.

Adapters **describe** invocations; only ``_runner`` executes them. That keeps
timeout, isolation and version capture in one auditable place.
"""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from importlib import metadata
from pathlib import Path
from typing import Any, Protocol

from ._metrics_types import Finding, Measurement
from ._runner import Invocation, ToolResult


class Exclusions(tuple):  # noqa: SLOT001 - attribute is set once in __new__
    """What an analyzer must not read, in two kinds that mean two things.

    A **config pattern** is a name. The operator wrote `node_modules`, and
    it is dropped wherever it appears — at the root, or under
    `packages/ui/`.

    An **inventory path** is a location. `discover()` proved that the
    `lib` directory at the repository root is rebuilt by a build script,
    which says nothing at all about `src/lib`. Matching it by name would
    turn one piece of evidence into a directory-name list, which is the
    option ADR 010 rejected, and would silently drop first-party code
    that happens to share the name.

    Kept in one object because they travel together and are consumed
    together; kept apart inside it because collapsing them is the bug.
    Subclasses `tuple` over the config patterns, so every `for e in
    excludes` already written keeps meaning exactly what it meant, and
    only the places that need location semantics read `.trees`.
    """

    trees: tuple[str, ...]

    def __new__(cls, patterns: Sequence[str] = (), trees: Sequence[str] = ()) -> Exclusions:
        self = super().__new__(cls, tuple(patterns))
        self.trees = tuple(trees)
        return self

    def covers(self, relative: str) -> bool:
        """Whether an inventory path covers this repository-relative path.

        Prefix, bounded at a directory separator: `lib` covers `lib` and
        `lib/bundle.js` and not `library.py`.
        """
        return any(
            relative == tree or relative.startswith(f"{tree}/")
            for tree in self.trees
        )


def exclusions_for(config: dict, inventory: object) -> Exclusions:
    """The operator's patterns and the inventory's classified paths."""
    patterns = tuple((config.get("paths") or {}).get("exclude_patterns", ()))
    return Exclusions(patterns, inventory.exclusions())


def _posix(base: Path, tree: str) -> str:
    return (base / tree).as_posix()


def _format_fnmatch(base: Path, tree: str) -> tuple[str, ...]:
    path = _posix(base, tree)
    return (path, f"{path}/*")


def _format_regex(base: Path, tree: str) -> tuple[str, ...]:
    return (f"^{re.escape(_posix(base, tree))}(?:/|$)",)


def _format_rel_regex(_base: Path, tree: str) -> tuple[str, ...]:
    return (f"^{re.escape(tree)}(?:/|$)",)


def _format_vulture(base: Path, tree: str) -> tuple[str, ...]:
    path = _posix(base, tree)
    return (path,) if "." in Path(tree).name else (f"{path}/*",)


def _format_abspath(base: Path, tree: str) -> tuple[str, ...]:
    return (_posix(base, tree),)


def _format_gitignore(_base: Path, tree: str) -> tuple[str, ...]:
    return (f"/{tree}", f"/{tree}/**")


def _format_default(_base: Path, tree: str) -> tuple[str, ...]:
    return (tree, f"{tree}/**")


_TREE_FORMATTERS = {
    "fnmatch": _format_fnmatch,
    "regex": _format_regex,
    "rel_regex": _format_rel_regex,
    "vulture": _format_vulture,
    "abspath": _format_abspath,
    "gitignore": _format_gitignore,
}

# How much raw output to keep inline per tool. Enough for a language model
# to reason over the shape of a result, bounded so a report stays a
# document. The full text is written beside the report when a sidecar
# directory is supplied.
RAW_INLINE_LIMIT = 64_000


@dataclass(frozen=True)
class Extraction:
    """Everything one adapter produced from one run."""

    measurements: tuple[Measurement, ...] = ()
    findings: tuple[Finding, ...] = ()
    # Set when a tool ran successfully but its output could not be read.
    # Distinct from "ran and found nothing", which is a real result; this
    # is a gap, and reporting it as clean is the failure ADR 006 exists
    # to prevent.
    parse_error: str | None = None
    # What the tool actually said, kept whether or not the parser
    # understood it.
    #
    # Two consumers with different constraints. The scoring engine is
    # deliberately conservative: it reads only measurements, refuses
    # threshold-contaminated verdicts as rates, and maps everything onto
    # nine concerns. That is lossy by design. A language model reading the
    # report is bound by none of it, and can see what the engine
    # structurally cannot -- that forty unused-import findings cluster in
    # one module, that every complexity warning sits on one code path,
    # that a whole rule category is missing because nobody enabled it.
    #
    # Retained on parse failure especially. A parse error means *this
    # agent* could not read the output; a model usually can, and
    # discarding it would throw away the one artifact that still had
    # value.
    raw: str = ""
    truncated: bool = False


class Adapter(Protocol):
    """What every tool integration must provide."""

    slug: str
    emits: str  # "metric" | "verdict" | "both"
    concepts: tuple[str, ...]

    def version_argv(self) -> tuple[str, ...]:
        """How to ask this tool what it is. Doubles as the availability probe."""

    def invocation(self, root: Path, paths: Iterable[str] | None) -> Invocation:
        """How to run it over a tree."""

    def parse(self, result: ToolResult) -> Extraction:
        """Read its output. Never raises; unreadable output is a parse_error."""


@dataclass
class BaseAdapter:
    """Shared plumbing so an adapter is mostly its parser.

    Subclasses set the class attributes and implement ``_read``. The
    exception handling lives here so no adapter can forget it: a tool whose
    output shape changed must degrade to a stated gap, never to silence.
    """

    slug: str = ""
    emits: str = "metric"
    concepts: tuple[str, ...] = ()
    executable: str = ""
    version_flag: str = "--version"
    findings_exit_codes: tuple[int, ...] = (0,)
    extra_args: tuple[str, ...] = field(default_factory=tuple)
    # The languages THIS integration actually reads, when narrower than
    # the catalog's claim for the tool. PMD upstream reads five
    # languages; this project's adapter names only .java files, and
    # applicability plus the coverage row must state what the
    # integration does, not what the tool could (audit M on 549fcad).
    # Empty means "trust the catalog entry".
    languages: tuple[str, ...] = ()

    def version_argv(self) -> tuple[str, ...]:
        return (self.executable, self.version_flag)

    def installed_version(self) -> str | None:
        """The version from package metadata, when the CLI cannot say."""
        if not self.distribution:
            return None
        try:
            return f"{self.distribution} {metadata.version(self.distribution)}"
        except metadata.PackageNotFoundError:
            return None

    # How this tool spells "skip these". Empty means it has no exclusion
    # flag and must be filtered another way.
    exclude_flag: str = ""
    exclude_separator: str = ","
    # mypy takes `--exclude` once per pattern. A comma-joined regex is
    # one pattern that never matches any of them.
    exclude_repeat: bool = False
    # How this tool matches a *location*. Guessing one syntax for every
    # flag is what sent `^lib(/|$)` to lizard (fnmatch on the full
    # pathname) and a bare `lib` to vulture (which wraps that as
    # `*lib*`). Each dialect is the tool's documented matcher.
    #   files     — no flag; honour trees by naming files
    #   none      — flag cannot exclude; ours_only is the only backstop
    #   gitignore — `/tree` is rooted (ruff)
    #   abspath   — filesystem path (interrogate)
    #   vulture   — glob against absolute paths; glob-less becomes *pat*
    #   fnmatch   — lizard `--exclude` on the full pathname
    #   regex     — pylint `--ignore-paths`, `re.match` on the full path
    #   rel_regex — mypy `--exclude`, `re.search` on cwd-relative path
    exclude_dialect: str = "path"
    # Installed distribution name, for tools whose CLI has no version flag.
    # multimetric is one: `--version` is not an option, so it exits 2 with
    # usage text and a CLI-only probe reports a working tool as broken.
    # P1 now depends on recording which version ran, so a tool that cannot
    # say must be asked another way rather than left blank.
    distribution: str = ""

    def exclusions(self, excludes: Sequence[str], root: Path | None = None) -> tuple[str, ...]:
        """Translate the audit's exclude patterns into this tool's dialect.

        Without this, every analyzer walks `.venv`, `node_modules` and
        `build` and reports third-party code as the user's. Measured
        before it was added: vulture returned 517 dead-code findings on
        this repository and **all 517 were inside `.venv`**. A report that
        blames a user for a vendored library is worse than no report.

        Two inputs. The operator's patterns are names, passed through as
        written. The inventory's trees are locations and are translated
        into `exclude_dialect` first — `lib` in a regex flag matches
        `src/lib`, and that is the directory-name list ADR 010 rejected
        arriving through a command line.

        `if not excludes` was the second half of the same bug:
        `Exclusions` is a tuple over the *patterns*, so a repository with
        no operator excludes and a discovered `lib/` read as "nothing to
        exclude" — the exact case discovery exists for.
        """
        if not self.exclude_flag:
            return ()
        entries = tuple(excludes) + self.tree_patterns(
            getattr(excludes, "trees", ()), root
        )
        if not entries:
            return ()
        if self.exclude_repeat:
            repeated: list[str] = []
            for entry in entries:
                repeated.extend((self.exclude_flag, entry))
            return tuple(repeated)
        return (self.exclude_flag, self.exclude_separator.join(entries))

    def tree_patterns(
        self, trees: Sequence[str], root: Path | None = None
    ) -> tuple[str, ...]:
        """One classified tree, spelled for this tool's actual matcher."""
        if self.exclude_dialect in {"none", "files"} or not trees:
            return ()
        # As handed to the tool, not Path.resolve()'d: on macOS `/var`
        # becomes `/private/var` and a resolved pattern matches nothing
        # the tool is walking.
        base = Path(root) if root is not None else Path(".")
        formatter = _TREE_FORMATTERS.get(self.exclude_dialect, _format_default)
        return tuple(pattern for tree in trees for pattern in formatter(base, tree))

    def received_trees(self, excludes: Sequence[str]) -> bool:
        """Whether this adapter can keep foreign files out of its own run.

        `bool(excludes.trees)` is the inventory, not the adapter.
        """
        if self.exclude_dialect == "none":
            return False
        return bool(getattr(excludes, "trees", ()))

    def invocation(
        self, root: Path, paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        targets = tuple(paths) if paths else (str(root),)
        return Invocation(
            argv=(
                self.executable, *self.extra_args,
                *self.exclusions(excludes, root), *targets,
            ),
            findings_exit_codes=self.findings_exit_codes,
            cwd=root if self.exclude_dialect == "rel_regex" else None,
        )

    def parse(self, result: ToolResult) -> Extraction:
        if not result.usable:
            return Extraction(parse_error=result.detail or f"{self.slug} did not run")
        try:
            return self._with_raw(self._read(result), result)
        except (ValueError, KeyError, IndexError, TypeError, AttributeError,
                json.JSONDecodeError) as error:
            # Output shapes drift between tool releases, and a message-text
            # parser drifts faster. Failing to a stated gap keeps a version
            # bump from quietly turning findings into a clean result.
            return self._with_raw(
                Extraction(
                    parse_error=(
                        f"{self.slug} ran but its output could not be read "
                        f"({type(error).__name__}: {error}). Pin the tool version or "
                        "update the adapter. The raw output is retained: a reader, "
                        "human or model, can still use it."
                    )
                ),
                result,
            )

    @staticmethod
    def _with_raw(extraction: Extraction, result: ToolResult) -> Extraction:
        """Attach what the tool said, bounded but never dropped."""
        text = result.stdout or result.stderr
        return replace(
            extraction,
            raw=text[:RAW_INLINE_LIMIT],
            truncated=len(text) > RAW_INLINE_LIMIT,
        )

    def _read(self, result: ToolResult) -> Extraction:
        raise NotImplementedError


def measurements_only(extraction: Extraction, adapter: BaseAdapter) -> tuple[Measurement, ...]:
    """Measurements a verdict emitter is not allowed to contribute.

    Enforced here rather than trusted: an adapter marked ``verdict`` that
    started returning measurements would silently reintroduce
    threshold-contaminated rates, which is the defect the audit found in
    eslint and the reason the two shapes are distinguished at all.

    Lives with the base rather than the registry: it is a rule about what
    an adapter *may* do, not knowledge of which adapters exist.
    """
    if adapter.emits == "verdict":
        return ()
    return extraction.measurements

# Whether a missing Node tool may be fetched. Off unless the operator
# set `analyzers.acquire_tools`; thrown by `_analysis.analyze` from the
# configuration, so an adapter never decides it. A module switch rather
# than a parameter because the adapters build argv in a dozen places and
# threading a flag through every one of them is how one gets missed.
_ACQUIRE_TOOLS = False


def set_tool_acquisition(enabled: bool) -> None:
    global _ACQUIRE_TOOLS
    _ACQUIRE_TOOLS = bool(enabled)


def _npx(tool: str, *args: str) -> tuple[str, ...]:
    """Invoke a Node tool, using a local install when there is one.

    A globally installed binary is used directly. When the binary is
    missing, what happens is the operator's choice, not this function's:
    with `analyzers.acquire_tools` set, ``npx --yes`` fetches the package
    — a network action P1 discloses, with the fetched version recorded.
    Without it (the default), the bare tool name is returned and the
    runner's probe fails exactly as for any absent binary, so the tool
    lands in coverage as not-installed and in the environment work order
    with its install command. A fetch nobody chose is the defect; even
    bare ``npx`` without ``--yes`` resolves an uncached package from the
    registry, so the fallback emits no npx at all.

    This does not sandbox children. What a tool the user installed does
    is that tool's affair; the promise is about what this agent
    initiates.
    """
    if shutil.which(tool):
        return (tool, *args)
    if _ACQUIRE_TOOLS:
        return ("npx", "--yes", tool, *args)
    return (tool, *args)


def ours_only(
    items: list[Any], root: Path, inventory: Any, told_about_trees: bool = True
) -> list[Any]:
    """Drop measurements or findings about code the team did not write.

    Tools report paths however they like — absolute, relative, or
    relative to their own working directory — so each is reduced to a
    repository-relative posix path before it is looked up. A path that
    cannot be placed inside the tree is kept: an unrecognised location
    is not evidence of foreign code, and silently dropping it would be
    the same absence-as-value mistake in a new place.

    `told_about_trees` decides the fate of a tree-wide rate — jscpd's
    duplication percentage, interrogate's coverage — which carries an
    empty path and survives any path-exact filter. Told, the rate
    describes our code and stands. Untold, it counted somebody else's
    files and nothing after the fact can correct it, so it is dropped
    rather than adjusted: a corrected-looking number nobody computed is
    worse than no number.
    """
    not_ours = inventory.not_ours()
    if not not_ours:
        return list(items)
    return [
        item for item in items
        if _relative_path(item.path, root) not in not_ours
        and (told_about_trees or item.path != "")
    ]


def _relative_path(path: str, root: Path) -> str:
    try:
        return Path(path).resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return path.replace("\\", "/")


def apply_staleness(adapter: Any, root: Path, excludes: Any,
                    extraction: Extraction) -> tuple[dict[str, Any] | None, Extraction]:
    """ADR 012's evidence, applied: the row gets the mtimes, stale findings say so.

    ``None`` evidence means the adapter does not measure staleness —
    the question does not apply to source-read tools. When bytecode is
    older than the newest surviving source, every finding is labeled,
    because advice derived from stale compilation must not read like
    advice about the tree as it stands (P8).
    """
    from dataclasses import replace

    measures = getattr(adapter, "staleness", None)
    if measures is None:
        return None, extraction
    evidence = measures(root, excludes=excludes)
    if evidence["stale"]:
        extraction = replace(extraction, findings=tuple(
            replace(finding,
                    message=f"{finding.message} [measured against stale compilation]")
            for finding in extraction.findings
        ))
    return evidence, extraction


def ours_only_extraction(
    extraction: Extraction, root: Path, adapter: Any,
    excludes: Sequence[str], inventory: Any,
) -> Extraction:
    """The backstop, applied per tool before its contribution is counted.

    A tool is not obliged to honour the exclusions it was handed —
    `test_adapters` already records that some ignore them. Naming the
    classified trees keeps a well-behaved tool from reading the files;
    this keeps a badly-behaved one from reporting them, and keeps the
    coverage record describing what survived rather than what was seen.
    """
    if inventory is None:
        return extraction
    told = (
        adapter.received_trees(excludes)
        if hasattr(adapter, "received_trees")
        else bool(getattr(excludes, "trees", ()))
    )
    return replace(
        extraction,
        measurements=tuple(ours_only(list(extraction.measurements), root, inventory, told)),
        findings=tuple(ours_only(list(extraction.findings), root, inventory, told)),
    )
