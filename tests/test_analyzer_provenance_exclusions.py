"""ADR 010 provenance exclusions must reach the external analyzer pool."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

import pytest

from maintainability_audit import _analysis, _selection
from maintainability_audit._adapters import BaseAdapter, Exclusions, Extraction, exclusions_for
from maintainability_audit._analysis import analyze, ours_only
from maintainability_audit._discovery import discover
from maintainability_audit._metric_adapters import InterrogateAdapter, JscpdAdapter, expand_files
from maintainability_audit._metrics_types import Finding, Measurement
from maintainability_audit._runner import Invocation, Outcome, ToolResult
from maintainability_audit.config import load_config
from maintainability_audit.metrics import is_excluded
from maintainability_audit.report import build_report


def _repo(root: Path, files: dict[str, str]) -> Path:
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for relative, body in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return root


class _InventoryEchoAdapter(BaseAdapter):
    """Emit one measurement and finding for every path not passed as excluded."""

    def __init__(self) -> None:
        super().__init__(
            slug="inventory-echo",
            emits="both",
            executable="inventory-echo",
            concepts=("cyclomatic_complexity",),
        )
        self.invocation_excludes: list[Sequence[str]] = []

    def invocation(
        self,
        root: Path,
        paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        del paths
        self.invocation_excludes.append(excludes)
        included = (
            Path(path).relative_to(root).as_posix()
            for path in expand_files(root, excludes, suffixes=(".py",))
        )
        return Invocation(argv=(self.executable, *included))

    def _read(self, result: ToolResult) -> Extraction:
        paths = tuple(line for line in result.stdout.splitlines() if line)
        return Extraction(
            measurements=tuple(
                Measurement(
                    concept="cyclomatic_complexity",
                    unit=f"{path}::unit",
                    value=2.0,
                    tool=self.slug,
                    path=path,
                )
                for path in paths
            ),
            findings=tuple(
                Finding(
                    concept="complexity",
                    path=path,
                    line=1,
                    message="synthetic analyzer finding",
                    tool=self.slug,
                )
                for path in paths
            ),
        )


class _TreeWideNoDialectAdapter(BaseAdapter):
    """Emit a whole-tree rate through a flag that cannot encode tree locations."""

    def __init__(self) -> None:
        super().__init__(
            slug="tree-rate-none",
            emits="metric",
            executable="tree-rate-none",
            concepts=("documentation",),
            exclude_flag="--include-only",
            exclude_dialect="none",
        )

    def _read(self, result: ToolResult) -> Extraction:
        del result
        return Extraction(measurements=(Measurement(
            concept="documentation",
            unit="<tree>",
            value=75.0,
            tool=self.slug,
            path="",
        ),))


@pytest.fixture
def analyzer(monkeypatch: pytest.MonkeyPatch) -> _InventoryEchoAdapter:
    adapter = _InventoryEchoAdapter()
    _install_adapter(monkeypatch, adapter)
    return adapter


def _install_adapter(
    monkeypatch: pytest.MonkeyPatch,
    adapter: BaseAdapter,
    stdout_for: Callable[[Invocation], str] | None = None,
) -> list[Invocation]:
    invocations: list[Invocation] = []
    monkeypatch.setattr(
        _analysis,
        "resolve_pool",
        lambda _config: ([{
            "slug": adapter.slug,
            "measures": ["complexity"],
            "languages": ["python"],
        }], []),
    )
    monkeypatch.setattr(_selection, "adapter_for", lambda slug: adapter if slug == adapter.slug else None)
    monkeypatch.setattr(_selection, "declared_adapter", lambda _slug: None)
    monkeypatch.setattr(
        _analysis.Probe,
        "check",
        lambda _self, slug, _argv: ToolResult(
            slug=slug, outcome=Outcome.RAN, version="inventory-echo 1.0"
        ),
    )
    monkeypatch.setattr(
        _analysis,
        "run",
        lambda slug, invocation, *, timeout_seconds: _fake_result(
            slug, invocation, timeout_seconds, invocations, stdout_for
        ),
    )
    return invocations


def _fake_result(
    slug: str,
    invocation: Invocation,
    timeout_seconds: int,
    invocations: list[Invocation],
    stdout_for: Callable[[Invocation], str] | None,
) -> ToolResult:
    invocations.append(invocation)
    stdout = stdout_for(invocation) if stdout_for else "\n".join(invocation.argv[1:])
    return ToolResult(
        slug=slug,
        outcome=Outcome.RAN,
        stdout=stdout,
        duration_seconds=float(timeout_seconds > 0),
    )


def _assert_only_first_party_was_emitted(root: Path, config: dict) -> None:
    analysis = analyze(root, config)
    measurement_paths = {item.path for item in analysis.measurements}
    finding_paths = {item.path for item in analysis.findings}

    assert "src/owned.py" in measurement_paths
    assert "src/owned.py" in finding_paths
    assert measurement_paths == {"src/owned.py"}
    assert finding_paths == {"src/owned.py"}


def test_generated_files_are_counted_but_not_sent_to_analyzers(
    tmp_path: Path, analyzer: _InventoryEchoAdapter
) -> None:
    root = _repo(tmp_path / "generated", {
        "src/owned.py": "def owned():\n    return 1\n",
        "artifacts/output.py": "# @generated\ndef generated():\n    return 2\n",
    })
    config = load_config(None)

    _assert_only_first_party_was_emitted(root, config)
    report = build_report(root, config, run_analyzers=True)

    assert report["summary"]["generated_files"] == 1
    assert report["summary"]["vendored_files"] == 0


def test_vendored_files_are_counted_but_not_sent_to_analyzers(
    tmp_path: Path, analyzer: _InventoryEchoAdapter
) -> None:
    root = _repo(tmp_path / "repository", {
        ".gitmodules": (
            '[submodule "deps/lib"]\n'
            "\tpath = deps/lib\n"
            "\turl = https://example.invalid/lib\n"
        ),
        "src/owned.py": "def owned():\n    return 1\n",
        "deps/lib/dependency.py": "def dependency():\n    return 2\n",
    })
    config = load_config(None)

    _assert_only_first_party_was_emitted(root, config)
    report = build_report(root, config, run_analyzers=True)

    assert report["summary"]["generated_files"] == 0
    assert report["summary"]["vendored_files"] == 1


def test_inventory_paths_are_part_of_adapter_invocation_excludes(
    tmp_path: Path, analyzer: _InventoryEchoAdapter
) -> None:
    root = _repo(tmp_path / "mixed", {
        ".gitmodules": (
            '[submodule "deps/lib"]\n'
            "\tpath = deps/lib\n"
            "\turl = https://example.invalid/lib\n"
        ),
        "src/owned.py": "def owned():\n    return 1\n",
        "artifacts/output.py": "# @generated\ndef generated():\n    return 2\n",
        "deps/lib/dependency.py": "def dependency():\n    return 3\n",
    })

    analyze(root, load_config(None))

    assert analyzer.invocation_excludes
    excludes = analyzer.invocation_excludes[-1]
    covers = getattr(excludes, "covers", lambda path: is_excluded(path, list(excludes)))
    assert covers("artifacts/output.py"), (
        "the generated path discovered from its banner was not passed to the adapter"
    )
    assert covers("deps/lib/dependency.py"), (
        "the vendored path discovered from .gitmodules was not passed to the adapter"
    )


def _same_named_directory_tree(root: Path) -> Path:
    return _repo(root, {
        "package.json": '{"scripts":{"build":"rm -rf lib && build"}}',
        ".gitmodules": (
            '[submodule "ggml"]\n'
            "\tpath = ggml\n"
            "\turl = https://example.invalid/ggml\n"
        ),
        "src/app.py": "def app():\n    return 1\n",
        "src/lib/owned.py": "def owned():\n    return 2\n",
        "lib/generated.py": "def generated():\n    return 3\n",
        "src/pb2.py": "# @generated by protoc\ndef message():\n    return 4\n",
        "ggml/core.py": "def dependency():\n    return 5\n",
        "node_modules/package.py": "def dependency():\n    return 6\n",
        ".venv/package.py": "def dependency():\n    return 7\n",
    })


def test_analyzers_keep_a_first_party_directory_with_a_generated_name_collision(
    tmp_path: Path, analyzer: _InventoryEchoAdapter
) -> None:
    root = _same_named_directory_tree(tmp_path / "collision")
    config = load_config(None)

    analysis = analyze(root, config)
    measurement_paths = {item.path for item in analysis.measurements}
    finding_paths = {item.path for item in analysis.findings}
    expected = {"src/app.py", "src/lib/owned.py"}

    assert measurement_paths == expected
    assert finding_paths == expected

    summary = build_report(root, config, run_analyzers=True)["summary"]
    assert summary["generated_files"] == 2
    assert summary["vendored_files"] == 1


def test_expand_files_treats_inventory_directories_as_root_relative_prefixes(
    tmp_path: Path,
) -> None:
    root = _same_named_directory_tree(tmp_path / "collision")
    config = load_config(None)
    inventory = discover(root, config)
    inventory_excludes = inventory.exclusions()

    assert any(entry.rstrip("/") == "lib" for entry in inventory_excludes), (
        "the premise requires a classified root lib directory"
    )
    exclusions = exclusions_for(config, inventory)
    assert exclusions.covers("lib/generated.py")
    assert not exclusions.covers("src/lib/owned.py"), (
        "an inventory directory is a repository-relative prefix, not a name list"
    )
    named = {
        Path(path).relative_to(root).as_posix()
        for path in expand_files(root, exclusions)
    }

    assert {"src/app.py", "src/lib/owned.py"} <= named
    assert "lib/generated.py" not in named
    assert "src/pb2.py" not in named
    assert "ggml/core.py" not in named
    assert "node_modules/package.py" not in named
    assert ".venv/package.py" not in named


def test_a_nested_generated_prefix_does_not_exclude_another_lib_directory(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path / "nested", {
        "packages/icons/package.json": (
            '{"scripts":{"build:lib:clean":"rimraf lib && build --flat"}}'
        ),
        "packages/icons/lib/Icon.mjs": "export default 1;\n",
        "src/lib/owned.py": "def owned():\n    return 1\n",
    })
    config = load_config(None)
    inventory = discover(root, config)

    named = {
        Path(path).relative_to(root).as_posix()
        for path in expand_files(
            root,
            exclusions_for(config, inventory),
        )
    }

    assert "src/lib/owned.py" in named
    assert "packages/icons/lib/Icon.mjs" not in named


def _dialect_pieces(argv: tuple[str, ...]) -> set[str]:
    return {
        piece
        for argument in argv
        for piece in re.split(r"[,| ]+", argument)
        if piece
    }


def test_analyzer_coverage_counts_only_evidence_that_survives_provenance_filtering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path / "coverage-counts", {
        "src/owned.py": "def owned():\n    return 1\n",
        "generated.py": "# @generated\ndef generated():\n    return 2\n",
    })
    adapter = _InventoryEchoAdapter()

    def ignore_exclusions(
        root: Path,
        paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        del paths, excludes
        relative = sorted(path.relative_to(root).as_posix() for path in root.rglob("*.py"))
        return Invocation(argv=(adapter.executable, *relative))

    monkeypatch.setattr(adapter, "invocation", ignore_exclusions)
    _install_adapter(monkeypatch, adapter)

    analysis = analyze(root, load_config(None))
    coverage = [row for row in analysis.coverage if row.tier == "analyzer"]

    assert len(coverage) == 1
    assert coverage[0].measurements == len(analysis.measurements) == 1
    assert coverage[0].findings == len(analysis.findings) == 1


def test_a_filtered_tree_wide_measurement_may_remain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _same_named_directory_tree(tmp_path / "jscpd-tree")
    adapter = JscpdAdapter()
    invocations = _install_adapter(
        monkeypatch,
        adapter,
        lambda _invocation: '{"statistics":{"total":{"percentage":12.5}}}',
    )

    analysis = analyze(root, load_config(None))

    assert invocations
    assert "lib/**" in "\n".join(invocations[0].argv)
    assert [(item.path, item.unit) for item in analysis.measurements] == [("", "<tree>")]


def test_an_unfiltered_tree_wide_measurement_is_not_kept(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _same_named_directory_tree(tmp_path / "interrogate-tree")
    adapter = InterrogateAdapter()
    config = load_config(None)
    config_patterns = tuple(config["paths"]["exclude_patterns"])
    monkeypatch.setattr(
        _analysis,
        "exclusions_for",
        lambda _config, _inventory: Exclusions(config_patterns),
    )
    invocations = _install_adapter(
        monkeypatch,
        adapter,
        lambda _invocation: "RESULT: FAILED (minimum: 80.0%, actual: 63.3%)",
    )

    analysis = analyze(root, config)

    assert invocations
    assert "lib" not in _dialect_pieces(invocations[0].argv), (
        "the premise requires interrogate not to receive the inventory tree"
    )
    assert analysis.measurements == [], (
        "a repository-wide rate over unfiltered generated/vendored code was retained"
    )


def test_told_about_trees_depends_on_this_adapters_invocation_dialect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Possessing inventory trees is not the same as delivering them to this tool."""
    root = _same_named_directory_tree(tmp_path / "no-dialect-tree")
    adapter = _TreeWideNoDialectAdapter()
    invocations = _install_adapter(monkeypatch, adapter, lambda _invocation: "75.0")

    analysis = analyze(root, load_config(None))

    assert invocations
    pieces = _dialect_pieces(invocations[0].argv)
    assert "lib" not in pieces and "ggml" not in pieces and "src/pb2.py" not in pieces
    assert analysis.measurements == [], (
        "dialect=none cannot keep a tree-wide rate merely because Exclusions.trees is nonempty"
    )


def test_ours_only_remains_path_exact_for_absolute_and_relative_paths(tmp_path: Path) -> None:
    root = _same_named_directory_tree(tmp_path / "exact-filter")
    inventory = discover(root, load_config(None))
    measurements = [
        Measurement(
            "cyclomatic_complexity", "owned-abs", 1, "fake",
            str(root / "src/lib/owned.py"),
        ),
        Measurement(
            "cyclomatic_complexity", "owned-rel", 1, "fake", "src/lib/owned.py",
        ),
        Measurement(
            "cyclomatic_complexity", "foreign-abs", 9, "fake",
            str(root / "lib/generated.py"),
        ),
        Measurement(
            "cyclomatic_complexity", "foreign-rel", 9, "fake", "lib/generated.py",
        ),
    ]

    kept = ours_only(measurements, root, inventory)

    assert [item.unit for item in kept] == ["owned-abs", "owned-rel"]
