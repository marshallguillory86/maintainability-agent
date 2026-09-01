"""D7/D8: MCP baseline adoption and one requested presentation per call."""

from __future__ import annotations

import asyncio
import inspect
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
from _mcp_fixtures import _drop_generated_line

from maintainability_audit._scan_history import DEFAULT_HISTORY_PATH, read_history
from maintainability_audit.baseline import BASELINE_VERSION
from maintainability_audit.cli import main
from maintainability_audit.config import CONFIG_FILENAME
from maintainability_audit.mcp_server import (
    SERVER_INSTRUCTIONS,
    PathNotAllowed,
    audit_repository,
    create_server,
    server_info,
)

DEFAULT_BASELINE_PATH = Path(".maintainability/baseline.json")


def _large_function(name: str) -> str:
    body = "".join(f"    value_{line} = value + {line}\n" for line in range(90))
    return f"def {name}(value):\n{body}    return value\n"


def _repo(base: Path) -> Path:
    root = base / "repo"
    root.mkdir(parents=True)
    (root / CONFIG_FILENAME).write_text(
        json.dumps({
            "version": 1,
            "analyzers": {"run": False},
            "hard_gates": {"fail_on_function_failures": True},
        }),
        encoding="utf-8",
    )
    (root / ".gitignore").write_text(".maintainability/\n", encoding="utf-8")
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (root / "hot.py").write_text(_large_function("huge"), encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    _commit(root, "fixture")
    return root


def _commit(root: Path, message: str) -> None:
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        [
            "git", "-C", str(root), "-c", "user.email=t@t",
            "-c", "user.name=t", "commit", "-qm", message,
        ],
        check=True,
    )


