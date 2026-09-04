#!/usr/bin/env python3
"""Clone the candidates, keep the ones that are actually codebases, pin them.

`select_corpus.py` filters by name, which is cheap and imprecise — a
repository called `PayloadsAllTheThings` or `30-Days-Of-Python` is
plainly a collection rather than a program, but plenty of others are not
so obvious from a name. This is the real filter: clone the candidate and
look at what is inside.

A repository qualifies as a codebase when the audit finds enough
declarations in enough source files. A curriculum repo full of Markdown
with a handful of snippets will not clear it; a maintained library will
clear it comfortably. The threshold is deliberately low, because the
corpus is supposed to describe the range of real code rather than an
idealised slice of it.

Each survivor is pinned to the exact commit that was measured, so a
recalibration months from now reproduces these numbers rather than
whatever HEAD happens to be.

    python3 tools/calibration/verify_corpus.py candidates.json --cache-dir DIR
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from maintainability_audit.config import load_config  # noqa: E402
from maintainability_audit.declarations import DECLARATION_SUFFIXES  # noqa: E402
from maintainability_audit.metrics import iter_files  # noqa: E402
from maintainability_audit.source import SourceIndex  # noqa: E402

# A codebase, not a collection. Low on purpose: the corpus should span
# the real range, including small libraries.
MIN_DECLARATIONS = 100
MIN_SOURCE_FILES = 20


def clone(entry: dict, cache_dir: Path) -> Path | None:
    target = cache_dir / entry["name"]
    if (target / ".git").exists():
        return target
    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--quiet", entry["url"], str(target)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  !! clone failed {entry['full_name']}: {result.stderr.strip()[:90]}", file=sys.stderr)
        return None
    return target


def profile(path: Path) -> tuple[int, int]:
    """(source files, declarations) — how much actual code is in here."""
    config = load_config(None)
    index = SourceIndex()
    files = [p for p in iter_files(path, config) if p.suffix in DECLARATION_SUFFIXES]
    declarations = sum(len(index.declarations(p)[0]) for p in files)
    return len(files), declarations


def head_commit(path: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, check=True
    ).stdout.strip()


def _refuses_to_clobber(destination: Path, *, replace: bool) -> bool:
    """True when writing here would destroy a corpus nobody asked to replace.

    The corpus is evidence, not output. This script used to write it
    unconditionally, and `--out` protected nothing: a run whose stdout was
    redirected elsewhere still overwrote the checked-in corpus, replacing 40
    pinned repositories with whatever candidate file happened to be passed.
    A guard failing on the mismatch is what caught it, which is luck rather
    than design — the same lesson `measure.py --check` learned when it
    rewrote the evidence it was supposed to be checking against.
    """
    if not destination.exists() or replace:
        return False
    try:
        existing: object = len(json.loads(destination.read_text(encoding="utf-8"))["repos"])
    except (ValueError, KeyError):
        existing = "an unreadable number of"
    print(
        f"refusing to overwrite {destination} ({existing} pinned repositories).\n"
        "Pass --replace to recalibrate against a new corpus, or --out PATH to "
        "write somewhere else.",
        file=sys.stderr,
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates")
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--out", default=str(Path(__file__).with_name("corpus.json")))
    parser.add_argument(
        "--replace", action="store_true",
        help="Overwrite an existing corpus. Required, because the corpus is a pinned "
             "artifact and replacing it silently discards the commits every stored "
             "measurement was taken at.",
    )
    args = parser.parse_args()

    if _refuses_to_clobber(Path(args.out), replace=args.replace):
        return 2

    data = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    cache = Path(args.cache_dir)
    cache.mkdir(parents=True, exist_ok=True)

    kept, rejected = [], []
    for entry in data["candidates"]:
        path = clone(entry, cache)
        if path is None:
            continue
        files, declarations = profile(path)
        verdict = f"{entry['full_name']:<38} {files:>5} files {declarations:>6} decls"
        if files < MIN_SOURCE_FILES or declarations < MIN_DECLARATIONS:
            rejected.append({**entry, "source_files": files, "declarations": declarations})
            print(f"  skip  {verdict}  (not a codebase)", file=sys.stderr)
            continue
        kept.append(
            {
                "name": entry["name"],
                "url": entry["url"],
                "commit": head_commit(path),
                "language": entry["language"],
                "stars": entry["stars"],
                "created": entry["created"],
                "source_files": files,
                "declarations": declarations,
            }
        )
        print(f"  keep  {verdict}", file=sys.stderr)

    Path(args.out).write_text(
        json.dumps(
            {
                "description": (
                    "Reference corpus for scoring calibration. Selected mechanically by "
                    "tools/calibration/select_corpus.py and filtered by this script; pinned to exact "
                    "commits so a recalibration is reproducible."
                ),
                "selection": data["query"],
                "selection_note": (
                    "created:<2021-01-01 is load-bearing. The corpus is the human-written baseline "
                    "against which AI-assisted code is compared, and today's most-starred repositories "
                    "include projects begun well into the LLM era — using those would answer the "
                    "question before measuring it."
                ),
                "verification": {
                    "min_source_files": MIN_SOURCE_FILES,
                    "min_declarations": MIN_DECLARATIONS,
                    "rejected": [{"full_name": r["full_name"], "declarations": r["declarations"]} for r in rejected],
                },
                "repos": sorted(kept, key=lambda item: item["name"]),
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nkept {len(kept)}, rejected {len(rejected)} -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
