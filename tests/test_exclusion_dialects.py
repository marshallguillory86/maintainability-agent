"""Every adapter is told about generated and vendored trees, in its dialect.

`ours_only` drops foreign measurements from the report, which is a
backstop and not a fix: the tool still walked `.venv`-sized trees, still
spent the time, and still produced the findings we then threw away. The
exclusion has to reach the command line.

Two ways to get that wrong, and both have shipped here:

- **Not passing it at all.** `BaseAdapter.exclusions()` iterated the
  operator's patterns only, so lizard, vulture, ruff, interrogate,
  pydocstyle, pylint and mypy never heard about a classified tree.
  `Exclusions` subclasses `tuple` over the *patterns*, so `if not
  excludes` was also true for a repository with no operator excludes and
  a generated `lib/` — the exact case the inventory exists for.
- **Passing it in the wrong dialect.** An inventory entry is a location,
  not a name. `lib` handed to a regex flag matches `src/lib` and
  `library.py`; handed to a glob flag as `lib*` it does the same. The
  directory-name list is what ADR 010 rejected, and reintroducing it
  through a tool's argv is still reintroducing it.

The sweep is driven off the registry, so an adapter added later is
covered the day it is added rather than the day someone remembers.
"""
from __future__ import annotations

import re
from fnmatch import fnmatch
from pathlib import Path

import pytest

from maintainability_audit._adapters import Exclusions
from maintainability_audit._generic import DECLARED, declared_adapter
from maintainability_audit._tool_adapters import ADAPTERS, adapter_for

TREES = ("lib", "src/pb2.py")
FILE_LIST = {"pydocstyle", "complexipy", "multimetric"}
# These spell trees in their own invocation() and do not use tree_patterns().
CUSTOM_INVOCATION = {"jscpd", "radon", "eslint"}

ALL_SLUGS = sorted(set(ADAPTERS) | set(DECLARED))


def _adapter(slug: str):
    return adapter_for(slug) or declared_adapter(slug)


def _argv(slug: str, root: Path, excludes: Exclusions) -> tuple[str, ...]:
    return _adapter(slug).invocation(root, excludes=excludes).argv


def _tree(root: Path) -> Path:
    """A generated root `lib/`, first-party `src/lib/`, a banner stray."""
    (root / "lib").mkdir(parents=True)
    (root / "lib" / "bundle.py").write_text("x = 1\n", encoding="utf-8")
    (root / "src" / "lib").mkdir(parents=True)
    (root / "src" / "lib" / "owned.py").write_text("y = 2\n", encoding="utf-8")
    (root / "src" / "library.py").write_text("z = 3\n", encoding="utf-8")
    (root / "src" / "pb2.py").write_text("w = 4\n", encoding="utf-8")
    return root


def test_the_sweep_covers_every_registered_adapter() -> None:
    """The premise: a slug with no adapter would silently pass everything."""
    assert ALL_SLUGS, "no adapters were discovered"
    missing = [slug for slug in ALL_SLUGS if _adapter(slug) is None]
    assert not missing, f"registered slugs with no adapter: {missing}"


@pytest.mark.parametrize("slug", ALL_SLUGS)
def test_an_empty_operator_list_still_emits_the_inventory_trees(
    slug: str, tmp_path: Path
) -> None:
    """`Exclusions((), trees=("lib",))` is falsy as a tuple, and must not read as empty.

    A repository whose operator wrote no `exclude_patterns` is exactly
    the one relying on discovery, and `if not excludes` skipped it.
    """
    if slug in FILE_LIST:
        pytest.skip(f"{slug} names files rather than exclude flags")

    argv = _argv(slug, _tree(tmp_path / slug), Exclusions((), TREES))

    assert any("lib" in token for token in argv), (
        f"{slug} received no exclusion for a classified tree: {argv}"
    )


@pytest.mark.parametrize("slug", ALL_SLUGS)
def test_no_adapter_receives_a_bare_tree_token(slug: str, tmp_path: Path) -> None:
    """`lib` alone is a name. Every dialect needs it anchored or bounded.

    Checked by what the token would match rather than by its spelling: a
    pattern is acceptable only if it cannot also select `src/lib` or
    `library.py`.
    """
    if slug in FILE_LIST:
        pytest.skip(f"{slug} names files rather than exclude flags")

    argv = _argv(slug, _tree(tmp_path / slug), Exclusions((), TREES))
    offenders = [
        token for token in argv
        if token in {"lib", "lib*", "*lib*", "**/lib/**"}
    ]

    assert not offenders, (
        f"{slug} was handed an unanchored tree token {offenders}, which also "
        "matches src/lib and library.py"
    )


