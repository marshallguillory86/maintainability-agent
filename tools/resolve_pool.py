#!/usr/bin/env python3
"""Resolve the analyzer pool from config + catalog, and explain the result.

Answers the only question that matters about a policy file: *given this
configuration, exactly which tools would run, and why was everything else
left out?* A policy nobody can evaluate is a policy nobody can trust.

    python tools/resolve_pool.py                        # use maintainability-agent.json
    python tools/resolve_pool.py --depth all            # override for a what-if
    python tools/resolve_pool.py --explain lizard       # why is one tool in or out?

This is a design-verification utility, not part of the audit. It reads the
same fields the agent will read, so a config that resolves here is a config
the agent can act on.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "analyzer-catalog.json"
CONFIG = ROOT / "maintainability-agent.json"

# Depth is cumulative: choosing "heavy" includes baseline and moderate.
DEPTH_ORDER = ["baseline", "moderate", "heavy", "all"]

# License policy is cumulative in the same way. Each entry lists the classes
# that policy admits *in addition to* the ones before it.
LICENSE_POLICIES: dict[str, list[str]] = {
    "permissive": ["permissive"],
    "copyleft-weak": ["permissive", "weak-copyleft"],
    "copyleft-any": ["permissive", "weak-copyleft", "strong-copyleft"],
    "commercial-free-tier": [
        "permissive", "weak-copyleft", "strong-copyleft", "proprietary-free-tier",
    ],
    "unverified": [
        "permissive", "weak-copyleft", "strong-copyleft", "proprietary-free-tier",
        "unverified",
    ],
}

DEFAULTS: dict[str, Any] = {
    "depth": "moderate",
    "license_policy": "permissive",
    "prompt_when_interactive": True,
    "allow_tools": [],
    "deny_tools": [],
    "deny_license_classes": [],
    "deny_concerns": ["security"],
    "timeout_seconds": 120,
}


class PolicyError(ValueError):
    """The configuration names something that does not exist."""


def load_settings(path: Path, overrides: dict[str, Any]) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    settings = {**DEFAULTS, **{k: v for k, v in (raw.get("analyzers") or {}).items() if k != "_doc"}}
    settings.update({k: v for k, v in overrides.items() if v is not None})

    if settings["depth"] not in DEPTH_ORDER:
        raise PolicyError(f"unknown depth {settings['depth']!r}; expected one of {DEPTH_ORDER}")
    if settings["license_policy"] not in LICENSE_POLICIES:
        raise PolicyError(
            f"unknown license_policy {settings['license_policy']!r}; "
            f"expected one of {sorted(LICENSE_POLICIES)}"
        )
    return settings


def decide(tool: dict[str, Any], settings: dict[str, Any]) -> tuple[bool, str]:
    """Return (selected, reason). The reason is stated for exclusions too.

    Precedence, applied in this order and deliberately not negotiable:
      1. an explicit allow admits a tool the policy tiers would exclude
      2. every deny wins, including over an allow -- an organization's
         prohibition must not be overridable by a per-repository opt-in
      3. otherwise the depth and license tiers decide
    """
    slug = tool["slug"]

    if slug in settings["deny_tools"]:
        return False, "denied by name in deny_tools"
    if tool["license_class"] in settings["deny_license_classes"]:
        return False, f"license class {tool['license_class']} denied"
    if set(tool["concerns"]) & set(settings["deny_concerns"]):
        overlap = sorted(set(tool["concerns"]) & set(settings["deny_concerns"]))
        return False, f"concern {','.join(overlap)} denied"

    if slug in settings["allow_tools"]:
        return True, "explicitly allowed by name"

    if tool["deprecated"]:
        return False, "deprecated upstream"
    if not tool["languages"]:
        return False, "targets no language"
    if tool["security_only"]:
        return False, "security-only; belongs to secure-code-agent"

    permitted = LICENSE_POLICIES[settings["license_policy"]]
    if tool["license_class"] not in permitted:
        return False, f"license class {tool['license_class']} outside policy {settings['license_policy']}"

    depth_limit = DEPTH_ORDER.index(settings["depth"])
    if DEPTH_ORDER.index(tool["tier"]) > depth_limit:
        return False, f"tier {tool['tier']} beyond depth {settings['depth']}"

    if tool["adapter"] != "implemented":
        return False, "no adapter yet -- cataloged, cannot be invoked"

    return True, f"tier {tool['tier']}, license {tool['license_class']}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--depth", choices=DEPTH_ORDER)
    parser.add_argument("--license-policy", dest="license_policy", choices=sorted(LICENSE_POLICIES))
    parser.add_argument("--explain", metavar="SLUG", help="explain one tool's inclusion or exclusion")
    args = parser.parse_args()

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    try:
        settings = load_settings(
            args.config, {"depth": args.depth, "license_policy": args.license_policy}
        )
    except PolicyError as exc:
        print(f"config error: {exc}")
        return 2

    tools = catalog["tools"]
    known = {t["slug"] for t in tools}
    for field in ("allow_tools", "deny_tools"):
        unknown = sorted(set(settings[field]) - known)
        if unknown:
            print(f"config error: {field} names tools not in the catalog: {unknown}")
            return 2

    if args.explain:
        match = next((t for t in tools if t["slug"] == args.explain), None)
        if match is None:
            print(f"no tool named {args.explain!r} in the catalog")
            return 2
        selected, reason = decide(match, settings)
        print(f"{match['slug']}: {'SELECTED' if selected else 'excluded'} -- {reason}")
        print(f"  license  {match['license']}  ({match['license_class']})")
        print(f"  tier     {match['tier']}   adapter: {match['adapter']}")
        print(f"  languages {', '.join(match['languages'][:12]) or '(none)'}")
        return 0

    selected, excluded = [], {}
    for tool in tools:
        ok, reason = decide(tool, settings)
        if ok:
            selected.append((tool["slug"], reason))
        else:
            excluded.setdefault(reason.split(" --")[0], []).append(tool["slug"])

    print(f"config      : {args.config.name}")
    print(f"depth       : {settings['depth']}")
    print(f"policy      : {settings['license_policy']} -> {LICENSE_POLICIES[settings['license_policy']]}")
    for field in ("deny_tools", "deny_license_classes", "deny_concerns", "allow_tools"):
        if settings[field]:
            print(f"{field:<12}: {settings[field]}")

    print(f"\nWOULD RUN ({len(selected)}):")
    for slug, reason in sorted(selected):
        print(f"  {slug:<16} {reason}")

    print(f"\nexcluded ({sum(len(v) for v in excluded.values())}), by reason:")
    for reason, slugs in sorted(excluded.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(slugs):>4}  {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
