"""What setup writes, the published schema accepts (D191).

`maintainability-agent.schema.json` is the contract an operator points
their editor and their CI at. It sets `additionalProperties: false`, and
it did not describe `presentation`, `history`, `test_execution` or
`economic_context` — four blocks **this tool's own first-run setup
writes**.

So the tool produced a configuration its own published schema rejected.
Nobody saw it because the fixture it was validated against was this
repository's config, which predated setup and carried none of those
blocks. Completing setup anywhere else produced a file an editor marks
invalid on every line of it.

The gate is the round trip, not a list: run `apply_answers` and validate
what lands on disk. A settings block added without a schema entry then
fails here rather than in somebody's editor.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "maintainability-agent.schema.json").read_text(encoding="utf-8"))


def _validate(config: dict) -> None:
    import jsonschema

    jsonschema.validate(config, SCHEMA)


def _written(tmp_path: Path, answers: dict[str, str]) -> dict:
    from maintainability_audit._mcp_setup import apply_answers

    apply_answers(tmp_path, answers)
    return json.loads(
        (tmp_path / "maintainability-agent.json").read_text(encoding="utf-8")
    )


_FIRST_STAGE = {
    "run_pool": "yes",
    "depth": "heavy",
    "license_policy": "copyleft-any",
    "economics": "include",
    "run_tests": "yes",
    "default_format": "html",
    "record_scan_history": "yes",
}


def test_a_completed_setup_validates_against_the_published_schema(tmp_path) -> None:
    """The round trip. Written by the tool, judged by the tool's contract."""
    _validate(_written(tmp_path, _FIRST_STAGE))


def test_every_block_setup_writes_is_described_by_the_schema(tmp_path) -> None:
    """Named explicitly, so the failure says which block is undescribed.

    `additionalProperties: false` already fails the test above, but its
    message names the keys without saying they are ours.
    """
    written = _written(tmp_path, _FIRST_STAGE)

    undescribed = sorted(set(written) - set(SCHEMA["properties"]))

    assert not undescribed, (
        f"first-run setup writes blocks the published schema does not "
        f"describe: {undescribed}. The tool would produce a configuration "
        "its own schema rejects."
    )


@pytest.mark.parametrize("answers", [
    pytest.param({**_FIRST_STAGE, "economics": "skip"}, id="economics skipped"),
    pytest.param({**_FIRST_STAGE, "run_tests": "no"}, id="suite declined"),
    pytest.param({**_FIRST_STAGE, "run_pool": "no"}, id="pool declined"),
    pytest.param({**_FIRST_STAGE, "default_format": "chat"}, id="chat skin"),
])
def test_every_answer_combination_writes_a_valid_config(tmp_path, answers) -> None:
    """A declined option must not write a shape the schema refuses either.

    One happy-path fixture is how the original gap survived: the config it
    validated simply did not contain the blocks.
    """
    _validate(_written(tmp_path, answers))


def test_the_staged_second_answers_also_validate(tmp_path) -> None:
    """The labor rates and the test command land in the same file.

    They arrive on a later call and merge, so they are a second way to
    reach a shape the schema has to accept.
    """
    from maintainability_audit._mcp_setup import apply_answers

    apply_answers(tmp_path, _FIRST_STAGE)
    apply_answers(tmp_path, {"labor_low": 90, "labor_base": 140, "labor_high": 210})
    apply_answers(tmp_path, {"test_command": "pytest -q"})

    _validate(json.loads(
        (tmp_path / "maintainability-agent.json").read_text(encoding="utf-8")
    ))

