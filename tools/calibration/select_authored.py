#!/usr/bin/env python3
"""Build the AI-assisted cohort, and an age-matched human control.

Comparing AI-written code against the mature-OSS corpus has a confound
big enough to invalidate the answer: every AI-assisted repository is new
and most are applications, while the reference corpus is libraries and
frameworks with a decade of maintenance behind them. A difference
between those two groups could be authorship, or it could be age, or
domain, and nothing in the data separates them.

So this builds two cohorts, both created in the same period:

- **ai-assisted** — repositories whose commits carry an AI co-author
  trailer on at least ``MIN_AI_FRACTION`` of recent commits. Not "used AI
  once"; substantially AI-authored.
- **recent-human** — repositories from the same era with *no* AI trailer
  on any sampled commit.

Comparing those two isolates authorship, because age and project type
are held roughly constant. Comparing either against the mature corpus
measures something else — maturity — and the report should say so rather
than pretending otherwise.

**Two limits worth stating plainly.** Trailers only exist where tooling
wrote them, so the AI cohort is self-selected toward deliberate
workflows. And absence of a trailer is not absence of AI: the
``recent-human`` cohort is really "no evidence of AI", which is weaker
than "written by hand".

    python3 tools/calibration/select_authored.py --mode ai --target 20 --cache-dir DIR
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from maintainability_audit.config import load_config  # noqa: E402
from maintainability_audit.declarations import DECLARATION_SUFFIXES  # noqa: E402
from maintainability_audit.metrics import iter_files  # noqa: E402
from maintainability_audit.source import SourceIndex  # noqa: E402

AI_TRAILER = re.compile(
    r"co-authored-by:\s*(claude|copilot|cursor|codex|devin|aider|gemini|chatgpt)"
    r"|generated with\s+\[?(claude|copilot|cursor|codex|aider)"
    r"|🤖\s*generated with",
    re.I,
)

# Same bar as the mature corpus, so both cohorts are filtered identically.
MIN_SOURCE_FILES = 20
MIN_DECLARATIONS = 100

# Languages the repository search can address, and therefore the ones a
# control cohort can be matched on. An AI-cohort repo GitHub labels
# something else (html, java) still counts toward the treatment group; it
# simply cannot be matched one-for-one.
SEARCHABLE_LANGUAGES = ("python", "typescript", "javascript", "go", "rust")

# Commits sampled per repo when judging authorship.
HISTORY_DEPTH = 300
MIN_COMMITS = 25

# Share of sampled commits that must carry a trailer for "AI-assisted".
MIN_AI_FRACTION = 0.5


def candidate_repos(pages: int) -> list[str]:
    """Repository names drawn from commit search for AI trailers."""
    names: list[str] = []
    for marker in ('"Co-Authored-By: Claude"', '"Generated with [Claude Code]"', '"Co-authored-by: Cursor"'):
        for page in range(1, pages + 1):
            result = subprocess.run(
                ["gh", "api", "-X", "GET", "search/commits",
                 "--raw-field", f"q={marker}", "--raw-field", "per_page=100",
                 "--raw-field", f"page={page}"],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                break
            for item in json.loads(result.stdout or "{}").get("items", []):
                names.append(item["repository"]["full_name"])
    seen: set[str] = set()
    return [n for n in names if not (n in seen or seen.add(n))]


def human_candidates(
    pages: int, min_stars: int, max_stars: int | None, created_after: str
) -> dict[str, list[str]]:
    """Control-cohort candidates per language, in the treatment's star band.

    **The star bound is the point.** Sorting by stars with only a floor
    returns the most popular recent repositories — `microsoft/markitdown`
    and similar — while the AI cohort, drawn from commit search with no
    popularity filter at all, has a median of *zero* stars. Comparing
    those two measures how many people are watching, not who wrote the
    code: stars proxy for team size, review pressure and how long the
    project has been taken seriously, all of which move these metrics
    directly. ``--match-to`` reads the bound off the treatment cohort.

    Sorted by recency rather than stars for the same reason. Within a
    band of 0-to-a-handful of stars, star-sorting would still skim the top
    of the band and reintroduce the gradient in miniature.

    **Returned per language, not as one list.** A flat list plus a
    first-past-the-post keep loop lets whichever language the search
    happened to visit first take every slot: the first matched control
    came back 20/20 Python against an AI cohort that is 13/20 TypeScript,
    which measures the language rather than the author. The caller fills
    a per-language quota copied from the treatment cohort.

    Paginated because the survival rate is low: most recent repositories
    either carry AI trailers or are not codebases, and an underpowered
    control is the same failure as an underpowered treatment.
    """
    star_range = f"{min_stars}..{max_stars}" if max_stars is not None else f">{min_stars}"
    found: dict[str, list[str]] = {}
    for language in SEARCHABLE_LANGUAGES:
        names: list[str] = []
        for page in range(1, pages + 1):
            result = subprocess.run(
                ["gh", "api", "-X", "GET", "search/repositories",
                 "--raw-field",
                 f"q=language:{language} stars:{star_range} created:>{created_after} "
                 f"pushed:>2026-01-01 archived:false",
                 "--raw-field", "sort=updated", "--raw-field", "per_page=100",
                 "--raw-field", f"page={page}"],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                break
            names.extend(i["full_name"] for i in json.loads(result.stdout or "{}").get("items", []))
        found[language] = list(dict.fromkeys(names))
    return found


def language_quota(reference: list[dict], target: int) -> dict[str, int]:
    """How many control repos each language should contribute.

    Copies the treatment cohort's language mix so authorship is what
    differs between the groups and language is not. Languages the
    repository search cannot address are folded into the largest
    searchable one rather than dropped, because dropping them would
    quietly shrink the control below its target.
    """
    counts = Counter(repo["language"] for repo in reference)
    quota = {lang: count for lang, count in counts.items() if lang in SEARCHABLE_LANGUAGES}
    scale = target / max(1, sum(quota.values()))
    scaled = {lang: max(1, round(count * scale)) for lang, count in quota.items()}
    if not scaled:
        return {"python": target}
    # Rounding can overshoot or undershoot; settle the difference on the
    # language the treatment cohort uses most.
    dominant = max(scaled, key=lambda lang: scaled[lang])
    scaled[dominant] = max(1, scaled[dominant] + target - sum(scaled.values()))
    return scaled


def metadata(full_name: str) -> dict | None:
    result = subprocess.run(["gh", "api", f"repos/{full_name}"], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    data = json.loads(result.stdout)
    if data.get("fork") or data.get("archived") or data.get("size", 0) > 400_000:
        return None
    return data


def clone(url: str, target: Path) -> bool:
    if (target / ".git").exists():
        return True
    result = subprocess.run(
        ["git", "clone", "--quiet", "--depth", str(HISTORY_DEPTH), url, str(target)],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def ai_fraction(path: Path) -> tuple[float, int]:
    """Share of sampled commits carrying an AI co-author trailer."""
    result = subprocess.run(
        ["git", "log", "--no-merges", "--format=%B%x1e"], cwd=path, capture_output=True, text=True
    )
    if result.returncode != 0:
        return 0.0, 0
    messages = [m for m in result.stdout.split("\x1e") if m.strip()]
    if not messages:
        return 0.0, 0
    marked = sum(1 for m in messages if AI_TRAILER.search(m))
    return marked / len(messages), len(messages)


def profile(path: Path) -> tuple[int, int]:
    config = load_config(None)
    index = SourceIndex()
    files = [p for p in iter_files(path, config) if p.suffix in DECLARATION_SUFFIXES]
    return len(files), sum(len(index.declarations(p)[0]) for p in files)


def consider(full_name: str, cache: Path, mode: str) -> dict | None:
    """Admit one repository to a cohort, or reject it.

    Every rejection is a filter the comparison depends on: too few sampled
    commits to judge authorship, the wrong side of the trailer evidence,
    or not enough code to measure. ``None`` means "not this one".
    """
    info = metadata(full_name)
    if info is None:
        return None
    target = cache / full_name.replace("/", "__")
    if not clone(info["clone_url"], target):
        return None
    fraction, commits = ai_fraction(target)
    if commits < MIN_COMMITS:
        return None
    # Absence of a trailer is weaker evidence than presence of one, so the
    # control demands zero rather than "below the AI bar" — a repo at 0.3
    # belongs in neither cohort.
    if mode == "ai" and fraction < MIN_AI_FRACTION:
        return None
    if mode == "human" and fraction > 0.0:
        return None
    files, declarations = profile(target)
    if files < MIN_SOURCE_FILES or declarations < MIN_DECLARATIONS:
        return None
    return {
        "name": full_name.replace("/", "__"),
        "full_name": full_name,
        "url": info["clone_url"],
        "commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=target,
                                 capture_output=True, text=True).stdout.strip(),
        "created": info["created_at"][:10],
        "language": (info.get("language") or "unknown").lower(),
        "stars": info["stargazers_count"],
        "ai_commit_fraction": round(fraction, 3),
        "commits_sampled": commits,
        "source_files": files,
        "declarations": declarations,
    }


def plan(args: argparse.Namespace, reference: list[dict]) -> tuple[dict[str, list[str]], dict[str, int]]:
    """Candidate pools and how many to take from each.

    The AI cohort comes from commit search, which has no language facet,
    so it is one undifferentiated pool. The control is searched per
    language precisely so it can be matched to whatever mix the AI cohort
    turned out to have.
    """
    if args.mode == "ai":
        return {"any": candidate_repos(args.pages)}, {"any": args.target}
    pools = human_candidates(args.pages, args.min_stars, args.max_stars, args.created_after)
    quota = (
        language_quota(reference, args.target)
        if reference
        else dict.fromkeys(pools, max(1, args.target // max(1, len(pools))))
    )
    print(f"language quota: {quota}", file=sys.stderr)
    return pools, quota


def fill(group: str, names: list[str], wanted: int, cache: Path, mode: str) -> list[dict]:
    """Take repositories from one pool until its quota is met."""
    kept: list[dict] = []
    for full_name in names:
        if len(kept) >= wanted:
            break
        entry = consider(full_name, cache, mode)
        if entry is None:
            continue
        kept.append(entry)
        print(
            f"  keep [{group}] {full_name:<40} ai={entry['ai_commit_fraction']:.2f}"
            f" files={entry['source_files']} decls={entry['declarations']}",
            file=sys.stderr,
        )
    if len(kept) < wanted:
        print(f"  !! {group}: only {len(kept)}/{wanted} found", file=sys.stderr)
    return kept


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["ai", "human"], required=True)
    parser.add_argument("--target", type=int, default=20)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--pages", type=int, default=4)
    parser.add_argument("--out", required=True)
    # Popularity bounds for the control. Defaults are deliberately absent:
    # the right values are whatever the *treatment* cohort turned out to
    # be, and hard-coding them once produced a control of the most-starred
    # recent repositories (microsoft/markitdown and similar) against an AI
    # cohort with a median of zero stars. See --match-to.
    parser.add_argument("--min-stars", type=int, default=0)
    parser.add_argument("--max-stars", type=int)
    parser.add_argument("--created-after", default="2023-06-01")
    parser.add_argument(
        "--match-to",
        help="Cohort JSON to match on. Reads its star range and creation window and "
             "uses them for the control query, so popularity and age are held constant.",
    )
    args = parser.parse_args()

    reference: list[dict] = []
    if args.match_to:
        reference = json.loads(Path(args.match_to).read_text(encoding="utf-8"))["repos"]
        args.max_stars = max(r["stars"] for r in reference)
        args.created_after = min(r["created"] for r in reference)
        print(
            f"matching {args.match_to}: stars <= {args.max_stars}, created > {args.created_after}",
            file=sys.stderr,
        )

    cache = Path(args.cache_dir)
    cache.mkdir(parents=True, exist_ok=True)

    pools, quota = plan(args, reference)
    print(f"{sum(len(p) for p in pools.values())} candidates", file=sys.stderr)
    kept: list[dict] = []
    for group, names in pools.items():
        kept.extend(fill(group, names, quota.get(group, 0), cache, args.mode))

    Path(args.out).write_text(json.dumps({"cohort": args.mode, "repos": kept}, indent=1) + "\n", encoding="utf-8")
    print(f"kept {len(kept)} -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