def _vulture_hits(pattern: str, absolute: str) -> bool:
    if not any(char in pattern for char in "*?["):
        pattern = f"*{pattern}*"
    return fnmatch(absolute, pattern)


def _gitignore_hits(pattern: str, relative: str) -> bool:
    rooted = pattern[1:] if pattern.startswith("/") else pattern
    stem = rooted.rstrip("*").rstrip("/")
    return relative == rooted or relative.startswith(f"{stem}/")


_ENGINE = {
    "fnmatch": lambda pats, root, rel: any(fnmatch((root / rel).as_posix(), p) for p in pats),
    "regex": lambda pats, root, rel: any(re.match(p, (root / rel).as_posix()) for p in pats),
    "rel_regex": lambda pats, _root, rel: any(re.search(p, rel) for p in pats),
    "vulture": lambda pats, root, rel: any(_vulture_hits(p, (root / rel).as_posix()) for p in pats),
    "abspath": lambda pats, root, rel: any(
        (root / rel).as_posix() == p or (root / rel).as_posix().startswith(f"{p.rstrip('/')}/")
        for p in pats
    ),
    "gitignore": lambda pats, _root, rel: any(_gitignore_hits(p, rel) for p in pats),
}


def _engine_hits(slug: str, patterns: tuple[str, ...], root: Path, relative: str) -> bool:
    """Whether this tool's real matcher would skip `relative`."""
    matcher = _ENGINE.get(_adapter(slug).exclude_dialect)
    return bool(matcher and matcher(patterns, root, relative))


@pytest.mark.parametrize(
    "slug", [s for s in ALL_SLUGS if s not in FILE_LIST | CUSTOM_INVOCATION]
)
def test_tree_patterns_match_only_the_classified_location(
    slug: str, tmp_path: Path
) -> None:
    """The oracle is the tool's matcher, not a regex we wished it used."""
    root = _tree(tmp_path / slug)
    patterns = _adapter(slug).tree_patterns(TREES, root)
    assert patterns, f"{slug} emitted no tree patterns"

    assert _engine_hits(slug, patterns, root, "lib/bundle.py"), (
        f"{slug} does not exclude the classified tree: {patterns}"
    )
    assert _engine_hits(slug, patterns, root, "src/pb2.py"), (
        f"{slug} misses the banner stray: {patterns}"
    )
    assert not _engine_hits(slug, patterns, root, "src/lib/owned.py"), (
        f"{slug} also excludes first-party src/lib: {patterns}"
    )
    assert not _engine_hits(slug, patterns, root, "src/library.py"), (
        f"{slug} also excludes library.py: {patterns}"
    )


@pytest.mark.parametrize("slug", ["complexipy", "multimetric"])
def test_expanded_targets_keep_first_party_code_under_a_shared_name(
    slug: str, tmp_path: Path
) -> None:
    """These adapters have no flag, so the exclusion is what we name."""
    argv = _argv(slug, _tree(tmp_path / slug), Exclusions((), TREES))
    named = " ".join(argv)

    assert "src/lib/owned.py" in named, f"{slug} dropped first-party code: {argv}"
    assert "src/library.py" in named, f"{slug} prefix-matched past a boundary: {argv}"
    assert "lib/bundle.py" not in named.replace("src/lib/", ""), (
        f"{slug} named a generated file: {argv}"
    )
    assert "src/pb2.py" not in named, f"{slug} named a banner-generated stray: {argv}"


