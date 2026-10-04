"""Reading a regular file works on a platform with no `os.O_NONBLOCK`.

`open_regular_file` opens with `O_NONBLOCK` so a FIFO cannot hang the open
before the regular-file check runs. Windows has no such flag, and the module
used it unconditionally, so every read on the Windows probe died with
`module 'os' has no attribute 'O_NONBLOCK'`. Windows has no POSIX FIFO in
the tree to guard against, so where the flag does not exist the open goes
without it; the check that follows is unchanged.
"""

from __future__ import annotations

import os
from pathlib import Path

from maintainability_audit._operator_reads import open_regular_file


def test_a_regular_file_opens_where_the_flag_does_not_exist(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "config.json"
    target.write_text("{}", encoding="utf-8")
    monkeypatch.delattr(os, "O_NONBLOCK")

    handle = open_regular_file(target, "test")
    try:
        assert os.read(handle, 10) == b"{}"
    finally:
        os.close(handle)
