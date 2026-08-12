#!/usr/bin/env python3
"""Build the analyzer catalog from the analysis-tools.dev database.

The catalog is *data about tools*, not a claim that any of them run.
Two fields are deliberately distinct:

  license_status   what the source database says, normalized. Tools whose
                   license GitHub could not map to an SPDX id are marked
                   ``unverified`` rather than guessed in either direction.
                   flake8 and checkstyle both land there and both are FOSS,
                   so "Other" is not evidence of anything.

  adapter          whether *this* project can invoke the tool and parse it.
                   Almost all are ``none``. A catalog entry is a fact about
                   the world; an adapter is work someone has to do.

Regenerate with:  python tools/build_catalog.py <path-to-static-analysis-checkout>
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

SOURCE_REPO = "https://github.com/analysis-tools-dev/static-analysis"
SOURCE_SHA = "66668c6cc5b2db72d0233033efe7ccf2c489aaf8"
SOURCE_DATE = "2026-06-10"
SOURCE_LICENSE = "CC0-1.0"

# Tags that name a language rather than a concern. Anything not here is
# treated as a concern tag (security, ci, container...) and does not make a
# tool eligible on language grounds alone.
LANGUAGE_TAGS = {
    "abap", "ada", "apex", "assembly", "awk", "bash", "c", "clojure", "cmake",
    "cobol", "coffeescript", "coldfusion", "cpp", "crystal", "csharp", "css",
    "d", "dart", "delphi", "dockerfile", "elixir", "elm", "erlang", "fortran",
    "fsharp", "gherkin", "go", "graphql", "groovy", "haskell", "haxe", "hcl",
    "html", "java", "javascript", "json", "jsx", "julia", "kotlin", "latex",
    "lisp", "lua", "makefile", "markdown", "matlab", "nim", "objectivec",
    "ocaml", "opa", "openapi", "pascal", "perl", "php", "powershell", "prolog",
    "protobuf", "puppet", "python", "r", "raku", "reason", "ruby", "rust",
    "sass", "scala", "scheme", "shell", "solidity", "sql", "svelte", "swift",
    "tcl", "terraform", "toml", "typescript", "vala", "vhdl", "viml", "vue",
    "xml", "yaml", "zig",
}

# Concerns owned by secure-code-agent. A tool tagged only with these is
# recorded and excluded from this agent's pool, per ADR 006's scope line.
SECURITY_TAGS = {"security", "secrets", "sca", "container", "kubernetes"}

PROPRIETARY = {"proprietary", "commercial"}
UNVERIFIABLE = {"other", "unknown", "", "noassertion", "custom"}

# License policy classes. An organization may forbid a class outright, so the
# classification has to be conservative and inspectable rather than clever.
#
# Order matters: the first matching pattern wins, and source-available and
# copyleft are tested before permissive so that a dual "GPL or MIT" is not
# caught by the permissive test on its second half. Dual licenses are then
# resolved deliberately in classify_license, because the licensee chooses.
#
# Nothing here is legal advice. Whether invoking a GPL analyzer as a separate
# process affects the code it scans is a question for the adopting
# organization's counsel; this field exists so their answer can be enforced.
_SOURCE_AVAILABLE = (
    "elastic license", "business source", "sustainable use",
    "android software development kit",
)
_STRONG_COPYLEFT = (
    "agpl", "affero", "gpl-3", "gpl v3", "gpl-2", "gpl v2", "gplv2", "gplv3",
    "general public license", "gnu gpl", "gnu public license", "cc-by-sa",
    "european union public license", "eupl", "gpl",
)
_WEAK_COPYLEFT = ("lgpl", "lesser general public", "mozilla public", "mpl-", "eclipse public", "cddl")
_PERMISSIVE = (
    "mit", "bsd", "apache", "isc", "zlib", "boost", "bsl-1.0", "upl",
    "postgresql license", "artistic", "uiuc", "llvm release", "ncsa",
    "unlicense", "cc0", "wtfpl", "python software foundation",
)


def classify_license(name: str, status: str) -> str:
    """Map a license string to a policy class. Unmatched means unmatched."""
    if status == "proprietary":
        return "proprietary"
    if status == "unverified":
        return "unverified"
    low = name.lower()

    if any(token in low for token in _SOURCE_AVAILABLE):
        return "source-available"

    # A dual license gives the licensee the choice, so it takes the most
    # permissive class on offer. Split on the separators actually present in
    # the data: "MIT / Apache 2.0", "Apache-2.0, MIT license", "GPL v3 or ...".
    parts = [low]
    for sep in (" / ", "/", " or ", ", ", " & ", " + "):
        if sep in low:
            parts = [p.strip() for p in low.split(sep) if p.strip()]
            break
    if len(parts) > 1:
        classes = {classify_license(part, "foss") for part in parts}
        for best in ("permissive", "weak-copyleft", "strong-copyleft"):
            if best in classes:
                return best
        return "unverified"

    if any(token in low for token in _WEAK_COPYLEFT):
        return "weak-copyleft"
    if any(token in low for token in _STRONG_COPYLEFT):
        return "strong-copyleft"
    if any(token in low for token in _PERMISSIVE):
        return "permissive"
    return "unverified"

# Tools this project has actually installed and executed, with the tier they
# are assigned to. Nothing reaches a tier below "all" without being run:
# a tier is a promise that the tool works, and a promise needs evidence.
#
# baseline  multi-language, one install, no project config, seconds to run
# moderate  + mainstream per-language linters, still cheap
# heavy     + slower or config-hungry tools
VERIFIED_TIERS = {
    "lizard": "baseline",
    "radon": "baseline",
    "ruff": "baseline",
    "jscpd": "baseline",
    "pylint": "moderate",
    "vulture": "moderate",
    "eslint": "moderate",
    "flake8": "moderate",
    "complexipy": "moderate",
    "interrogate": "moderate",
    "pydocstyle": "moderate",
    "cohesion": "heavy",
    "multimetric": "heavy",
    "wily": "heavy",
    "xenon": "heavy",
}


# Tools this project installed and ran that the source snapshot does not list.
# Licenses here were read from the installed distribution's own metadata, not
# recalled: complexipy and interrogate from their OSI classifiers, multimetric
# from its ``License-Expression``, jscpd from the npm registry. Each is a fact
# recoverable by running the command in the comment.
LOCAL_ADDITIONS = [
    {
        # npm view jscpd license
        "slug": "jscpd", "name": "jscpd", "license": "MIT", "version_seen": "5.0.14",
        "categories": ["linter"], "concerns": ["duplication"],
        "languages": sorted(LANGUAGE_TAGS),  # ~150 formats; declares by detection
        "source": "https://github.com/kucherenko/jscpd",
    },
    {
        # importlib.metadata classifier: License :: OSI Approved :: MIT License
        "slug": "complexipy", "name": "complexipy", "license": "MIT", "version_seen": "7.0.0",
        "categories": ["linter"], "concerns": ["complexity"],
        "languages": ["python"],
        "source": "https://github.com/rohaquinlop/complexipy",
    },
    {
        # importlib.metadata classifier: License :: OSI Approved :: MIT License
        "slug": "interrogate", "name": "interrogate", "license": "MIT", "version_seen": "1.7.0",
        "categories": ["linter"], "concerns": ["documentation"],
        "languages": ["python"],
        "source": "https://github.com/econchick/interrogate",
    },
    {
        # importlib.metadata License-Expression: Zlib
        "slug": "multimetric", "name": "multimetric", "license": "Zlib", "version_seen": "2.4.4",
        "categories": ["linter"], "concerns": ["metrics"],
        "languages": ["python", "c", "cpp", "java", "javascript", "go", "ruby", "php"],
        "source": "https://github.com/priv-kweihmann/multimetric",
    },
]


def normalize_license(raw: str) -> tuple[str, str]:
    """Return (status, normalized name). Never guesses."""
    text = str(raw or "").strip()
    low = text.lower()
    if low in UNVERIFIABLE:
        return "unverified", text or "(none stated)"
    if low in PROPRIETARY:
        return "proprietary", text
    if any(token in low for token in _SOURCE_AVAILABLE):
        return "source-available", text
    return "foss", text


def load(source: Path) -> list[dict[str, Any]]:
    out = []
    for path in sorted((source / "data" / "tools").glob("*.yml")):
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not loaded:
            continue
        loaded["_slug"] = path.stem
        out.append(loaded)
    return out


def build(records: list[dict[str, Any]]) -> dict[str, Any]:
    entries = []
    for record in records:
        tags = set(record.get("tags") or [])
        languages = sorted(tags & LANGUAGE_TAGS)
        concerns = sorted(tags - LANGUAGE_TAGS)
        status, license_name = normalize_license(record.get("license"))
        slug = record["_slug"]

        # A proprietary tool with a free or OSS plan is a different policy
        # question from one that is paid-only: some organizations permit the
        # former for open work. The distinction comes from the source's own
        # ``plans`` block, so it is a recorded fact rather than an inference.
        plans = record.get("plans") if isinstance(record.get("plans"), dict) else {}
        free_tier = bool(plans.get("free") or plans.get("oss"))
        license_class = classify_license(license_name, status)
        if license_class == "proprietary" and free_tier:
            license_class = "proprietary-free-tier"

        entries.append({
            "slug": slug,
            "name": record.get("name", slug),
            "license": license_name,
            "license_status": status,
            "license_class": license_class,
            "free_tier": free_tier,
            "deprecated": bool(record.get("deprecated")),
            "categories": sorted(record.get("categories") or []),
            "languages": languages,
            "concerns": concerns,
            "security_only": bool(concerns) and set(concerns) <= SECURITY_TAGS and not languages,
            "source": record.get("source") or record.get("homepage") or "",
            "tier": VERIFIED_TIERS.get(slug, "all"),
            "adapter": "implemented" if slug in VERIFIED_TIERS else "none",
        })

    known = {e["slug"] for e in entries}
    for extra in LOCAL_ADDITIONS:
        if extra["slug"] in known:
            continue
        entries.append({
            "slug": extra["slug"],
            "name": extra["name"],
            "license": extra["license"],
            "license_status": "foss",
            "license_class": classify_license(extra["license"], "foss"),
            "free_tier": False,
            "deprecated": False,
            "categories": extra["categories"],
            "languages": extra["languages"],
            "concerns": extra["concerns"],
            "security_only": False,
            "source": extra["source"],
            "tier": VERIFIED_TIERS.get(extra["slug"], "all"),
            "adapter": "implemented" if extra["slug"] in VERIFIED_TIERS else "none",
            "provenance": f"verified locally, version {extra['version_seen']}",
        })

    entries.sort(key=lambda e: e["slug"])
    eligible = [e for e in entries if is_eligible(e)]
    return {
        "provenance": {
            "source": SOURCE_REPO,
            "commit": SOURCE_SHA,
            "captured": SOURCE_DATE,
            "source_license": SOURCE_LICENSE,
            "note": (
                "Facts in this file (name, license, languages, source URL) come from "
                "the snapshot above. Tier and adapter fields are this project's own "
                "and are not claims made by the source."
            ),
        },
        "counts": {
            "in_source": len(entries),
            "eligible": len(eligible),
            "by_tier": dict(Counter(e["tier"] for e in eligible)),
            "by_license_status": dict(Counter(e["license_status"] for e in entries)),
            "by_license_class": dict(Counter(e["license_class"] for e in entries)),
            "eligible_by_license_class": dict(Counter(e["license_class"] for e in eligible)),
            "adapters_implemented": sum(1 for e in entries if e["adapter"] == "implemented"),
        },
        "tools": entries,
    }


# Classes that may appear in the pool at all. "source-available" is excluded:
# the Elastic License and the Business Source License are not OSI-approved and
# restrict commercial use, so counting them as FOSS was a bug — they are
# cataloged and marked, never selected by a FOSS-only policy.
POOLABLE_CLASSES = {"permissive", "weak-copyleft", "strong-copyleft"}


def is_eligible(entry: dict[str, Any]) -> bool:
    """Eligible for this agent's pool: open source, current, has a language, not security-only."""
    return (
        entry["license_class"] in POOLABLE_CLASSES
        and not entry["deprecated"]
        and bool(entry["languages"])
        and not entry["security_only"]
    )


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    records = load(Path(sys.argv[1]))
    catalog = build(records)
    out = Path(__file__).resolve().parent.parent / "data" / "analyzer-catalog.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(catalog, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    counts = catalog["counts"]
    print(f"wrote {out.relative_to(out.parent.parent)}")
    print(f"  tools in source snapshot : {counts['in_source']}")
    print(f"  eligible for this agent  : {counts['eligible']}")
    print(f"  adapters implemented     : {counts['adapters_implemented']}")
    print(f"  by license status        : {counts['by_license_status']}")
    print(f"  eligible by tier         : {counts['by_tier']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
