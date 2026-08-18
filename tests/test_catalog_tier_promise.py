"""A verified analyzer tier is a promise that a runnable adapter ships."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from maintainability_audit._generic import declared_adapter
from maintainability_audit._tool_adapters import adapter_for

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "analyzer-catalog.json"
POOL_DOC = ROOT / "docs" / "analyzer-pool.md"
CATALOG_PRODUCER = ROOT / "tools" / "build_catalog.py"
DEPTHS = ("baseline", "moderate", "heavy")


def _catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _has_adapter(slug: str) -> bool:
    return adapter_for(slug) is not None or declared_adapter(slug) is not None


def _literal_assignment(path: Path, name: str) -> dict[str, str]:
    """Read a producer data map without importing its dev-only YAML dependency."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            value = ast.literal_eval(node.value)
            assert isinstance(value, dict)
            return value
    raise AssertionError(f"{name} is missing from {path.relative_to(ROOT)}")


def test_every_verified_tier_is_backed_by_a_shipped_adapter() -> None:
    """Below ``all`` means installed, run, parsed, and invokable here."""
    tools = _catalog()["tools"]
    verified = {tool["slug"] for tool in tools if tool["tier"] != "all"}
    adapted = {tool["slug"] for tool in tools if _has_adapter(tool["slug"])}

    assert verified == adapted, (
        "tier below 'all' must be exactly the runnable adapter set; "
        f"tier-only={sorted(verified - adapted)}, adapter-only={sorted(adapted - verified)}"
    )

    # Decisions 3 and 9 keep this hard promise at the current fifteen adapters.
    # The set itself is derived from the catalog so a sixteenth adapter must
    # update this explicit product count rather than silently changing it.
    assert len(verified) == len(adapted) == 15


def test_catalog_producer_tiers_are_exactly_the_shipped_adapter_set() -> None:
    """Regeneration must preserve the same tier-to-adapter promise as the artifact."""
    producer_tiers = set(_literal_assignment(CATALOG_PRODUCER, "VERIFIED_TIERS"))
    adapted = {
        tool["slug"]
        for tool in _catalog()["tools"]
        if _has_adapter(tool["slug"])
    }

    assert producer_tiers == adapted, (
        "the catalog producer would regenerate a tier that contradicts shipped adapters; "
        f"tier-only={sorted(producer_tiers - adapted)}, "
        f"adapter-only={sorted(adapted - producer_tiers)}"
    )


def test_catalog_tier_counts_are_internally_consistent() -> None:
    """The checked-in summary must change with the tool records it summarizes."""
    catalog = _catalog()
    eligible = [
        tool
        for tool in catalog["tools"]
        if tool["license_class"] in {"permissive", "weak-copyleft", "strong-copyleft"}
        and not tool["deprecated"]
        and tool["languages"]
        and not tool["security_only"]
    ]
    expected = {
        tier: sum(tool["tier"] == tier for tool in eligible)
        for tier in ("all", *DEPTHS)
        if any(tool["tier"] == tier for tool in eligible)
    }

    assert catalog["counts"]["by_tier"] == expected


def test_depth_table_is_derived_from_the_catalog_tiers() -> None:
    """Depth is cumulative; the prose table must not preserve stale counts."""
    tools = _catalog()["tools"]
    text = POOL_DOC.read_text(encoding="utf-8")
    section = text.split("### Depth", maxsplit=1)[1].split("### License policy", maxsplit=1)[0]
    stated = {
        match.group("tier"): int(match.group("count"))
        for match in re.finditer(
            r"^\| `(?P<tier>baseline|moderate|heavy)` \| (?P<count>\d+) \|",
            section,
            flags=re.MULTILINE,
        )
    }
    expected = {
        depth: sum(
            tool["tier"] in DEPTHS[: DEPTHS.index(depth) + 1]
            for tool in tools
        )
        for depth in DEPTHS
    }

    assert stated == expected
