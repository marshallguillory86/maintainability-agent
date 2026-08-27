"""P1: same tree, same config, same answer — and what counts as "same".

The promise nothing tested. Every other published promise had a test
keeping it; determinism had only the intention, which is the state every
other defect in this project started from.

Two things make it worth pinning now rather than assuming:

**History is an input.** A report carries `scan_history`,
`design_review_candidates` and the escalations derived from them, so two
runs over an identical tree with different histories legitimately
produce different reports. That is correct — a finding that came back
twice *is* different information — but it means "deterministic" has to
name what it is a function of, or the promise is either false or vague.

**The analysis performs no network access.** Acquiring a tool may, on
first run, and the acquired version is recorded. Analysis itself must
not, or a run is a function of somebody else's uptime.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from maintainability_audit.config import load_config
from maintainability_audit.report import build_report

ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def _repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    (root / "pkg").mkdir()
    for n in range(60):
        (root / "pkg" / f"mod{n}.py").write_text(
            f"def f{n}(x):\n    if x:\n        return {n}\n    return 0\n", encoding="utf-8")
    body = "".join(f"    if x == {i}:\n        return {i}\n" for i in range(40))
    (root / "pkg" / "hot.py").write_text(f"def tangled(x):\n{body}    return -1\n",
                                         encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "init"], check=True)
    return root


def _comparable(report: dict) -> str:
    """The report minus the fields that are *meant* to vary.

    The absolute root, worktree status, every analyzer ``seconds`` field,
    and terminal paint around version strings may vary. The uncolored
    version text and every other analyzer result must not.
    """

    def stable(value: object, field: str = "") -> object:
        if isinstance(value, dict):
            return {
                key: stable(item, key)
                for key, item in value.items()
                if key != "seconds"
            }
        if isinstance(value, list):
            return [stable(item) for item in value]
        if isinstance(value, tuple):
            return tuple(stable(item) for item in value)
        if field == "version" and isinstance(value, str):
            return ANSI_ESCAPE.sub("", value)
        return value

    stripped = {k: v for k, v in report.items() if k not in {"root", "git_status_short"}}
    return json.dumps(stable(stripped), sort_keys=True, default=str)


def test_two_runs_on_one_tree_agree(tmp_path: Path) -> None:
    """The promise, checked rather than assumed.

    Ordering is the usual way this breaks: a set iterated into a list, a
    dict built from a filesystem walk. Neither shows up in a single run.
    """
    root = _repo(tmp_path / "twice")
    config = load_config(None)

    first = build_report(root, config)
    second = build_report(root, config)

    assert _comparable(first) == _comparable(second)


def test_two_analyzer_runs_on_one_tree_agree(tmp_path: Path) -> None:
    """Pinned tool versions make analyzer output part of P1's input."""
    root = _repo(tmp_path / "twice-with-analyzers")
    config = load_config(None)

    first = build_report(root, config, run_analyzers=True)
    second = build_report(root, config, run_analyzers=True)

    assert _comparable(first) == _comparable(second)


def test_a_history_is_an_input_and_the_report_says_so(
    tmp_path: Path, monkeypatch
) -> None:
    """Determinism is over (tree, config, history) — not the tree alone.

    A finding that cleared and came back twice is genuinely different
    information from one seen for the first time, so the same tree
    *should* report differently against different histories. The promise
    must name history as an input, or it is false as written.
    """
    import sys

    from maintainability_audit._scan_history import (
        DEFAULT_HISTORY_PATH,
        ScanRecord,
        append_scan,
    )
    from maintainability_audit.cli import main

    root = _repo(tmp_path / "withhistory")
    history = root / DEFAULT_HISTORY_PATH
    first_path = tmp_path / "without-history.json"
    second_path = tmp_path / "with-history.json"
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)

    def record(commit: str, findings: tuple[str, ...]) -> ScanRecord:
        return ScanRecord(
            recorded_at=f"2026-08-{len(commit):02d}T00:00:00Z", commit=commit * 40,
            branch="main", scope="full", rubric_version="0.7.0", calibration=2.6279,
            thresholds_digest="t", analyzers=(), scored_languages=("Python",),
            estimate=4.0, fingerprints=findings)

    assert main([
        "--root", str(root), "--format", "json", "--output", str(first_path),
    ]) == 0
    without = json.loads(first_path.read_text(encoding="utf-8"))
    assert without["scan_history"] == [], (
        "the full report does not make a missing history file visible"
    )

    append_scan(history, record("a", ("x",)))
    append_scan(history, record("bb", ()))
    append_scan(history, record("ccc", ("x",)))
    assert main([
        "--root", str(root), "--format", "json", "--output", str(second_path),
    ]) == 0
    with_history = json.loads(second_path.read_text(encoding="utf-8"))

    assert with_history["scan_history"], (
        "the same tree with recorded history carries no history in its full report"
    )
    assert _comparable(without) != _comparable(with_history), (
        "two full reports over one tree ignored their different history inputs"
    )


