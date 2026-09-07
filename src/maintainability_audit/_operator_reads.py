"""The one door for reading a file this tool was told to read.

Its own module, and not part of `config`, for a structural reason. The
user tier reads a file too, `config` loads the user tier, so a reader
living in `config` makes `_user_config -> config -> _user_config` — the
cycle the architecture test caught when D131 routed the fifth site
through it. A primitive that everything reads through cannot sit in a
module that reads through it.

`config` re-exports both names, so every existing import keeps working.
"""
from __future__ import annotations

import os
from pathlib import Path


class PathNotAllowed(ValueError):
    """A configured path escaped the repository it belongs to, or is not
    a file this tool will read.

    The boundary is not advisory. Two different failures share this type
    because a caller does the same thing with both: refuse, and name the
    path. Location is bounded by `repository_path`; *kind* is checked
    here, and conflating them is what let an in-tree FIFO hang every
    audit (D131).
    """


MAX_OPERATOR_FILE_BYTES = 8 * 1024 * 1024


def read_operator_file(path: Path) -> str:
    """Read a file the operator named, after checking it is one.

    `--config`, `--baseline` and `--sarif-input` take a path from the
    command line and read it. Most other paths go through
    `repository_path`, which bounds them to the audited tree — but these
    legitimately point outside it, so bounding is the wrong control and
    *no* control was the shipped answer (SonarCloud S8707, found
    2026-09-05: "LLMs running this code with faulty CLI arguments can
    escape file system restrictions").

    This paragraph used to say `--config` and `--baseline` were the only
    two, and that every other path was bounded. That was false when it
    was written: `--sarif-input` is the same kind of argument and read
    its name directly for two more releases. The sentence is why nobody
    looked — a count in prose standing in for a check (D130).

    So the count is no longer the control.
    `tests/test_operator_named_paths.py` classifies **every** CLI option
    by what it does with a path and fails on one it has not been told
    about, which is a thing that cannot quietly go stale.

    What is checked is what a path cannot promise on its own:

    - **It is a regular file.** `read_text` on a FIFO blocks forever and
      on `/dev/zero` consumes memory until the process dies. An agent
      driving this CLI with an attacker-influenced argument is the case
      the rule names, and "denial-of-service via crafted config files" is
      in this project's own published scope.
    - **It is not larger than `MAX_OPERATOR_FILE_BYTES`.** A regular file
      can still be enormous.

    Deliberately *not* checked: whether the path is a symlink. The
    operator named it and controls it, and a symlinked config is an
    ordinary setup. The audited tree's own default path is a different
    question and `discovered_config` already refuses a symlink there.
    """
    import stat as stat_module

    # Opened once, then checked and read **through that handle** — the
    # same discipline `_safe_write` uses for writes, and for the same
    # reason. Checking `os.stat(path)` and then calling `path.read_text()`
    # resolves the name twice, so what was measured and what is read can
    # differ: the classic time-of-check/time-of-use gap.
    #
    # `O_NONBLOCK` is what makes the check possible at all. Opening a FIFO
    # for reading otherwise blocks until a writer appears, so the process
    # would hang *before* reaching any validation — the very failure this
    # function exists to prevent.
    handle = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        info = os.fstat(handle)
        if not stat_module.S_ISREG(info.st_mode):
            raise PathNotAllowed(
                f"{path} is not a regular file. This reads configuration "
                "and baselines; a device, socket or FIFO named here would "
                "block or exhaust memory rather than parse."
            )
        if info.st_size > MAX_OPERATOR_FILE_BYTES:
            raise PathNotAllowed(
                f"{path} is {info.st_size} bytes, over the "
                f"{MAX_OPERATOR_FILE_BYTES}-byte limit for a file named on "
                "the command line."
            )
        with os.fdopen(handle, "r", encoding="utf-8", closefd=False) as opened:
            return opened.read(MAX_OPERATOR_FILE_BYTES + 1)
    finally:
        os.close(handle)
