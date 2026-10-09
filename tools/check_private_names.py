"""Fail when a private repository's name appears in this public repository.

Reads every tracked file and every tracked path, and with `--messages REV`
every commit message in that range, against a list of names that never lives
in this tree: the `FORBIDDEN_TERMS` and `PRIVATE_NAMES` environment variables
(CI secrets, one name per line) and `~/.config/private-names`, which is
generated from the owner's private repositories.

A match is reported by file and line (line 0 for a path) or by commit, never
by the text that matched. With no names to check against it exits 2: a guard
with nothing to look for has proved nothing.

    python3 tools/check_private_names.py [--root DIR] [--messages REV]
"""

from __future__ import annotations

import argparse
import os
import pwd
import subprocess
import sys
from pathlib import Path

# The real home, not $HOME: the test suite isolates $HOME for git.
DEFAULT_FILE = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".config" / "private-names"
VARIABLES = ("FORBIDDEN_TERMS", "PRIVATE_NAMES")


def load_names(files: list[Path]) -> list[str]:
    """Every name from the variables and the files, lowercased, sorted, deduplicated."""
    lines: list[str] = []
    for name in VARIABLES:
        lines += os.environ.get(name, "").splitlines()
    for path in files:
        if path.is_file():
            lines += path.read_text(encoding="utf-8").splitlines()
    return sorted({line.strip().lower() for line in lines if line.strip() and not line.strip().startswith("#")})


def _tracked(root: Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], check=True, capture_output=True).stdout
    return [p for p in out.decode("utf-8").split("\0") if p]


def _contains(text: str, names: list[str]) -> bool:
    lowered = text.lower()
    return any(name.lower() in lowered for name in names)


def scan(root: Path, names: list[str]) -> list[tuple[str, int]]:
    """(path, line) for every match; line 0 means the path itself."""
    hits: list[tuple[str, int]] = []
    for path in _tracked(root):
        if _contains(path, names):
            hits.append((path, 0))
        try:
            text = (root / path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        hits += [(path, n) for n, line in enumerate(text.splitlines(), 1) if _contains(line, names)]
    return hits


def scan_messages(root: Path, revspec: str, names: list[str]) -> list[str]:
    """The sha of every commit in `revspec` whose message or identity names one."""
    shas = subprocess.run(["git", "-C", str(root), "rev-list", revspec],
                          check=True, capture_output=True, text=True).stdout.split()
    hits = []
    for sha in shas:
        body = subprocess.run(["git", "-C", str(root), "show", "-s", "--format=%an%n%ae%n%cn%n%ce%n%B", sha],
                              check=True, capture_output=True, text=True).stdout
        if _contains(body, names):
            hits.append(sha)
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="repository to scan")
    parser.add_argument("--messages", metavar="REV", help="also scan commit messages in this range")
    parser.add_argument("--no-default-file", action="store_true", help=f"do not read {DEFAULT_FILE}")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    names = load_names([] if args.no_default_file else [DEFAULT_FILE])
    if not names:
        print(f"no private names given ({', '.join(VARIABLES)} unset, {DEFAULT_FILE} absent); "
              "this check proved nothing", file=sys.stderr)
        return 2
    if args.messages and not subprocess.run(["git", "-C", str(root), "rev-list", "--no-merges", args.messages],
                                            check=True, capture_output=True, text=True).stdout.strip():
        print(f"no non-merge commits in {args.messages}; this check proved nothing")
        return 1
    hits = [f"{path}:{line}" for path, line in scan(root, names)]
    if args.messages:
        hits += [f"commit {sha}" for sha in scan_messages(root, args.messages, names)]
    for hit in hits:
        print(f"FAIL  {hit}  contains a private repository's name")
    if not hits:
        print(f"ok    {len(names)} private names, none in {root.name}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