def test_the_analysis_opens_no_sockets(tmp_path: Path) -> None:
    """"No network access during analysis" is P1's stated falsifier.

    A run that reaches the network is a function of somebody else's
    uptime, and its result cannot be reproduced from checked-in inputs —
    which would take P6 down with it.
    """
    import socket

    root = _repo(tmp_path / "offline")
    config = load_config(None)
    original = socket.socket

    class Refused(socket.socket):  # type: ignore[misc]
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("the analysis opened a socket")

    socket.socket = Refused  # type: ignore[misc, assignment]
    try:
        report = build_report(root, config)
    finally:
        socket.socket = original  # type: ignore[misc]

    assert report["summary"]["files_scanned"] >= 60


DISCLOSED_VARIABLE_FIELDS = {"root", "git_status_short", "seconds"}
ANALYZER_POOL = (
    "cohesion",
    "complexipy",
    "flake8",
    "interrogate",
    "lizard",
    "multimetric",
    "mypy",
    "pydocstyle",
    "pylint",
    "radon",
    "ruff",
    "vulture",
)


def test_the_determinism_exceptions_are_exactly_the_disclosed_ones() -> None:
    """P1's exception list and this file's stripping cannot drift apart.

    `_comparable` dropped `root`, `git_status_short` and every analyzer
    `seconds` while P1 promised "same report out". An audit ran two
    audits and found them differing by a millisecond on a `seconds`
    value: the promise was false of the JSON a consumer diffs and true
    only of this test's stripped projection.

    The exceptions are legitimate — a duration describes the run, not
    the repository — so P1 now names them, and this holds the two
    together. A field added to the strip list without reaching the
    promise fails here.
    """
    intent = (Path(__file__).resolve().parents[1] / "docs" / "product-intent.md")
    row = next(
        line for line in intent.read_text(encoding="utf-8").splitlines()
        if line.startswith("| P1 |")
    )
    for field in DISCLOSED_VARIABLE_FIELDS:
        assert f"`{field}`" in row, (
            f"P1 does not disclose that {field!r} varies between runs, and "
            "the determinism check strips it"
        )

    source = Path(__file__).read_text(encoding="utf-8")
    stripped = set(re.findall(r'key != "([a-z_]+)"', source))
    stripped |= set(re.findall(r'k not in \{"([a-z_]+)", "([a-z_]+)"\}', source)[0]) \
        if re.search(r'k not in \{"[a-z_]+", "[a-z_]+"\}', source) else set()
    undisclosed = sorted(stripped - DISCLOSED_VARIABLE_FIELDS)
    assert not undisclosed, (
        f"the determinism check silently ignores {undisclosed}, which P1 "
        "does not disclose"
    )


def test_the_history_window_is_disclosed_as_clock_relative() -> None:
    """P1 is true within a run and false across days; it must say so.

    `DEFAULT_SINCE` is a *relative* expression, resolved by git against
    the wall clock at the moment the audit runs. So an unchanged tree
    audited on two different days can report different churn, hotspot,
    coupling and ownership rates -- no input changed, and the grade
    moved. P1 promised "same tree, config, versions and history in, same
    score out" and named three excepted fields, none of which is this.

    The test above cannot catch it and neither can the runs at the top
    of this file: they audit the same tree seconds apart, which is
    exactly the interval over which a twelve-month window cannot shift.
    A promise kept green by a check narrower than the promise -- the
    fourth of that shape in this project -- so the disclosure is held to
    the constant rather than to a sentence someone remembered to write.
    """
    import ast
    import inspect

    from maintainability_audit import history as history_module
    from maintainability_audit.history import DEFAULT_SINCE, history_section

    # The *effective* window, not the constant. The first version of
    # this compared the prose to `DEFAULT_SINCE` alone, so changing
    # `history_section`'s default to "24 months ago" left the constant
    # untouched, the test green, and the disclosure describing a window
    # nothing used. An audit made exactly that change and walked past.
    effective = inspect.signature(history_section).parameters["since"].default
    assert effective == DEFAULT_SINCE, (
        f"history_section defaults to {effective!r} while the constant this "
        f"page is held to is {DEFAULT_SINCE!r}; the disclosure describes a "
        "window that is not the one being used"
    )

    # And the production call site must not override it, or the default
    # above is not what a report actually gets.
    report_source = (
        Path(inspect.getsourcefile(history_module)).parent / "report.py"
    ).read_text(encoding="utf-8")
    for call in ast.walk(ast.parse(report_source)):
        if (isinstance(call, ast.Call)
                and getattr(call.func, "id", "") == "history_section"):
            assert not any(kw.arg == "since" for kw in call.keywords), (
                "report.py passes its own history window, so the disclosed "
                "default is not the window a report is built with"
            )
            assert len(call.args) <= 3, (
                "report.py passes a fourth positional argument to "
                "history_section, which is the window"
            )

    assert "ago" in DEFAULT_SINCE, (
        f"the history window {DEFAULT_SINCE!r} no longer reads as relative "
        "to now; if it has become an absolute date, P1's disclosure below "
        "is the thing that is now wrong"
    )

    intent = (Path(__file__).resolve().parents[1] / "docs" / "product-intent.md")
    text = intent.read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith("| P1 |"))
    assert "wall clock" in row, (
        "P1's own row does not say the history window moves with the clock, "
        "so a reader diffing two reports a week apart has been promised "
        "they will match"
    )
    assert f"`{DEFAULT_SINCE}`" in text, (
        f"the window is {DEFAULT_SINCE!r} and product-intent quotes a "
        "different one, so the disclosure describes a window that is not "
        "the one being used"
    )


