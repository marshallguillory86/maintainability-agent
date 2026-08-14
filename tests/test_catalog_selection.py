"""Selecting analyzers by intent — ADR 006.

A user answers *what do you want examined*, *how deep* and *what may we
legally run*, and never names a tool. The pool is the intersection.

The precedence rule these tests pin hardest: **every deny wins, including over
an explicit allow.** An organization's prohibition must not be overridable by
a per-repository opt-in, or the licence policy is advisory rather than
enforced.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from maintainability_audit._catalog import (
    CONCERNS,
    DEPTH_ORDER,
    LICENSE_POLICIES,
    PolicyError,
    load_catalog,
    resolve_pool,
    settings_from,
)

ROOT = Path(__file__).resolve().parent.parent


def _config(**analyzers) -> dict:
    return {"version": 1, "analyzers": analyzers}


def _slugs(config: dict) -> set[str]:
    pool, _ = resolve_pool(config)
    return {tool["slug"] for tool in pool}


def test_the_shipped_config_resolves_to_a_usable_pool() -> None:
    """A shipped default that selects nothing would be a dead feature."""
    config = json.loads((ROOT / "maintainability-agent.json").read_text(encoding="utf-8"))
    pool, decisions = resolve_pool(config)

    assert pool, "the default configuration must select at least one tool"
    assert len(decisions) == len(load_catalog()), "every tool gets a recorded decision"


def test_every_exclusion_carries_a_reason() -> None:
    """"Why didn't it run my linter?" is the first question anyone asks."""
    _, decisions = resolve_pool(_config())

    for decision in decisions:
        assert decision.reason, f"{decision.slug} was decided without a stated reason"


def test_deny_by_name_beats_an_explicit_allow() -> None:
    """The precedence rule, stated as a test because it is the one that matters.

    A per-repository allow must not be able to reinstate a tool the
    organization has prohibited.
    """
    both = _config(allow_tools=["lizard"], deny_tools=["lizard"])
    assert "lizard" not in _slugs(both)


def test_deny_by_class_beats_an_explicit_allow() -> None:
    allowed = _config(license_policy="copyleft-any", allow_tools=["pylint"])
    assert "pylint" in _slugs(allowed)

    denied = _config(
        license_policy="copyleft-any",
        allow_tools=["pylint"],
        deny_license_classes=["strong-copyleft"],
    )
    assert "pylint" not in _slugs(denied)


def test_a_stricter_licence_policy_never_widens_the_pool() -> None:
    """Monotonic by construction, swept over the policy ladder.

    A policy that admitted something its stricter neighbour did not would
    make the ladder meaningless.
    """
    ladder = ["permissive", "copyleft-weak", "copyleft-any", "commercial-free-tier", "unverified"]
    pools = [_slugs(_config(license_policy=policy, depth="all")) for policy in ladder]

    for stricter, looser in zip(pools, pools[1:], strict=False):
        assert stricter <= looser, "a looser policy dropped a tool the stricter one allowed"


def test_a_deeper_depth_never_narrows_the_pool() -> None:
    pools = [_slugs(_config(depth=depth, license_policy="unverified")) for depth in DEPTH_ORDER]

    for shallower, deeper in zip(pools, pools[1:], strict=False):
        assert shallower <= deeper, "a deeper tier dropped a tool a shallower one ran"


@pytest.mark.parametrize("concern", CONCERNS)
def test_selecting_one_concern_only_admits_tools_that_measure_it(concern: str) -> None:
    """Swept over the vocabulary, so a concern added later is covered."""
    pool, _ = resolve_pool(_config(concerns=[concern], depth="all", license_policy="unverified"))

    for tool in pool:
        assert concern in tool["measures"], (
            f"{tool['slug']} was selected for {concern} but measures {tool['measures']}"
        )


def test_security_tools_are_never_selected_by_default() -> None:
    """That work belongs to secure-code-agent.

    Two tools disagreeing about the same repository is worse than one
    tool declining to answer.
    """
    pool, _ = resolve_pool(_config(depth="all", license_policy="unverified"))

    for tool in pool:
        assert not tool["security_only"]
        assert "security" not in tool["upstream_tags"]


def test_a_tool_without_an_adapter_is_never_selected() -> None:
    """Catalogued is not the same as invokable.

    The inventory is a fact about the world; an adapter is work someone
    has to do. Selecting an entry with no adapter would overstate what ran.
    """
    pool, _ = resolve_pool(_config(depth="all", license_policy="unverified"))

    for tool in pool:
        assert tool["adapter"] == "implemented"


@pytest.mark.parametrize(
    "block,fragment",
    [
        ({"depth": "extreme"}, "unknown depth"),
        ({"license_policy": "whatever"}, "unknown license_policy"),
        ({"concerns": ["vibes"]}, "unknown concerns"),
    ],
    ids=["depth", "policy", "concern"],
)
def test_an_unrecognized_setting_raises_rather_than_defaulting(
    block: dict, fragment: str
) -> None:
    """Defaulting would run a different pool than the operator asked for,
    and the report would attribute the result to their choice."""
    with pytest.raises(PolicyError, match=fragment):
        settings_from(_config(**block))


@pytest.mark.parametrize("field", ["allow_tools", "deny_tools"])
def test_a_misspelled_slug_is_an_error_not_a_no_op(field: str) -> None:
    """A silent no-op here means a denial that never took effect."""
    with pytest.raises(PolicyError, match="absent from the catalog"):
        resolve_pool(_config(**{field: ["pylnit"]}))


def test_the_defaults_alone_are_a_valid_configuration() -> None:
    """An empty analyzers block must behave, since most configs omit it."""
    settings = settings_from({"version": 1})

    assert settings["depth"] in DEPTH_ORDER
    assert settings["license_policy"] in LICENSE_POLICIES
    assert settings["deny_concerns"] == ["security"]


def test_the_pool_document_states_the_catalogs_own_counts() -> None:
    """docs/analyzer-pool.md is prose over data, and prose drifts.

    Every count on that page had drifted from `analyzer-catalog.json`:
    759 tools against 760, 464 permissive against 465, 444 eligible
    against 446, ten adapters against sixteen. Each number was true when
    written and silently wrong afterwards, which is worse than never
    having stated it — a reader has no way to tell a stale figure from a
    current one.

    Regenerating the catalog now fails this test until the page is
    updated with it.
    """
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    counts = json.loads(
        (root / "data" / "analyzer-catalog.json").read_text(encoding="utf-8"))["counts"]
    text = (root / "docs" / "analyzer-pool.md").read_text(encoding="utf-8")

    expected = {
        "total tools": f"**{counts['in_source']} tools.**",
        "eligible": f"**{counts['eligible']} tools** are eligible",
        "adapters": f"**{counts['adapters_implemented']} tools have adapters**",
        **{
            f"license class {name}": f"| `{name}` | {count} |"
            for name, count in counts["by_license_class"].items()
        },
    }
    missing = sorted(label for label, phrase in expected.items() if phrase not in text)

    assert not missing, (
        f"docs/analyzer-pool.md no longer states the catalog's counts for: {missing}. "
        "Regenerate the page from data/analyzer-catalog.json."
    )

    # The same figures are quoted elsewhere and drifted there too. Each
    # page is checked for the counts it actually states, not for all of
    # them — docs/README.md names the catalog's size and nothing else.
    also_quoting = {
        "README.md": (counts["in_source"],),
        "target-architecture.md": (counts["in_source"], counts["eligible"]),
    }
    for name, values in also_quoting.items():
        page = (root / "docs" / name).read_text(encoding="utf-8")
        stale = [str(value) for value in values if str(value) not in page]
        assert not stale, (
            f"docs/{name} quotes catalog counts but not the current {stale}; "
            "update it from data/analyzer-catalog.json"
        )