def _audit(root: Path, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("format", "json")
    kwargs.setdefault("record_history", False)
    return audit_repository(str(root), roots=(root.parent.resolve(),), **kwargs)


def _report_resource(root: Path) -> str:
    server = create_server(roots=(root.parent.resolve(),))
    resources = asyncio.run(server.list_resources())
    template = next(
        resource
        for resource in resources
        if resource.name == "maintainability-report-template"
    )
    uri = str(template.uri).replace("{repository_root}", str(root)).replace(
        "{root}", str(root),
    )
    contents = asyncio.run(server.read_resource(uri))
    return "".join(item.content for item in contents)


def test_registered_audit_tool_exposes_baseline_and_prompt_controls(
    tmp_path: Path,
) -> None:
    """The public MCP schema, not only the Python helper, carries D7/D8 controls."""
    from mcp import Client

    server = create_server(roots=(tmp_path.resolve(),))
    tools = asyncio.run(server.list_tools())
    audit = next(tool for tool in tools if tool.name == "audit_repository")
    properties = audit.input_schema["properties"]

    assert properties["baseline_path"]["default"] is None
    assert properties["write_baseline"]["default"] is False
    assert properties["include_prompt"]["default"] is True

    root = _repo(tmp_path)
    (root / "state").mkdir()

    async def exercise() -> dict[str, Any]:
        async with Client(server) as client:
            result = await client.call_tool(
                "audit_repository",
                {
                    "repository_root": str(root),
                    "action": "run",
                    "baseline_path": "state/from-mcp.json",
                    "write_baseline": True,
                    "include_prompt": False,
                    "record_history": False,
                    "format": "json",
                },
            )
            assert not result.is_error
            return result.structured_content

    result = asyncio.run(exercise())
    assert (root / "state/from-mcp.json").is_file()
    assert "report" in result and "remediation_prompt" not in result


def test_mcp_baseline_round_trip_survives_git_mv_and_names_only_new_findings(
    tmp_path: Path,
) -> None:
    """Baseline v3 follows a rename while a genuinely new finding stays new."""
    signature = inspect.signature(audit_repository).parameters
    assert signature["baseline_path"].default is None
    assert signature["write_baseline"].default is False
    root = _repo(tmp_path)

    written = _audit(root, write_baseline=True)

    baseline = root / DEFAULT_BASELINE_PATH
    payload = json.loads(baseline.read_text(encoding="utf-8"))
    assert payload["version"] == BASELINE_VERSION == 3
    assert payload["commit"] == written["report"]["git_commit"]
    assert payload["identities"]

    subprocess.run(["git", "-C", str(root), "mv", "hot.py", "moved.py"], check=True)
    _commit(root, "rename existing finding")
    moved = _audit(root)
    assert moved["new_findings"] == [], "git mv turned an existing finding into a new one"
    assert moved["gate_passed"] is False, "baseline suppression changed hard-gate truth"

    (root / "new.py").write_text(_large_function("new_huge"), encoding="utf-8")
    _commit(root, "add a genuinely new finding")
    changed = _audit(root)

    assert changed["new_findings"] == sorted(changed["new_findings"])
    assert any("new.py" in fingerprint for fingerprint in changed["new_findings"])


def test_mcp_baseline_defaults_inside_root_and_rejects_escape(tmp_path: Path) -> None:
    """The standing default and an explicit path share the repository boundary."""
    default_root = _repo(tmp_path / "default")
    _audit(default_root, write_baseline=True)
    assert (default_root / DEFAULT_BASELINE_PATH).is_file()

    custom_root = _repo(tmp_path / "custom")
    (custom_root / "state").mkdir()
    _audit(custom_root, baseline_path="state/known.json", write_baseline=True)
    assert (custom_root / "state/known.json").is_file()

    with pytest.raises(PathNotAllowed):
        _audit(
            custom_root,
            baseline_path=str(tmp_path / "outside.json"),
            write_baseline=True,
        )


@pytest.mark.parametrize(
    ("format_name", "presentation_keys"),
    [
        ("json", {"report"}),
        ("chat", {"report_markdown"}),
        ("markdown", {"report_markdown"}),
        ("html", {"report_html", "report_markdown"}),
    ],
)
def test_requested_format_governs_the_mcp_payload(
    tmp_path: Path,
    format_name: str,
    presentation_keys: set[str],
) -> None:
    """One request returns only its selected report skin plus the default prompt."""
    root = _repo(tmp_path)

    result = audit_repository(
        str(root),
        format=format_name,
        record_history=False,
        roots=(tmp_path.resolve(),),
    )

    always = {
        "agent", "agent_version", "source_commit", "worktree_dirty",
        # Two keys, deliberately: `analyzers_run` is the outcome and
        # `analyzers_requested` the decision behind it. One key carrying
        # both meanings reported a pool as run when none had (D24).
        "gate_passed", "analyzers_run", "analyzers_requested",
        # Stated on every reply so "did this produce a result?" is a key
        # to read, not the absence of one (D26/D27).
        "audit_ran",
        "format", "remediation_prompt",
    }
    assert set(result) == always | presentation_keys
    if "report" in result:
        assert isinstance(result["report"], dict)
    for key in presentation_keys - {"report"}:
        assert isinstance(result[key], str) and result[key]


def test_suppressing_prompt_records_no_targeted_advice(tmp_path: Path) -> None:
    """Advice omitted from the payload is not remembered as advice delivered."""
    root = _repo(tmp_path)

    result = audit_repository(
        str(root),
        format="json",
        include_prompt=False,
        record_history=True,
        roots=(tmp_path.resolve(),),
    )

    assert "remediation_prompt" not in result
    records = read_history(root / DEFAULT_HISTORY_PATH)
    assert len(records) == 1
    assert records[0].targeted == ()


def test_report_resource_matches_cli_over_stored_history_without_appending(
    tmp_path: Path,
) -> None:
    """The resource reads the CLI's series but never adds another scan to it."""
    root = _repo(tmp_path)
    output = tmp_path / "cli-report.md"
    assert main([
        "--root", str(root),
        "--no-analyzers",
        "--record-history",
        "--format", "markdown",
        "--output", str(output),
    ]) == 0
    history = root / DEFAULT_HISTORY_PATH
    stored = history.read_bytes()

    served = _report_resource(root)

    # Parity but for the run date (G) — a disclosed determinism exception (P1)
    # that two independently timed renders legitimately stamp differently.
    assert _drop_generated_line(served) == _drop_generated_line(
        output.read_text(encoding="utf-8").removesuffix("\n"))
    assert history.read_bytes() == stored, "reading the resource appended a scan"


def _sentence_with(text: str, token: str) -> str:
    normalized = " ".join(text.split())
    return next(
        sentence
        for sentence in re.split(r"(?<=[.!?])\s+", normalized)
        if token in sentence
    )


def test_server_discloses_five_artifacts_and_the_history_tristate(tmp_path: Path) -> None:
    """Baseline joins the bounded writes; history consent remains explicit and tri-state."""
    info = server_info((tmp_path.resolve(),))
    disclosure = f"{SERVER_INSTRUCTIONS}\n{json.dumps(info, sort_keys=True)}".lower()

    assert len(info["writes"]) == 5
    assert "baseline" in disclosure and str(DEFAULT_BASELINE_PATH) in disclosure
    assert "source" in " ".join(info["never_writes"]).lower()
    assert "report" in " ".join(info["never_writes"]).lower()

    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(
        encoding="utf-8",
    )
    for surface in (SERVER_INSTRUCTIONS, readme):
        sentence = _sentence_with(surface, "record_history").lower()
        assert "existing" in sentence and "history" in sentence
        assert "consent" in sentence or "persisted" in sentence
        assert "true" in sentence and "false" in sentence
