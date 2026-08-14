#!/usr/bin/env python3
"""Show which analyzers a configuration selects, and why the rest were not.

Answers the only question that matters about a policy file: *given this
configuration, exactly which tools would run?* A policy nobody can evaluate is
a policy nobody trusts.

    python tools/resolve_pool.py                        # the current config
    python tools/resolve_pool.py --depth all            # a what-if
    python tools/resolve_pool.py --concerns duplication # one concern
    python tools/resolve_pool.py --explain pylint       # why is one tool in or out?

A **thin wrapper over the shipped resolver**, deliberately. This began as a
standalone implementation, which meant two copies of the precedence rules that
could disagree -- and the copy people run to check their policy disagreeing
with the copy that actually selects tools is the worst possible place for a
divergence.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from maintainability_audit._catalog import (  # noqa: E402
    CONCERNS,
    DEPTH_ORDER,
    LICENSE_POLICIES,
    PolicyError,
    decide,
    load_catalog,
    resolve_pool,
    settings_from,
)

CONFIG = Path(__file__).resolve().parent.parent / "maintainability-agent.json"


def _config(path: Path, overrides: dict[str, object]) -> dict[str, object]:
    raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    block = dict(raw.get("analyzers") or {})
    block.update({k: v for k, v in overrides.items() if v is not None})
    return {**raw, "analyzers": block}


def _explain(slug: str, settings: dict[str, object]) -> int:
    match = next((t for t in load_catalog() if t["slug"] == slug), None)
    if match is None:
        print(f"no tool named {slug!r} in the catalog")
        return 2
    selection = decide(match, settings)
    print(f"{slug}: {'SELECTED' if selection.selected else 'excluded'} -- {selection.reason}")
    print(f"  license   {match['license']}  ({match['license_class']})")
    print(f"  tier      {match['tier']}   adapter: {match['adapter']}")
    print(f"  measures  {', '.join(match['measures']) or '(not yet assessed)'}")
    print(f"  languages {', '.join(match['languages'][:12]) or '(none)'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--depth", choices=DEPTH_ORDER)
    parser.add_argument("--license-policy", dest="license_policy",
                        choices=sorted(LICENSE_POLICIES))
    parser.add_argument("--concerns", help="comma-separated: " + ",".join(CONCERNS) + ", or all")
    parser.add_argument("--explain", metavar="SLUG", help="why one tool is in or out")
    args = parser.parse_args()

    config = _config(args.config, {
        "depth": args.depth,
        "license_policy": args.license_policy,
        "concerns": args.concerns.split(",") if args.concerns else None,
    })

    try:
        settings = settings_from(config)
        if args.explain:
            return _explain(args.explain, settings)
        pool, decisions = resolve_pool(config)
    except PolicyError as error:
        print(f"config error: {error}")
        return 2

    print(f"config      : {args.config.name}")
    print(f"concerns    : {', '.join(settings['concerns'])}")
    print(f"depth       : {settings['depth']}")
    print(f"policy      : {settings['license_policy']} -> "
          f"{list(LICENSE_POLICIES[settings['license_policy']])}")
    for field in ("deny_tools", "deny_license_classes", "deny_concerns", "allow_tools"):
        if settings[field]:
            print(f"{field:<12}: {settings[field]}")

    print(f"\nWOULD RUN ({len(pool)}):")
    for selection in sorted((d for d in decisions if d.selected), key=lambda d: d.slug):
        print(f"  {selection.slug:<16} {selection.reason}")

    grouped: dict[str, list[str]] = defaultdict(list)
    for selection in decisions:
        if not selection.selected:
            grouped[selection.reason].append(selection.slug)
    print(f"\nexcluded ({sum(len(v) for v in grouped.values())}), by reason:")
    for reason, slugs in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(slugs):>4}  {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