@pytest.mark.parametrize("slug", ALL_SLUGS)
def test_operator_patterns_keep_their_name_semantics(slug: str, tmp_path: Path) -> None:
    """The other half must not regress: `node_modules` is still a name.

    Adapters with no exclusion flag honour it by *omission* — they are
    handed an explicit file list — so for them the evidence is that the
    excluded file never appears, not that the pattern does.
    """
    root = _tree(tmp_path / slug)
    (root / "node_modules").mkdir()
    (root / "node_modules" / "dep.py").write_text("q = 5\n", encoding="utf-8")

    argv = _argv(slug, root, Exclusions(("node_modules",), ()))

    passed_as_pattern = any("node_modules" in token for token in argv)
    honoured_by_omission = not any(token.endswith("node_modules/dep.py") for token in argv)

    assert passed_as_pattern or honoured_by_omission, (
        f"{slug} neither excluded node_modules nor omitted its files: {argv}"
    )


# --------------------------------------------------------------------
# What the coverage record says must match what survived
# --------------------------------------------------------------------


def test_coverage_counts_match_what_was_kept(tmp_path: Path) -> None:
    """`ToolCoverage.measurements` was recorded before filtering.

    A tool that walked a vendored tree reported "48 measurements" while
    six reached the report. A coverage record that overstates what it
    contributed is the same class of defect as a clean scan that never
    looked: the number describes an activity, not a result.
    """
    from maintainability_audit._analysis import analyze
    from maintainability_audit.config import load_config

    root = tmp_path / "counts"
    _tree(root)
    (root / ".gitmodules").write_text(
        '[submodule "lib"]\n\tpath = lib\n\turl = https://example.invalid\n',
        encoding="utf-8",
    )
    (root / "README.md").write_text("# r\n", encoding="utf-8")

    analysis = analyze(root, load_config(None))
    ran = [entry for entry in analysis.coverage if entry.tier != "built-in" and entry.contributed]
    if not ran:
        pytest.skip("no external analyzer is installed, so there are no counts to compare")

    reported = sum(entry.measurements for entry in analysis.coverage if entry.tier != "built-in")
    reported_findings = sum(
        entry.findings for entry in analysis.coverage if entry.tier != "built-in"
    )

    assert reported == len(analysis.measurements), (
        f"coverage claims {reported} measurements, {len(analysis.measurements)} survived"
    )
    assert reported_findings == len(analysis.findings), (
        f"coverage claims {reported_findings} findings, {len(analysis.findings)} survived"
    )


def test_a_tree_wide_rate_is_dropped_when_its_tool_could_not_be_told(tmp_path: Path) -> None:
    """`path=""` survives a path-exact filter, and must not survive blindly.

    jscpd's duplication percentage and interrogate's coverage describe
    the whole tree. If the tool was told about the generated directories
    the number is about our code and stands; if it could not be told, the
    number counts somebody else's files and there is no way to correct it
    after the fact. Dropping it is the only honest option — inventing a
    corrected rate would be worse than saying nothing.
    """
    from maintainability_audit._analysis import ours_only
    from maintainability_audit._discovery import discover
    from maintainability_audit._metrics_types import Measurement
    from maintainability_audit.config import load_config

    root = tmp_path / "rates"
    _tree(root)
    (root / ".gitmodules").write_text(
        '[submodule "lib"]\n\tpath = lib\n\turl = https://example.invalid\n',
        encoding="utf-8",
    )
    inventory = discover(root, load_config(None))
    assert inventory.not_ours(), "fixture must classify something as foreign"

    rate = Measurement("duplication", "percent", 12.0, "jscpd", "")

    told = ours_only([rate], root, inventory, told_about_trees=True)
    untold = ours_only([rate], root, inventory, told_about_trees=False)

    assert told == [rate], "a tool that was told keeps its tree-wide rate"
    assert untold == [], "a tree-wide rate from an untold tool counts foreign files"


def test_told_is_the_adapter_not_the_inventory() -> None:
    """Inventory having trees does not mean this tool received them."""
    from maintainability_audit._adapters import BaseAdapter

    excludes = Exclusions((), ("lib",))
    silent = BaseAdapter(slug="silent", exclude_flag="--x", exclude_dialect="none")
    lizard = _adapter("lizard")
    pydocstyle = _adapter("pydocstyle")

    assert silent.received_trees(excludes) is False
    assert lizard.received_trees(excludes) is True
    assert pydocstyle.received_trees(excludes) is True


# --------------------------------------------------------------------
# A pattern is only correct against the paths the tool actually sees
# --------------------------------------------------------------------
#
# Every adapter here is handed the repository root as its target, so the
# paths these tools match against are absolute. A pattern anchored at a
# repository-relative `lib` matches nothing in that world, and one that
# is merely the token `lib` matches every `lib` on the filesystem —
# including `src/lib`, which is the directory-name list again.


