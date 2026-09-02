#!/usr/bin/env python3
"""Build the analyzer catalog from the analysis-tools.dev database.

The catalog is *data about tools*, not a claim that any of them run.
Two fields are deliberately distinct:

  license_status   what the source database says, normalized. Tools whose
                   license GitHub could not map to an SPDX id are marked
                   ``unverified`` rather than guessed in either direction.
                   flake8 lands there and is FOSS, so "Other" is not
                   evidence of anything. Checkstyle's LGPL is verified
                   from its upstream LICENSE rather than left here.

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
# Separators that actually appear in the data: "MIT / Apache 2.0",
# "Apache-2.0, MIT license", "GPL v3 or Perl Artistic License 2.0".
_DUAL_SEPARATORS = (" / ", "/", " or ", ", ", " & ", " + ")


# Tools this project has actually installed and executed, with the tier they
# are assigned to. Nothing reaches a tier below "all" without being run:
# a tier is a promise that the tool works, and a promise needs evidence.
#
# baseline  multi-language, one install, no project config, seconds to run
# moderate  + mainstream per-language linters, still cheap
# heavy     + slower or config-hungry tools
VERIFIED_TIERS = {
    # baseline: zero project configuration, fast, runs on whatever languages
    # are present. Not "multi-language only" -- a zero-config Python tool is
    # baseline for a Python repository.
    "lizard": "baseline",       # multi-language CCN/NLOC/params/tokens
    "multimetric": "baseline",  # multi-language MI, Halstead, 25 metrics
    "jscpd": "baseline",        # multi-language clone detection
    "radon": "baseline",        # Python MI, CC, Halstead
    "ruff": "baseline",         # Python lint, ~800 rules
    "vulture": "baseline",      # Python dead code
    "complexipy": "baseline",   # Python cognitive complexity
    "interrogate": "baseline",  # Python docstring coverage
    "pydocstyle": "baseline",   # Python docstring conventions
    # Rust-fast and zero-config on a Fortran tree, which is what
    # baseline means. Installed, run and parsed here (1.5.0) before
    # being moved out of "all" — the rule this table states.
    "fortitude": "baseline",    # Fortran lint, 100+ rules
    # moderate: needs configuration, tuning, or noticeably more time
    "pylint": "moderate",
    "mypy": "moderate",
    "flake8": "moderate",
    "eslint": "moderate",
    "cohesion": "moderate",
    "pmd": "moderate",
    "checkstyle": "moderate",
    "spotbugs": "moderate",
}


# Re-exported: license normalization moved to `catalog_licenses`,
# and this module stays the door every caller comes through.
from catalog_licenses import (  # noqa: E402
    classify_license,
    normalize_license,
)

IMPLEMENTED_ADAPTERS = frozenset({
    "checkstyle", "cohesion", "complexipy", "eslint", "flake8", "fortitude",
    "interrogate", "jscpd", "lizard", "multimetric", "mypy", "pydocstyle",
    "pylint", "radon", "pmd", "ruff", "spotbugs", "vulture",
})

# Deliberately unadapted, with the reason, so nobody writes one later
# believing it was an oversight.
#
# xenon is a pass/fail gate layered on radon: it re-ranks radon's own
# cyclomatic numbers against thresholds and emits nothing radon has not
# already given. Adding it would put a fourth "independent" reading on
# complexity that is strictly derived from one already counted --
# inflating apparent corroboration without adding evidence. Two tools
# agreeing because one *is* the other is worse than one tool alone,
# because it looks like confirmation.
NOT_ADAPTED: dict[str, str] = {
    "xenon": "a threshold gate over radon; contributes no independent measurement",
}

# Languages the upstream inventory does not list and this project has
# *run the tool on*. The inventory's tags are what a tool's page says,
# and pages go stale: lizard has read Fortran for years, the tag was
# never added, and because selection is gated on this list, lizard came
# out `not-applicable` on every Fortran repository. Fortran therefore had
# no metric emitter — not because none existed, but because of one stale
# row, while the tool that could measure it sat installed in the pool.
#
# Evidence for each entry, so nobody has to take it on faith: lizard
# 1.24.0 on a nested-loop kernel reports CCN 5, NLOC 11, 2 parameters —
# the same 5 this project's own reading gives after 1.6.0.
VERIFIED_EXTRA_LANGUAGES: dict[str, tuple[str, ...]] = {
    "lizard": ("fortran",),
}

VERIFIED_MEASURES: dict[str, tuple[str, ...]] = {
    "lizard":      ("complexity", "structure", "metrics", "duplication"),
    "radon":       ("complexity", "metrics"),
    "ruff":        ("style", "complexity", "dead-code"),
    # Not "types": fortitude checks that things are *declared*
    # (`implicit none`, `intent`, kind parameters), which a reader
    # would take for type-checking. Nothing type-checks Fortran here.
    "fortitude":   ("style", "dead-code"),
    "jscpd":       ("duplication",),
    "pylint":      ("structure", "style"),
    "mypy":        ("types",),
    "flake8":      ("style", "complexity"),
    "vulture":     ("dead-code",),
    "eslint":      ("style", "complexity", "structure"),
    "complexipy":  ("complexity",),
    "interrogate": ("documentation",),
    "pydocstyle":  ("documentation", "style"),
    "cohesion":    ("structure",),
    "multimetric": ("metrics", "complexity", "documentation"),
    # The concern first ("complexity" is what `decide()` intersects with
    # a configured concern pool), then the concepts it is served by — a
    # concepts-only tuple dropped PMD from a complexity-only pool
    # (audit M on 549fcad).
    "pmd":         ("complexity", "cognitive_complexity", "cyclomatic_complexity"),
    "checkstyle":  ("style", "documentation"),
    "spotbugs":    ("style",),
    "cloc": ("metrics", "documentation"),
    "wily":        ("metrics",),
}

# Licences the upstream snapshot could not classify, resolved here from the
# installed distribution's own metadata. `unverified` is the honest default
# for a licence nobody confirmed, but leaving a genuinely permissive tool
# there hides it from every policy except the loosest -- so verifying beats
# both guessing and shrugging.
#
# Each entry names the evidence, and each is recoverable by running the
# command in the comment.
VERIFIED_LICENSES: dict[str, tuple[str, str]] = {
    # importlib.metadata License-Expression: MIT, plus a bundled LICENSE
    # opening "Mypy (and mypyc) are licensed under the terms of the MIT
    # license". Upstream records "Other" because GitHub's detector could
    # not map the file.
    "mypy": ("MIT", "License-Expression in the installed distribution"),
    # https://github.com/pmd/pmd/blob/main/LICENSE
    "pmd": ("BSD-style", "PMD upstream LICENSE file"),
    # https://github.com/checkstyle/checkstyle/blob/master/LICENSE
    "checkstyle": ("LGPL-2.1-or-later", "Checkstyle upstream LICENSE file"),
}

# Tools this project installed and ran that the source snapshot does not list.
# Licenses here were read from the installed distribution's own metadata, not
# recalled: complexipy and interrogate from their OSI classifiers, multimetric
# from its ``License-Expression``, jscpd from the npm registry. Each is a fact
# recoverable by running the command in the comment.
LOCAL_ADDITIONS = [
    {
        # npx cloc --version ; https://github.com/AlDanial/cloc  (GPL-2.0)
        "slug": "cloc", "name": "cloc", "license": "GNU General Public License v2.0",
        "version_seen": "2.06", "categories": ["linter"], "concerns": ["metrics"],
        "languages": sorted(LANGUAGE_TAGS),
        "source": "https://github.com/AlDanial/cloc",
    },
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


def load(source: Path) -> list[dict[str, Any]]:
    out = []
    for path in sorted((source / "data" / "tools").glob("*.yml")):
        import yaml  # lazy: tests import is_eligible without PyYAML

        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not loaded:
            continue
        loaded["_slug"] = path.stem
        out.append(loaded)
    return out


def _entry(record: dict[str, Any]) -> dict[str, Any]:
    """One catalog row, from one source record.

    Split out of ``build`` when the audit put that function at complexity
    22 against a limit of 15. Row construction and the counting pass were
    two jobs sharing a loop.
    """
    tags = set(record.get("tags") or [])
    slug_for_languages = record["_slug"]
    languages = sorted(
        (tags & LANGUAGE_TAGS)
        | set(VERIFIED_EXTRA_LANGUAGES.get(slug_for_languages, ()))
    )
    concerns = sorted(tags - LANGUAGE_TAGS)
    slug = record["_slug"]
    verified = VERIFIED_LICENSES.get(slug)
    status, license_name = normalize_license(
        verified[0] if verified else record.get("license")
    )

    # A proprietary tool with a free or OSS plan is a different policy
    # question from one that is paid-only.
    plans = record.get("plans") if isinstance(record.get("plans"), dict) else {}
    free_tier = bool(plans.get("free") or plans.get("oss"))
    license_class = classify_license(license_name, status)
    if license_class == "proprietary" and free_tier:
        license_class = "proprietary-free-tier"

    return {
        "slug": slug,
        "name": record.get("name", slug),
        "license": license_name,
        "license_status": status,
        "license_class": license_class,
        "license_evidence": verified[1] if verified else "upstream catalog",
        "free_tier": free_tier,
        "deprecated": bool(record.get("deprecated")),
        "categories": sorted(record.get("categories") or []),
        "languages": languages,
        "upstream_tags": concerns,
        "measures": sorted(VERIFIED_MEASURES.get(slug, ())),
        "security_only": bool(concerns) and set(concerns) <= SECURITY_TAGS and not languages,
        "source": record.get("source") or record.get("homepage") or "",
        "tier": VERIFIED_TIERS.get(slug, "all"),
        "adapter": "implemented" if slug in IMPLEMENTED_ADAPTERS else "none",
    }


def _local_entry(extra: dict[str, Any]) -> dict[str, Any]:
    """A row for a tool this project verified but the source does not list."""
    return {
        "slug": extra["slug"],
        "name": extra["name"],
        "license": extra["license"],
        "license_status": "foss",
        "license_class": classify_license(extra["license"], "foss"),
        "license_evidence": f"verified locally, version {extra['version_seen']}",
        "free_tier": False,
        "deprecated": False,
        "categories": extra["categories"],
        "languages": extra["languages"],
        "upstream_tags": extra["concerns"],
        "measures": sorted(VERIFIED_MEASURES.get(extra["slug"], ())),
        "security_only": False,
        "source": extra["source"],
        "tier": VERIFIED_TIERS.get(extra["slug"], "all"),
        "adapter": "implemented" if extra["slug"] in IMPLEMENTED_ADAPTERS else "none",
    }


def build(records: list[dict[str, Any]]) -> dict[str, Any]:
    entries = [_entry(record) for record in records]
    known = {entry["slug"] for entry in entries}
    entries.extend(_local_entry(extra) for extra in LOCAL_ADDITIONS if extra["slug"] not in known)
    entries.sort(key=lambda entry: entry["slug"])
    eligible = [entry for entry in entries if is_eligible(entry)]

    return {
        "provenance": {
            "source": SOURCE_REPO,
            "commit": SOURCE_SHA,
            "captured": SOURCE_DATE,
            "source_license": SOURCE_LICENSE,
            "note": (
                "Facts in this file (name, license, languages, source URL) come from "
                "the snapshot above. Tier and adapter fields are this project's own "
                "and are not claims made by the source. PMD's BSD-style license is "
                "verified from the upstream PMD LICENSE file. Checkstyle's "
                "LGPL-2.1-or-later license is verified from the upstream "
                "Checkstyle LICENSE file. SpotBugs is classified weak-copyleft "
                "from the upstream catalog's GNU Lesser General Public License "
                "v2.1."
            ),
        },
        "counts": {
            "in_source": len(entries),
            "eligible": len(eligible),
            "by_tier": dict(Counter(e["tier"] for e in eligible)),
            "by_license_status": dict(Counter(e["license_status"] for e in entries)),
            "by_license_class": dict(Counter(e["license_class"] for e in entries)),
            "by_measure": dict(Counter(m for e in entries for m in e["measures"])),
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
    # Writes into the package, which is where the catalog has to live to
    # reach an installed copy at all (D23). A build tool may climb to the
    # repository root; the runtime never can.
    out = (
        Path(__file__).resolve().parent.parent
        / "src" / "maintainability_audit" / "_assets" / "analyzer-catalog.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
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
