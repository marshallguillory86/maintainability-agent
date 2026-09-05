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
from pathlib import Path

import pytest

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
