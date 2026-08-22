"""Which analyzers may run — ADR 006.

Resolves the shipped catalog against three independent selectors, so a user
answers *what do you want examined*, *how deep* and *what may we legally run*
and never names a tool.

The catalog is data: 760 entries with licence, licence class, languages and
what each measures, built by ``tools/build_catalog.py`` from a pinned snapshot
of the analysis-tools.dev database plus locally verified additions. Nothing
here decides whether a tool *works* — that is the runner's job, proven by
invocation — only whether it is *permitted and wanted*.

Precedence is fixed and not configurable: **every deny wins, including over an
explicit allow.** An organization's prohibition must not be overridable by a
per-repository opt-in, or the licence policy is advisory rather than enforced.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

# Inside the package, not beside it. This path used to climb three
# parents to a repository-root `data/` directory, which resolves only in
# a source checkout: from an installed wheel the same expression pointed
# at `<site-packages>/../data/analyzer-catalog.json`, a path that has
# never existed. Nine releases shipped with no catalog at all, so every
# pip-installed user silently lost the analyzer pool — the product's
# primary evidence source — and got built-in fallback numbers instead.
# Package data resolves identically from a checkout and from a wheel.
CATALOG_PATH = Path(__file__).resolve().parent / "_assets" / "analyzer-catalog.json"

# Cumulative: choosing "heavy" includes baseline and moderate. A tier below
# "all" is a promise the tool works, so nothing enters one until this project
# has installed it, run it and parsed its output.
DEPTH_ORDER: tuple[str, ...] = ("baseline", "moderate", "heavy", "all")

# Cumulative in the same way. Each policy admits the classes before it.
# `source-available` and paid proprietary tools never appear: adding one
# requires naming it in `allow_tools`, which is a deliberate act.
LICENSE_POLICIES: dict[str, tuple[str, ...]] = {
    "permissive": ("permissive",),
    "copyleft-weak": ("permissive", "weak-copyleft"),
    "copyleft-any": ("permissive", "weak-copyleft", "strong-copyleft"),
    "commercial-free-tier": (
        "permissive", "weak-copyleft", "strong-copyleft", "proprietary-free-tier",
    ),
    "unverified": (
        "permissive", "weak-copyleft", "strong-copyleft", "proprietary-free-tier",
        "unverified",
    ),
}

CONCERNS: tuple[str, ...] = (
    "complexity", "duplication", "dead-code", "documentation",
    "structure", "testing", "style", "types", "metrics",
)

# A concern is what a *user* asks for; a concept is what a tool measures.
# "complexity" covers two genuinely different metrics — cyclomatic counts
# branches, cognitive weights nesting — and they must not be averaged
# together, so the vocabularies are kept apart and mapped here.
CONCERN_CONCEPTS: dict[str, tuple[str, ...]] = {
    "complexity": (
        "cyclomatic_complexity", "cognitive_complexity", "file_cyclomatic_complexity",
    ),
    "metrics": ("maintainability_index", "halstead_difficulty", "declaration_lines"),
    # `cohesion` is per-class method/attribute cohesion — a fact about
    # how a type is organised, which is the structure concern.
    "structure": ("parameters", "cohesion"),
}


def concepts_for(concern: str) -> tuple[str, ...]:
    return CONCERN_CONCEPTS.get(concern, (concern,))


DEFAULTS: dict[str, Any] = {
    "concerns": ["all"],
    "depth": "moderate",
    "license_policy": "permissive",
    "prompt_when_interactive": True,
    # Whether a missing Node tool may be fetched (npx --yes) during a
    # run. Off: acquisition is a network action, and P1's separation of
    # analysis from acquisition only means something if acquisition is
    # chosen, not defaulted. A missing tool is reported not-installed
    # with its install command instead.
    "acquire_tools": False,
    "allow_tools": [],
    "deny_tools": [],
    "deny_license_classes": [],
    "deny_concerns": ["security"],
    "timeout_seconds": 120,
}


class PolicyError(ValueError):
    """The configuration names something the catalog does not contain."""


@dataclass(frozen=True)
class Selection:
    """One tool's fate, with the reason either way.

    Exclusions carry a reason because "why didn't it run my linter?" is the
    first question anyone asks, and a pool that cannot answer it is a pool
    nobody trusts.
    """

    slug: str
    selected: bool
    reason: str


@lru_cache(maxsize=1)
def load_catalog(path: str | None = None) -> tuple[dict[str, Any], ...]:
    """Every catalog entry. Cached — the file is data and does not change mid-run."""
    source = Path(path) if path else CATALOG_PATH
    if not source.exists():
        raise PolicyError(
            f"analyzer catalog missing at {source}. Rebuild it with "
            "tools/build_catalog.py; the package cannot select tools without it."
        )
    return tuple(json.loads(source.read_text(encoding="utf-8"))["tools"])


def settings_from(config: dict[str, Any]) -> dict[str, Any]:
    """The analyzer block, defaulted and validated.

    An unknown depth or policy raises rather than falling back: silently
    defaulting would run a different pool than the one the operator asked
    for, and the report would attribute the result to their choice.
    """
    block = {k: v for k, v in (config.get("analyzers") or {}).items() if k != "_doc"}
    settings = {**DEFAULTS, **block}

    if settings["depth"] not in DEPTH_ORDER:
        raise PolicyError(f"unknown depth {settings['depth']!r}; expected one of {DEPTH_ORDER}")
    if settings["license_policy"] not in LICENSE_POLICIES:
        raise PolicyError(
            f"unknown license_policy {settings['license_policy']!r}; "
            f"expected one of {sorted(LICENSE_POLICIES)}"
        )
    unknown = set(settings["concerns"]) - set(CONCERNS) - {"all"}
    if unknown:
        raise PolicyError(f"unknown concerns {sorted(unknown)}; expected from {list(CONCERNS)}")
    return settings


def decide(tool: dict[str, Any], settings: dict[str, Any]) -> Selection:
    """Whether one tool is permitted and wanted, and why.

    Order is deliberate and fixed:

    1. every deny, including over an explicit allow;
    2. an explicit allow, which admits a tool the tiers would exclude;
    3. the depth, licence and concern tiers.
    """
    slug = tool["slug"]

    if slug in settings["deny_tools"]:
        return Selection(slug, False, "denied by name")
    if tool["license_class"] in settings["deny_license_classes"]:
        return Selection(slug, False, f"license class {tool['license_class']} denied")
    denied_concerns = set(tool["upstream_tags"]) & set(settings["deny_concerns"])
    if denied_concerns:
        return Selection(slug, False, f"concern {','.join(sorted(denied_concerns))} denied")

    if slug in settings["allow_tools"]:
        return Selection(slug, True, "explicitly allowed by name")

    if tool["deprecated"]:
        return Selection(slug, False, "deprecated upstream")
    if not tool["languages"]:
        return Selection(slug, False, "targets no language")
    if tool["security_only"]:
        return Selection(slug, False, "security-only; belongs to secure-code-agent")

    permitted = LICENSE_POLICIES[settings["license_policy"]]
    if tool["license_class"] not in permitted:
        return Selection(
            slug, False,
            f"license class {tool['license_class']} outside policy {settings['license_policy']}",
        )
    if DEPTH_ORDER.index(tool["tier"]) > DEPTH_ORDER.index(settings["depth"]):
        return Selection(slug, False, f"tier {tool['tier']} beyond depth {settings['depth']}")
    if tool["adapter"] != "implemented":
        # Catalogued but not invokable. Reported rather than hidden: the
        # inventory is a fact about the world, an adapter is work someone
        # has to do, and conflating them would overstate what ran.
        return Selection(slug, False, "no adapter yet")

    wanted = settings["concerns"]
    measures = set(tool["measures"])
    if "all" not in wanted and not (measures & set(wanted)):
        return Selection(slug, False, f"measures {','.join(sorted(measures)) or 'nothing'}")

    return Selection(
        slug, True,
        f"measures {','.join(sorted(measures))}; tier {tool['tier']}, {tool['license_class']}",
    )


def resolve_pool(
    config: dict[str, Any], catalog_path: str | None = None
) -> tuple[list[dict[str, Any]], list[Selection]]:
    """The tools to run, and every decision made getting there.

    Returns both because the report has to state what was *not* run and
    why. A pool without its exclusions cannot explain itself.
    """
    settings = settings_from(config)
    catalog = load_catalog(catalog_path)
    known = {tool["slug"] for tool in catalog}

    for field in ("allow_tools", "deny_tools"):
        missing = sorted(set(settings[field]) - known)
        if missing:
            raise PolicyError(
                f"{field} names tools absent from the catalog: {missing}. "
                "A misspelled slug would silently do nothing."
            )

    decisions = [decide(tool, settings) for tool in catalog]
    chosen = {d.slug for d in decisions if d.selected}
    return [t for t in catalog if t["slug"] in chosen], decisions
