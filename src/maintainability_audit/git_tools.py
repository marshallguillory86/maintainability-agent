from __future__ import annotations

import os
import subprocess
from pathlib import Path


def run_git(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def changed_paths(root: Path, revspec: str) -> set[str]:
    output = run_git(["diff", "--name-only", revspec], root)
    if not output:
        return set()
    return {line.strip().replace(os.sep, "/") for line in output.splitlines() if line.strip()}
