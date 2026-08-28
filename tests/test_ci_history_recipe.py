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

import re
import subprocess
from pathlib import Path

from maintainability_audit._scan_history import DEFAULT_HISTORY_PATH, read_history
from maintainability_audit.cli import main

ROOT = Path(__file__).resolve().parents[1]
ACTION = (ROOT / "action.yml").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "maintainability.yml").read_text(
    encoding="utf-8"
)


def test_the_action_can_be_told_to_record_history() -> None:
    """An input, off by default — recording is a write, and every write
    this tool performs is opt-in."""
    assert re.search(r"^  record-history:", ACTION, re.M), (
        "action.yml has no record-history input, so no CI run can accumulate "
        "the history ADR 009's trends and recurrence read"
    )
    assert not re.search(
        r"record-history:.*?default:\s*[\"']?true", ACTION, re.S | re.I
    ), "recording must be opt-in: it writes into the consumer's workspace"
    assert "--record-history" in ACTION, (
        "the input never reaches the CLI, so setting it changes nothing"
    )
    assert "inputs.record-history" in ACTION, (
        "the flag must be conditional on the input, not always on"
    )


def test_the_action_does_not_invent_a_second_history_file() -> None:
    """One path: the CLI default. A recipe naming its own file forks the
    history the moment someone runs the CLI by hand."""
    combined = ACTION + WORKFLOW
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
    restore = WORKFLOW.find("actions/cache/restore")
    audit = WORKFLOW.find("maintainability-agent@")
    save = WORKFLOW.find("actions/cache/save")

    assert restore != -1, "the workflow never restores the history cache"
    assert save != -1, "the workflow never saves the history cache"
    assert audit != -1
    assert restore < audit < save, "restore must precede the audit; save must follow it"

    save_block = WORKFLOW[save:]
    assert re.search(r"if:\s*always\(\)", WORKFLOW[WORKFLOW.rfind("- if:", 0, save):save + 80]), (
        "the save step skips on failure, so the runs that fail gates — the ones "
        "recurrence exists for — are exactly the ones forgotten"
    )
    assert DEFAULT_HISTORY_PATH in WORKFLOW[restore:audit]
    assert DEFAULT_HISTORY_PATH in save_block.split("upload-artifact", 1)[0]
    # Located by searching, not by counting characters from `save`. The
    # original read a fixed 200-character window, which broke the day
    # the `uses:` line above it grew a pinned commit SHA — the recipe
    # was unchanged and the test failed anyway (D41).
    save_key = re.search(r"^\s*key:.*$", save_block, re.MULTILINE)
    assert save_key, "the save step names no cache key"
    assert "${{" in save_key.group(0), (
        "the save key is fixed, so the cache can be written once and "
        "every later run silently keeps the first history"
    )
    # Rolling key lives on the save step; prefix restore-keys on restore.
    assert "restore-keys" in WORKFLOW[restore:audit], (
        "without restore-keys the rolling save key never matches on the next run"
    )
    assert re.search(r"record-history:\s*[\"']true[\"']", WORKFLOW), (
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
