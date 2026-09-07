"""D104: a path from the command line is still checked before it is read.

`--config` and `--baseline` are the only two path-taking entry points
that legitimately point *outside* the audited tree, so `repository_path`
— which bounds every other path here — is the wrong control for them.
The shipped answer was no control at all, which SonarCloud's
`pythonsecurity:S8707` named in words aimed squarely at this product:
*"LLMs running this code with faulty CLI arguments can escape file system
restrictions."*

The harm is not a traversal. It is a **hang**: `read_text` on a FIFO
blocks forever, and on `/dev/zero` consumes memory until the process
dies. Measured before the fix, a bare `read_text` on a FIFO had to be
killed at four seconds. "Denial-of-service via crafted config files" sits
in this project's own published in-scope list, so the tool was open to
something it invites people to report.

These assert the *refusal*, never a timeout. A test that proves a hang by
hanging cannot fail cleanly — it takes the suite down with it — so the
regression is caught by the exception type instead.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from maintainability_audit.baseline import load_baseline
from maintainability_audit.config import (
    MAX_OPERATOR_FILE_BYTES,
    ConfigUnreadable,
    PathNotAllowed,
    load_config,
    read_operator_file,
)


def test_an_operator_named_path_must_be_a_regular_file(tmp_path: Path) -> None:
    """A FIFO named as config would block the process forever."""
    fifo = tmp_path / "config.json"
    os.mkfifo(fifo)

    with pytest.raises(PathNotAllowed, match="not a regular file"):
        read_operator_file(fifo)


def test_a_device_is_refused_rather_than_read() -> None:
    """`/dev/zero` reads until memory runs out, and it is a regular-looking
    path a faulty argument can easily name."""
    with pytest.raises(PathNotAllowed, match="not a regular file"):
        read_operator_file(Path("/dev/zero"))


def test_an_enormous_file_is_refused_before_it_is_read(tmp_path: Path) -> None:
    """A regular file can still be too big to read into memory.

    Written sparse so the test does not need the disk the check refuses.
    """
    huge = tmp_path / "huge.json"
    with huge.open("wb") as handle:
        handle.truncate(MAX_OPERATOR_FILE_BYTES + 1)

    with pytest.raises(PathNotAllowed, match="over the"):
        read_operator_file(huge)


def test_an_ordinary_file_still_reads(tmp_path: Path) -> None:
    """The check must not cost the normal case."""
    ordinary = tmp_path / "config.json"
    ordinary.write_text('{"analyzers": {"run": true}}', encoding="utf-8")

    assert read_operator_file(ordinary) == '{"analyzers": {"run": true}}'


def test_the_config_door_refuses_a_fifo_instead_of_hanging(tmp_path: Path) -> None:
    """End to end through `--config`'s own loader.

    It surfaces as `ConfigUnreadable` — the door's existing refusal, which
    names the file rather than leaking what a followed symlink pointed at
    (D32). What matters here is that it *returns*.
    """
    fifo = tmp_path / "maintainability-agent.json"
    os.mkfifo(fifo)

    with pytest.raises((ConfigUnreadable, PathNotAllowed)):
        load_config(str(fifo))


def test_the_baseline_door_refuses_a_fifo_instead_of_hanging(tmp_path: Path) -> None:
    """The same check on `--baseline`, which had the same hole."""
    fifo = tmp_path / "baseline.json"
    os.mkfifo(fifo)

    with pytest.raises(PathNotAllowed, match="not a regular file"):
        load_baseline(str(fifo))


def test_a_symlinked_config_is_deliberately_still_allowed(tmp_path: Path) -> None:
    """The one check *not* added, pinned so nobody adds it by reflex.

    The operator named this path and controls it; a symlinked config is an
    ordinary setup and refusing it would break people for no gain. The
    audited tree's own default path is a different question, and
    `discovered_config` already refuses a symlink there.
    """
    real = tmp_path / "real.json"
    real.write_text('{"analyzers": {"run": false}}', encoding="utf-8")
    link = tmp_path / "link.json"
    link.symlink_to(real)

    assert read_operator_file(link) == '{"analyzers": {"run": false}}'


# ---------------------------------------------------------------------------
# D130/D131: `--sarif-input` is the third argument of this kind.
#
# The entry above closed on the claim that `--config` and `--baseline` were
# the only two path-taking arguments with no validation. `--sarif-input` is
# the same shape — repeatable, allowed outside `--root`, ingested into the
# published report — and read its name directly, so a FIFO hung, a device
# read until memory died, and a directory escaped as a traceback.
#
# The claim that hid it was written into `read_operator_file`'s own
# docstring: "every other path in this project goes through
# `repository_path`". Prose standing in for a check, for the third time in
# this release.
# ---------------------------------------------------------------------------


def test_a_directory_named_as_sarif_input_is_refused_by_name(tmp_path: Path) -> None:
    """`PathNotAllowed`, not a bare `IsADirectoryError`.

    The distinction is the test. A directory already raised *an* exception
    on the shipped tree — an uncaught `IsADirectoryError` with a traceback
    — so asserting "something was raised" would have passed against the
    defect. What is asserted is the refusal contract: the door's own error
    type, naming the file.
    """
    from maintainability_audit.sarif import read_sarif_inputs

    directory = tmp_path / "reports"
    directory.mkdir()

    with pytest.raises(PathNotAllowed, match="reports"):
        read_sarif_inputs([str(directory)])


def test_a_missing_sarif_input_is_refused_by_name(tmp_path: Path) -> None:
    """Same contract for a path that is not there at all."""
    from maintainability_audit.sarif import read_sarif_inputs

    with pytest.raises(PathNotAllowed, match="absent.sarif"):
        read_sarif_inputs([str(tmp_path / "absent.sarif")])


def test_a_fifo_named_as_sarif_input_returns_rather_than_hanging(
    tmp_path: Path,
) -> None:
    """Run in a child process, because the defect is a hang.

    A hanging test cannot fail cleanly: in-process it would stop the suite
    and the falsifier gate rather than report anything. The child gets a
    deadline, so the unfixed code fails as a timeout and the fixed code
    returns — which is the property under test, exactly as D104 said when
    it measured this on `--config`.
    """
    fifo = tmp_path / "pipe.sarif"
    os.mkfifo(fifo)

    probe = (
        "import sys;"
        "sys.path.insert(0, %r);"
        "from maintainability_audit.sarif import read_sarif_inputs;"
        "from maintainability_audit.config import PathNotAllowed;"
        "\ntry:\n"
        "    read_sarif_inputs([%r])\n"
        "except PathNotAllowed:\n"
        "    print('refused')\n"
    ) % (str(ROOT / "src"), str(fifo))

    finished = subprocess.run(  # noqa: S603
        [sys.executable, "-c", probe],
        capture_output=True, text=True, timeout=20, check=False,
    )
    assert "refused" in finished.stdout, (
        "opening the FIFO did not refuse; on the unfixed tree this call "
        f"blocks forever. stderr: {finished.stderr[-400:]}"
    )


def test_a_well_formed_sarif_input_is_still_read(tmp_path: Path) -> None:
    """The guard must not cost the feature."""
    from maintainability_audit.sarif import read_sarif_inputs

    report = tmp_path / "ok.sarif"
    report.write_text(
        '{"runs":[{"tool":{"driver":{"name":"demo"}},"results":['
        '{"ruleId":"R1","level":"error","message":{"text":"m"},'
        '"locations":[{"physicalLocation":{"artifactLocation":{"uri":"a.py"},'
        '"region":{"startLine":3}}}]}]}]}',
        encoding="utf-8",
    )

    found = read_sarif_inputs([str(report)])
    assert [(f["tool"], f["rule_id"], f["line"]) for f in found] == [
        ("demo", "R1", 3)
    ]


#: Every CLI option, sorted by what it does with a path. A new option has
#: to be added here before the suite passes, which is the structural half
#: of D131: the class stays closed because a fourth `--something-input`
#: cannot be added without answering this question.
READS_AN_OPERATOR_FILE = {"--config", "--baseline", "--sarif-input"}
WRITES_A_FILE = {
    "--output", "--html-output", "--sarif-output", "--write-baseline",
    "--comment-output", "--prompt-output", "--attestation-output",
    "--agent-instructions-output", "--hostile-prompt-output",
    "--instructions-output-dir", "--skills-dir", "--target-path",
}
NOT_AN_OPERATOR_PATH = {
    # A revspec, not a file.
    "--changed-only", "--conformance",
    # A directory, bounded by `repository_path` rather than named freely.
    "--root",
    # Names the content on stdin and is deliberately never opened, which
    # is the whole point of `--check`.
    "--check",
    # Flags, values and actions.
    "--analyzers", "--no-analyzers", "--backfill", "--backfill-interval",
    "--fail-on-gate", "--fail-on-new", "--fail-on-out-of-scope",
    "--fail-on-regression", "--force-skill", "--format", "--help",
    "--init-agent-standards", "--install-precommit-hook", "--install-skill",
    "--record-history", "--staged", "--target", "--transformation",
    "--version", "--work",
}


def _options() -> set[str]:
    import argparse

    from maintainability_audit._arguments import add_arguments

    parser = argparse.ArgumentParser()
    add_arguments(parser)
    return {
        option
        for action in parser._actions
        for option in action.option_strings
        if option.startswith("--")
    }


def test_every_cli_option_is_classified_by_what_it_does_with_a_path() -> None:
    """A new option cannot be added without saying which kind it is.

    D104 closed this class on a count — "the only two" — and the count
    was wrong, because nothing enforced it. The option list is read from
    the parser rather than written here, so `--whatever-input` added
    tomorrow fails this until somebody decides whether it reads a file
    the operator named, and therefore whether it goes through the door.
    """
    classified = READS_AN_OPERATOR_FILE | WRITES_A_FILE | NOT_AN_OPERATOR_PATH
    unclassified = sorted(_options() - classified)
    assert not unclassified, (
        f"these CLI options are not classified: {unclassified}. If one "
        "reads a file the operator named, add it to READS_AN_OPERATOR_FILE "
        "and route it through `read_operator_file`; a FIFO, a device, a "
        "directory or a missing file must refuse rather than hang or "
        "traceback."
    )
    stale = sorted(classified - _options())
    assert not stale, f"these are classified and no longer exist: {stale}"


def test_no_door_reads_a_named_path_outside_the_primitive() -> None:
    """The doors themselves, checked by parsing them rather than by eye.

    `config` is where `read_operator_file` lives, so its own `os.open` is
    the implementation. Everywhere else, a call to `open`, `read_text` or
    `read_bytes` on an operator-named path is the shape that hung.
    """
    import ast

    package = ROOT / "src" / "maintainability_audit"
    offenders = []
    for name in ("sarif.py", "baseline.py"):
        tree = ast.parse((package / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            called = (
                func.attr if isinstance(func, ast.Attribute)
                else getattr(func, "id", "")
            )
            if called in {"open", "read_text", "read_bytes"}:
                offenders.append(f"{name}:{node.lineno}: {called}()")
    assert not offenders, (
        "these read a path directly instead of through "
        "`read_operator_file`, which is how a FIFO hangs and a directory "
        "escapes as a traceback:\n" + "\n".join(offenders)
    )
