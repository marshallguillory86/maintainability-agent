"""What the repository's own history says about cost of change.

Every metric elsewhere in this package is a photograph: it reads the
code as it stands today. But maintainability is defined as the effort to
*modify* a system, and effort is paid per change — so a 600-line file
nobody has touched in three years and a 600-line file edited weekly are
scored identically by a photograph, when only one of them is costing
anybody anything.

Churn is the missing multiplier. Three signals come out of ``git log``,
no LLM and no extra clone required:

- **churn** — commits touching a file, and lines added and removed.
- **hotspots** — churn multiplied by the complexity already measured.
  Complex code nobody edits is free; complex code edited constantly is
  where defects concentrate. This product is a better-replicated defect
  predictor than complexity alone.
- **change coupling** — files that keep changing in the same commit
  without being structurally related. That is the shape of a boundary
  drawn in the wrong place, and no static metric in this package can
  see it.

**These are reported, not scored.** Adding them to the score would move
every grade the tool has ever issued, and they have not been validated
against an outcome yet — which is the same standard the near-duplicate
signal was held to after it failed one.

A shallow clone has no history to read. That is reported as "unknown",
never as zero, because a file with no recorded commits and a file that
genuinely never changes are opposite findings.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any

from .git_tools import run_git

# Commits touching more than this are migrations, reformats, licence
# header sweeps and dependency bumps. They co-change hundreds of
# unrelated files and would swamp the coupling counts with noise.
MAX_FILES_PER_COMMIT = 30

# A pair needs to co-change this often before the pattern is worth
# reporting. Two files that changed together twice is a coincidence.
MIN_COUPLING_SUPPORT = 5

# ...and it has to be most of what one of them does. A file that changes
# with everything (a router, a barrel export) is not coupled to any one
# of them in particular.
MIN_COUPLING_CONFIDENCE = 0.5

# Default window. Long enough to see a pattern, short enough that a
# rewrite three years ago does not still dominate.
DEFAULT_SINCE = "12 months ago"


@dataclass
class FileChurn:
    """How much a single file has actually been worked on."""

    path: str
    commits: int = 0
    added: int = 0
    removed: int = 0
    authors: set[str] = field(default_factory=set)

    @property
    def churn(self) -> int:
        return self.added + self.removed


def has_history(root: Path) -> bool:
    """False for a shallow clone or a directory that is not a repo.

    Distinguishes "no history available" from "no changes", which are
    opposite findings that a zero would conflate.
    """
    if not run_git(["rev-parse", "--git-dir"], root):
        return False
    return run_git(["rev-parse", "--is-shallow-repository"], root) != "true"


def _normalize(path: str) -> str:
    return path.strip().replace(os.sep, "/")


# One character class, no adjacent variable-length pieces: linear scan.
# The "old => new" split happens in plain string code, not the pattern.
_BRACED_SEGMENT = re.compile(r"\{([^{}]*)\}")


def _resolve_segment(match: re.Match[str]) -> str:
    inner = match.group(1)
    if "=>" not in inner:
        return match.group(0)  # literal braces in a filename; keep them
    _, _, new = inner.partition("=>")
    return new.strip()


def _rename_target(path: str) -> str:
    """The post-rename path, from git's numstat rename notations.

    Git writes ``old => new`` and the braced ``src/{old => new}/leaf`` —
    with possibly *several* braced segments in one path, and possibly an
    empty new side (``src/{old => }/leaf``, a directory flattening).
    Treating any of these as a literal filename would invent files that
    never existed. Every braced segment is resolved, and the doubled
    slash an empty segment leaves behind is collapsed.

    This maps the *notation* to the new path. It does not join a file's
    pre-rename history to its post-rename history — commits from before
    the rename still accrue to the old path (that would need
    ``--follow``, which is per-file and expensive). Churn for a
    recently-renamed file is therefore undercounted, not misattributed.
    """
    if "=>" not in path:
        return _normalize(path)
    if "{" in path:
        resolved = _BRACED_SEGMENT.sub(_resolve_segment, path)
        while "//" in resolved:
            resolved = resolved.replace("//", "/")
        return _normalize(resolved)
    _, _, new = path.partition("=>")
    return _normalize(new)


def _commits(root: Path, since: str) -> list[tuple[str, list[tuple[str, int, int]]]]:
    """Parse ``git log --numstat`` into (author, [(path, added, removed)]).

    One pass serves every signal here. Merges are excluded: their
    numstat re-reports changes already counted on the branch, which
    would double the churn of anything that landed through a merge.
    """
    output = run_git(
        ["log", "--no-merges", f"--since={since}", "--format=%x1ecommit%x1f%ae", "--numstat"],
        root,
    )
    if not output:
        return []
    parsed = []
    for block in output.split("\x1e"):
        if not block.strip():
            continue
        header, _, body = block.partition("\n")
        _, _, author = header.partition("\x1f")
        files = []
        for line in body.splitlines():
            fields = line.split("\t")
            if len(fields) != 3:
                continue
            added, removed, path = fields
            # "-" marks a binary file: no line counts to attribute, but
            # the commit still counts as a touch.
            files.append((
                _rename_target(path),
                int(added) if added.isdigit() else 0,
                int(removed) if removed.isdigit() else 0,
            ))
        parsed.append((author.strip(), files))
    return parsed


def file_churn(root: Path, since: str = DEFAULT_SINCE, tracked: set[str] | None = None) -> dict[str, FileChurn]:
    """Commits, line churn and author count per file over the window.

    ``tracked`` restricts the result to files the audit actually scans,
    so deleted files and excluded directories do not appear.
    """
    churn: dict[str, FileChurn] = {}
    for author, files in _commits(root, since):
        for path, added, removed in files:
            if tracked is not None and path not in tracked:
                continue
            entry = churn.setdefault(path, FileChurn(path))
            entry.commits += 1
            entry.added += added
            entry.removed += removed
            entry.authors.add(author)
    return churn


def hotspots(
    churn: dict[str, FileChurn], complexity: dict[str, int], limit: int = 25
) -> list[dict[str, Any]]:
    """Files ranked by churn x complexity, worst first.

    The product is the point. Ranking by complexity alone nominates code
    that may be perfectly stable, and ranking by churn alone nominates
    the changelog. A file scores here only by being both hard to read
    and constantly read.
    """
    ranked = []
    for path, measure in churn.items():
        weight = complexity.get(path, 0)
        if weight <= 0 or measure.commits <= 1:
            continue
        ranked.append({
            "file": path,
            "commits": measure.commits,
            "lines_changed": measure.churn,
            "complexity": weight,
            "authors": len(measure.authors),
            "score": measure.commits * weight,
        })
    ranked.sort(key=lambda item: (-item["score"], item["file"]))
    return ranked[:limit]


def history_section(
    root: Path, file_metrics: list, function_metrics: list, since: str = DEFAULT_SINCE
) -> dict[str, Any] | None:
    """The report's history block, or None when there is no history.

    None rather than empty lists: a shallow CI checkout and a genuinely
    quiet repository must not be indistinguishable in the report.

    Hotspots weight churn by the file's summed cognitive complexity, not
    its line count — a much-edited Markdown file is a changelog, not a
    hotspot. Cost of change is a comprehension cost, and cognitive
    complexity is the closest thing this package measures to one.
    """
    if not has_history(root):
        return None
    tracked = {metric.path for metric in file_metrics}
    weight: dict[str, int] = {}
    for metric in function_metrics:
        weight[metric.path] = weight.get(metric.path, 0) + metric.cognitive
    churn = file_churn(root, since, tracked)
    # Ownership concentration, over files with enough commits to have an
    # opinion. A file touched once has one author by arithmetic, not by
    # concentration; three commits is the floor for the distinction.
    settled = [entry for entry in churn.values() if entry.commits >= 3]
    single = sum(1 for entry in settled if len(entry.authors) == 1)
    return {
        "window": since,
        "files_changed": len(churn),
        "hotspots": hotspots(churn, weight),
        "change_coupling": change_coupling(root, since, tracked),
        "multi_commit_files": len(settled),
        "single_author_files": single,
    }


def change_coupling(
    root: Path,
    since: str = DEFAULT_SINCE,
    tracked: set[str] | None = None,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Pairs of files that keep changing together.

    Reported with *confidence* as well as support, because raw
    co-change counts just rank the busiest files. Confidence is the
    share of one file's commits that also touched the other, so a pair
    only surfaces when the relationship is most of what one of them
    does.
    """
    touches: dict[str, int] = {}
    together: dict[tuple[str, str], int] = {}
    for _, files in _commits(root, since):
        # Judge the sweep filter on the commit's *raw* size, before the
        # tracked filter. A 500-file dependency bump that happens to
        # touch 25 tracked files is still a sweep, and letting it through
        # would couple those 25 files to each other by pure coincidence.
        if len({path for path, _, _ in files}) > MAX_FILES_PER_COMMIT:
            continue
        paths = {path for path, _, _ in files if tracked is None or path in tracked}
        for path in paths:
            touches[path] = touches.get(path, 0) + 1
        for pair in combinations(sorted(paths), 2):
            together[pair] = together.get(pair, 0) + 1

    coupled = []
    for (left, right), support in together.items():
        if support < MIN_COUPLING_SUPPORT:
            continue
        confidence = support / min(touches[left], touches[right])
        if confidence < MIN_COUPLING_CONFIDENCE:
            continue
        coupled.append({
            "files": [left, right],
            "co_changes": support,
            "confidence": round(confidence, 3),
        })
    coupled.sort(key=lambda item: (-item["co_changes"], -item["confidence"], item["files"]))
    return coupled[:limit]
