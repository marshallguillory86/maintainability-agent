"""D35: the tree being audited does not decide what the host installs.

`product-intent.md` P1 separates analysis from acquisition and says a
**user** enables `analyzers.acquire_tools`. `load_config` says a
repository always beats a person — correct for thresholds and
exclusions, since the repository knows its own code, and exactly wrong
here. An audit pointed out that four words in a pull request otherwise
make the host run `npx --yes` on an unpinned package, honouring the
tree's own `.npmrc`.

License policy already had the right shape: deny wins, and no
repository overrides an organisation's prohibition. Acquisition was the
one decision still taking the audited tree's word for it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from maintainability_audit._user_config import user_config_path
from maintainability_audit.config import acquisition_permitted

SCHEMA = Path(__file__).resolve().parents[1] / "maintainability-agent.schema.json"


@pytest.fixture(autouse=True)
def _isolated_user_tier(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Never read the developer's real acquisition choice."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))


def _write_user_tier(payload: dict) -> None:
    path = user_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_no_configuration_means_no_acquisition() -> None:
    """The default P1 promises: off unless chosen."""
    assert acquisition_permitted() is False


def test_the_user_tier_can_enable_acquisition() -> None:
    """Refusing everyone would not be a fix, it would be a removal."""
    _write_user_tier({"analyzers": {"acquire_tools": True}})
    assert acquisition_permitted() is True


def test_a_repository_cannot_enable_acquisition(tmp_path: Path) -> None:
    """The inversion itself, at the seam that decides.

    Checked through `acquisition_permitted` rather than a full audit,
    because the property is about *where the answer comes from*: the
    merged config carries the repository's value and this function must
    not consult it.
    """
    from maintainability_audit.config import load_config

    repo_config = tmp_path / "maintainability-agent.json"
    repo_config.write_text(
        json.dumps({"version": 1, "analyzers": {"run": True, "acquire_tools": True}}),
        encoding="utf-8",
    )

    merged = load_config(str(repo_config))
    assert merged["analyzers"]["acquire_tools"] is True, (
        "the merged config no longer carries the repository's value, so "
        "this test would pass for the wrong reason"
    )
    assert acquisition_permitted() is False, (
        "a repository under audit enabled tool acquisition on the host"
    )


def test_a_repository_cannot_revoke_a_users_choice(tmp_path: Path) -> None:
    """Symmetry, so the rule is 'the user decides', not 'the answer is no'."""
    from maintainability_audit.config import load_config

    _write_user_tier({"analyzers": {"acquire_tools": True}})
    repo_config = tmp_path / "maintainability-agent.json"
    repo_config.write_text(
        json.dumps({"version": 1, "analyzers": {"acquire_tools": False}}),
        encoding="utf-8",
    )
    load_config(str(repo_config))

    assert acquisition_permitted() is True


def test_the_schema_declares_the_key_the_runtime_reads() -> None:
    """A contract that forbids what the code obeys is worse than silence.

    `analyzers` is `additionalProperties: false` and did not list
    `acquire_tools`, so the published schema said the key was illegal
    while the runtime honoured it — the schema is never loaded, so
    nothing caught the contradiction.
    """
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    analyzers = schema["properties"]["analyzers"]
    assert analyzers["additionalProperties"] is False
    declared = analyzers["properties"]
    assert "acquire_tools" in declared, (
        "the schema forbids a key the runtime reads"
    )
    assert "user" in declared["acquire_tools"]["description"].lower(), (
        "the schema does not say whose decision this is"
    )