def _fnmatch_hits(patterns: list[str], candidate: str) -> bool:
    import fnmatch
    return any(fnmatch.fnmatch(candidate, pattern) for pattern in patterns)


def test_lizard_patterns_match_absolute_paths_by_fnmatch(tmp_path: Path) -> None:
    """lizard's `--exclude` is fnmatch over the full pathname.

    `^lib(/|$)` is a regex and matches no filename at all, so the tree
    was never excluded and only `ours_only` hid it.
    """
    root = _tree(tmp_path / "lizard")
    patterns = list(_adapter("lizard").tree_patterns(TREES, root))
    assert patterns, "lizard emitted no tree pattern"

    assert _fnmatch_hits(patterns, str(root / "lib" / "bundle.py")), (
        f"lizard does not exclude the generated tree: {patterns}"
    )
    assert _fnmatch_hits(patterns, str(root / "src" / "pb2.py")), (
        f"lizard misses the banner stray: {patterns}"
    )
    assert not _fnmatch_hits(patterns, str(root / "src" / "lib" / "owned.py")), (
        f"lizard also excludes first-party src/lib: {patterns}"
    )
    assert not _fnmatch_hits(patterns, str(root / "src" / "library.py")), (
        f"lizard also excludes library.py: {patterns}"
    )


def test_pylint_regex_matches_the_absolute_path(tmp_path: Path) -> None:
    """pylint uses Pattern.match on the normpath, usually absolute."""
    root = _tree(tmp_path / "pylint")
    patterns = _adapter("pylint").tree_patterns(TREES, root)
    assert any(re.match(p, str(root / "lib" / "bundle.py")) for p in patterns)
    assert any(re.match(p, str(root / "src" / "pb2.py")) for p in patterns)
    assert not any(re.match(p, str(root / "src" / "lib" / "owned.py")) for p in patterns)
    assert not any(re.match(p, str(root / "src" / "library.py")) for p in patterns)


def test_mypy_regex_matches_the_cwd_relative_path(tmp_path: Path) -> None:
    """mypy searches os.path.relpath(path); invocation sets cwd=root."""
    root = _tree(tmp_path / "mypy")
    adapter = _adapter("mypy")
    patterns = adapter.tree_patterns(TREES, root)
    invocation = adapter.invocation(root, excludes=Exclusions((), TREES))
    assert invocation.cwd == root
    assert any(re.search(p, "lib/bundle.py") for p in patterns)
    assert any(re.search(p, "src/pb2.py") for p in patterns)
    assert not any(re.search(p, "src/lib/owned.py") for p in patterns)
    assert not any(re.search(p, "src/library.py") for p in patterns)


def test_vulture_never_receives_a_globless_token(tmp_path: Path) -> None:
    """vulture treats a bare `lib` as a substring match — `*lib*`.

    That is the widest possible reading of a location: it takes
    `src/lib`, `library.py`, and anything else containing the letters.
    """
    root = _tree(tmp_path / "vulture")
    patterns = list(_adapter("vulture").tree_patterns(TREES, root))
    assert patterns, "vulture emitted no tree pattern"

    assert not [p for p in patterns if "/" not in p and "*" not in p], (
        f"vulture was handed a glob-less token: {patterns}"
    )
    assert _fnmatch_hits(patterns, str(root / "lib" / "bundle.py")), patterns
    assert not _fnmatch_hits(patterns, str(root / "src" / "lib" / "owned.py")), (
        f"vulture also excludes first-party src/lib: {patterns}"
    )


@pytest.mark.parametrize("slug", ["ruff", "interrogate", "vulture", "lizard"])
def test_rooted_dialects_do_not_regress_first_party_paths(
    slug: str, tmp_path: Path
) -> None:
    """No emitted token may be a prefix of a first-party path."""
    root = _tree(tmp_path / slug)
    patterns = _adapter(slug).tree_patterns(TREES, root)

    for pattern in patterns:
        stem = pattern.rstrip("*").rstrip("/")
        assert not str(root / "src" / "lib").startswith(stem) or stem == str(root), (
            f"{slug} pattern {pattern!r} covers first-party src/lib"
        )
