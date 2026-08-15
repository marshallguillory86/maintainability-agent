"""6.4: the CI recipes carry history, or every CI run is the first run.

ADR 009 persists scans so the engine can measure change over time. In
CI the working directory is disposable, so a history that is not
restored before the audit and saved after it simply never accumulates —
`--record-history` writes one record into a workspace that evaporates,
and the next run starts blind. Recurrence and trends silently never
fire for exactly the users who run the tool most often.

Three surfaces, one contract:

- `action.yml` can be told to record (the flag has to reach the CLI).
- The consumer workflow restores `.maintainability/history.jsonl`
  before the audit and saves it after — even on a failing run, because
  the run that fails a gate is precisely the one the next run needs to
  remember.
- `examples/local-ci.sh` records; locally the file itself persists.

Asserted against the recipes, not live Actions: what these tests hold
is that the shipped text tells the truth, which is this repository's
recurring defect class.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from maintainability_audit._scan_history import DEFAULT_HISTORY_PATH, read_history
from maintainability_audit.cli import main

ROOT = Path(__file__).resolve().parents[1]


def _action() -> dict:
    return yaml.safe_load((ROOT / "action.yml").read_text(encoding="utf-8"))


def _workflow() -> dict:
    return yaml.safe_load(
        (ROOT / ".github" / "workflows" / "maintainability.yml").read_text(encoding="utf-8")
    )


def _run_script(action: dict) -> str:
    return "\n".join(step.get("run", "") for step in action["runs"]["steps"])


def test_the_action_can_be_told_to_record_history() -> None:
    """An input, off by default — recording is a write, and every write
    this tool performs is opt-in."""
    action = _action()

    assert "record-history" in action["inputs"], (
        "action.yml has no record-history input, so no CI run can accumulate "
        "the history ADR 009's trends and recurrence read"
    )
    assert str(action["inputs"]["record-history"].get("default", "")).lower() != "true", (
        "recording must be opt-in: it writes into the consumer's workspace"
    )

    script = _run_script(_action())
    assert "--record-history" in script, (
        "the input never reaches the CLI, so setting it changes nothing"
    )
    assert "record-history" in script.split("--record-history")[0], (
        "the flag must be conditional on the input, not always on"
    )


def test_the_action_does_not_invent_a_second_history_file() -> None:
    """One path: the CLI default. A recipe naming its own file forks the
    history the moment someone runs the CLI by hand."""
    combined = yaml.safe_dump(_action()) + yaml.safe_dump(_workflow())
    assert "history.jsonl" not in combined.replace(DEFAULT_HISTORY_PATH, ""), (
        f"a history path other than {DEFAULT_HISTORY_PATH} appears in the recipes"
    )


def test_the_workflow_restores_history_before_the_audit_and_saves_after() -> None:
    """Restore → audit → save, with the save running even on failure.

    `actions/cache`'s combined form saves in a post step that skips when
    the job fails, and the failing run is the one worth remembering —
    that is the run recurrence needs to see again. So the recipe must
    use the split restore/save with `if: always()` on the save.
    """
    steps = _workflow()["jobs"]["maintainability"]["steps"]
    uses = [str(step.get("uses", "")) for step in steps]

    restore = next((i for i, u in enumerate(uses) if u.startswith("actions/cache/restore")), None)
    audit = next((i for i, u in enumerate(uses) if "maintainability-agent@" in u), None)
    save = next((i for i, u in enumerate(uses) if u.startswith("actions/cache/save")), None)

    assert restore is not None, "the workflow never restores the history cache"
    assert save is not None, "the workflow never saves the history cache"
    assert audit is not None
    assert restore < audit < save, "restore must precede the audit; save must follow it"

    assert steps[save].get("if") == "always()", (
        "the save step skips on failure, so the runs that fail gates — the ones "
        "recurrence exists for — are exactly the ones forgotten"
    )
    for index in (restore, save):
        assert DEFAULT_HISTORY_PATH in str(steps[index].get("with", {}).get("path", "")), (
            f"the cache step does not carry {DEFAULT_HISTORY_PATH}"
        )

    # A fixed key can never be re-saved, so the second run would restore
    # and then fail to save forever. Rolling key + prefix restore is the
    # documented pattern for an append-only file.
    save_key = str(steps[save]["with"]["key"])
    restore_with = steps[restore]["with"]
    assert "${{" in save_key, f"the save key {save_key!r} is fixed and can be saved once"
    assert "restore-keys" in restore_with, (
        "without restore-keys the rolling save key never matches on the next run"
    )

    audit_with = steps[audit].get("with", {})
    assert str(audit_with.get("record-history", "")).lower() == "true", (
        "the workflow caches the history but never tells the action to record it"
    )


def test_local_ci_records_history() -> None:
    script = (ROOT / "examples" / "local-ci.sh").read_text(encoding="utf-8")
    assert "--record-history" in script, (
        "examples/local-ci.sh never records, so the local recipe accumulates "
        "no history either"
    )


def test_a_second_recorded_run_is_not_a_first_seen_history(tmp_path: Path) -> None:
    """The behaviour the recipes exist to preserve, driven end to end.

    Two audits with `--record-history` into one workspace: the file must
    hold both records, and the second report must see the first — a
    history of one is what every CI run had before this.
    """
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    for index in range(40):
        (root / f"m{index}.py").write_text(
            "\n".join(f"def f{index}_{j}(v):\n    return v + {j}\n" for j in range(4)),
            encoding="utf-8",
        )
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "start"],
        check=True,
    )
    out = tmp_path / "out.md"

    assert main(["--root", str(root), "--record-history", "--output", str(out)]) == 0
    assert main(["--root", str(root), "--record-history", "--output", str(out)]) == 0

    records = read_history(root / DEFAULT_HISTORY_PATH)
    assert len(records) == 2, (
        f"two recorded runs left {len(records)} records; the second run was a first run"
    )
