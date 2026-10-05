"""Three analyzers lost to the audit for reasons nobody could see.

Found from secure-code-agent's work order, where a clean repository graded C
with `structure`, `style` and `documentation` unexamined, and reproduced on
this repository's own audit.

**pylint never analysed anything.** The operator's exclude patterns are
shell-style names — `.venv/`, `*.egg-info/` — and were handed to
`--ignore-paths`, which pylint compiles as regular expressions. `*.egg-info`
is not one, so pylint exited with an argument error. That exit code is 2,
which is also pylint's "error messages issued" bit, so the run counted as
having worked and its empty output was read as JSON: the report said
"output could not be read" while stderr held the real reason. Every tool
whose exclude dialect is a regular expression gets the same translation now.

**A tool that wrote nothing failed, whatever its exit code says** — the rule
secure-code-agent recorded as its D30. The failure carries what it said.

**cohesion was never asked to run.** Its availability probe was
`cohesion --version`, a flag cohesion does not have, so argparse exited 2 and
the tool was recorded as failed; the adapter's comment said availability came
from package metadata, and it did not.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from maintainability_audit import _analysis
from maintainability_audit._config_defaults import DEFAULT_CONFIG
from maintainability_audit._generic import DECLARED, declared_adapter
from maintainability_audit._runner import Outcome, ToolResult
from maintainability_audit._tool_adapters import ADAPTERS

REGEX_DIALECTS = {"regex", "rel_regex"}


def _regex_adapters() -> list:
    adapters = [make() for make in ADAPTERS.values()] + [declared_adapter(slug) for slug in DECLARED]
    return [a for a in adapters if a is not None and getattr(a, "exclude_dialect", "") in REGEX_DIALECTS]


def _patterns(adapter, root: Path) -> list[str]:
    argv = adapter.exclusions(DEFAULT_CONFIG["paths"]["exclude_patterns"], root)
    flag = adapter.exclude_flag
    values = [argv[i + 1] for i, word in enumerate(argv) if word == flag]
    return [p for value in values for p in value.split(adapter.exclude_separator)] if not adapter.exclude_repeat else values


def test_every_regex_dialect_receives_valid_regular_expressions(tmp_path: Path) -> None:
    adapters = _regex_adapters()
    assert len(adapters) >= 2, f"too few regex-dialect adapters found to mean anything: {adapters}"
    for adapter in adapters:
        for pattern in _patterns(adapter, tmp_path):
            re.compile(pattern)  # raises on the defect: `*.egg-info` is "nothing to repeat"


@pytest.mark.parametrize(("path", "excluded"), [
    ("/repo/.venv/lib/a.py", True),
    ("/repo/static/app.min.js", True),
    ("/repo/static/app.js", False),
    ("/repo/src/venv_tools.py", False),
    ("/repo/src/app.py", False),
])
def test_a_translated_name_matches_the_paths_it_names_and_no_others(tmp_path: Path, path: str, excluded: bool) -> None:
    pylint = declared_adapter("pylint")
    patterns = _patterns(pylint, tmp_path)

    assert any(re.match(p, path) for p in patterns) is excluded


def test_a_tool_that_wrote_nothing_failed_and_says_why(tmp_path: Path, monkeypatch) -> None:
    usage = "usage: pylint [options]\npylint: error: argument --ignore-paths: bad regex\n"
    monkeypatch.setattr(_analysis, "run", lambda slug, invocation, **k: ToolResult(
        slug=slug, outcome=Outcome.RAN, stdout="", stderr=usage, exit_code=2))
    probe = SimpleNamespace(check=lambda slug, argv: SimpleNamespace(
        usable=True, version="pylint 4", outcome=Outcome.RAN, detail=""))
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")

    coverage = _analysis._attempt(tmp_path, declared_adapter("pylint"), probe, 60, _analysis.Analysis())

    assert coverage.outcome == "failed"
    assert "bad regex" in coverage.detail


@pytest.mark.skipif(shutil.which("cohesion") is None, reason="cohesion is not installed here")
def test_cohesions_availability_probe_is_a_flag_it_has() -> None:
    probe = subprocess.run(list(ADAPTERS["cohesion"]().version_argv()), capture_output=True, text=True)

    assert probe.returncode == 0, probe.stderr


def test_interrogate_receives_each_excluded_path_as_its_own_flag(tmp_path: Path) -> None:
    """One `--exclude` per path, under the root; it took one space-joined argument.

    interrogate's `--exclude` names one path per flag. The adapter joined
    every pattern into a single argument, which named no path at all, so a
    repository's excluded directories were analysed anyway — and one
    unparseable file there (a vendored Python 2 script) crashed interrogate
    before it printed a percentage (secure-code-agent's corpus, 2026-10-04).
    """
    argv = ADAPTERS["interrogate"]().exclusions(("calibration/.corpus/", "*.min.js"), tmp_path)

    assert argv.count("--exclude") >= 1
    assert argv[argv.index("--exclude") + 1] == str(tmp_path / "calibration" / ".corpus")
    assert all(" " not in value for value in argv)


@pytest.mark.skipif(shutil.which("interrogate") is None, reason="interrogate is not installed here")
def test_an_excluded_unparseable_file_no_longer_hides_the_percentage(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text('"""Documented."""\n\n\ndef f():\n    """Yes."""\n', encoding="utf-8")
    (tmp_path / "vendor_corpus").mkdir()
    (tmp_path / "vendor_corpus" / "old.py").write_text('print "python 2"\n', encoding="utf-8")
    probe = SimpleNamespace(check=lambda slug, argv: SimpleNamespace(
        usable=True, version="interrogate", outcome=Outcome.RAN, detail=""))

    coverage = _analysis._attempt(tmp_path, ADAPTERS["interrogate"](), probe, 60, _analysis.Analysis(),
                                  ("vendor_corpus/",))

    assert coverage.outcome == "ran" and coverage.measurements == 1, coverage.detail or coverage.parse_error