def _job_block(workflow: str, name: str) -> str:
    pattern = re.compile(rf"(?ms)^  {re.escape(name)}:\n(.*?)(?=^  [a-z0-9-]+:\n|\Z)")
    match = pattern.search(workflow)
    assert match, f"workflow job {name!r} is missing"
    return match.group(1)


def test_the_gating_pipeline_pins_the_analyzers_and_the_scheduled_run_detects_drift() -> None:
    """D89 closed: gating is pinned, schedule floats and fails on drift.

    P1 is a statement about two runs with the same pinned analyzer
    inputs. So the jobs that judge a pull request must install the pool
    through checked-in constraints. The old "an analyzer shipped" signal
    still matters too, but it belongs on the weekly scheduled run, where
    an unpinned install is compared against the checked-in freeze and
    fails visibly when the resolver result moves.

    This does not accept either arrangement. It fails if the gates float,
    if the scheduled drift check starts pinning, or if the page stops
    describing the split that the workflow actually implements.
    """
    workflow = (
        Path(__file__).resolve().parents[1]
        / ".github" / "workflows" / "quality-gates.yml"
    ).read_text(encoding="utf-8")
    intent = (
        Path(__file__).resolve().parents[1] / "docs" / "product-intent.md"
    ).read_text(encoding="utf-8")
    verify = _job_block(workflow, "verify")
    audit = _job_block(workflow, "audit")
    drift = _job_block(workflow, "analyzer-drift")

    for name, job in (("verify", verify), ("audit", audit)):
        assert "--constraint constraints/analyzers.txt" in job, (
            f"{name} installs the analyzer pool without the checked-in "
            "constraints file, so the PR gate floats"
        )
        for tool in ANALYZER_POOL:
            assert re.search(rf"\b{re.escape(tool)}\b", job), (
                f"{name} no longer names {tool}, so the pinned gate is "
                "not installing the full pip analyzer pool"
            )

    assert "github.event_name == 'schedule'" in drift, (
        "the unpinned analyzer drift job is no longer limited to the "
        "scheduled run"
    )
    assert "Install the analyzer pool unpinned in a throwaway venv" in drift, (
        "the scheduled job no longer says it is doing the unpinned "
        "install in a throwaway environment"
    )
    install = next(
        (block for block in drift.split("- name:")
         if "Install the analyzer pool unpinned in a throwaway venv" in block),
        None,
    )
    assert install is not None, "the scheduled unpinned install step is gone"
    assert "--constraint" not in install and "==" not in install, (
        "the scheduled drift detector pins the analyzer install, so it "
        "cannot detect movement in the floating pool"
    )
    for tool in ANALYZER_POOL:
        assert re.search(rf"\b{re.escape(tool)}\b", install), (
            f"the scheduled drift install no longer names {tool}, so it "
            "is not checking the same analyzer pool as the gates"
        )
    assert "pip freeze --all" in drift and "diff -u constraints/analyzers.txt" in drift, (
        "the scheduled run no longer fails visibly on a diff between the "
        "unpinned resolution and the checked-in constraints"
    )

    assert "`verify` and `audit` install the twelve" in intent, (
        "product-intent no longer says the PR gates are the pinned runs "
        "that certify P1"
    )
    assert "scheduled run keeps the old drift signal" in intent and "unpinned" in intent, (
        "product-intent no longer says the weekly scheduled run is the "
        "unpinned drift detector"
    )
    assert "fails visibly on a diff" in intent, (
        "product-intent no longer says how analyzer drift is surfaced"
    )
    assert (
        "`test_the_gating_pipeline_pins_the_analyzers_and_the_scheduled_run_detects_drift`"
        in intent
    ), "product-intent cites a different falsifier for the gating/schedule split"
