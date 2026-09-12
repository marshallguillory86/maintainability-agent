"""`-` means stdout, and the two outputs that cannot honour it say so.

Found by running the demo tree's own command as a reader would.
`--prompt-output -` created a file **named `-`** in the working
directory: the pipeline came back empty, the prompt sat on disk under a
name the reader's shell would fight them over, and nothing said so. Every
rendered output had the same hole, because each one went straight to
`Path(name)`.

The convention is not decoration here. The product is a prompt you pipe
into a coding agent, so `... --prompt-output - | claude` is the shape of
the five-minute path, and it silently produced nothing.

Two outputs still refuse `-`, by name and with a reason: a baseline is
read back by a later run and an HTML report is opened rather than piped.
Refusing is the point -- the failure being fixed is an output that
accepted `-` and did something else.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _tree(root: Path) -> Path:
    """A repository with one finding, so there is a prompt to render."""
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# t\n", encoding="utf-8")
    body = "".join(f"    if x == {n}:\n        return {n}\n" for n in range(40))
    (root / "a.py").write_text(f"def f(x):\n{body}    return -1\n", encoding="utf-8")
    return root


def _run(root: Path, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "maintainability_audit", "--root", str(root), *flags],
        cwd=root, capture_output=True, text=True, check=False, timeout=600,
    )


@pytest.mark.parametrize(
    ("flag", "marker"),
    [
        ("--prompt-output", "# AI Remediation Prompt"),
        ("--comment-output", "Maintainability"),
        ("--hostile-prompt-output", "audit"),
    ],
)
def test_a_rendered_output_reaches_stdout_and_writes_no_file(
    tmp_path: Path, flag: str, marker: str,
) -> None:
    """The fix: `-` is a stream, not a filename.

    Fails at base -- the text went into a file called `-` and stdout
    carried the report instead.
    """
    root = _tree(tmp_path / "tree")
    done = _run(root, flag, "-")

    assert marker in done.stdout, (
        f"{flag} - put nothing recognisable on stdout; got:\n{done.stdout[:400]}"
    )
    assert not (root / "-").exists(), (
        f"{flag} - created a file named '-' instead of writing to the stream"
    )


def test_sarif_reaches_stdout_as_parseable_json(tmp_path: Path) -> None:
    """A machine-readable output on a pipe has to still parse.

    Worth its own case: the report is suppressed precisely so this one
    can be piped into `jq` without a Markdown preamble in front of it.
    """
    root = _tree(tmp_path / "sarif")
    done = _run(root, "--sarif-output", "-")

    payload = json.loads(done.stdout)
    assert payload.get("runs"), f"stdout was not a SARIF document:\n{done.stdout[:300]}"


def test_the_report_does_not_interleave_with_the_piped_artifact(tmp_path: Path) -> None:
    """The trap a naive fix walks into, and the reason `_claims_stdout` exists.

    With no `--output`, the report prints to stdout. Sending the prompt
    there as well would have handed a reader a prompt with a full report
    stapled to its front -- worse than the file named `-`, because it
    looks like it worked.
    """
    root = _tree(tmp_path / "solo")
    done = _run(root, "--prompt-output", "-")

    assert "# AI Remediation Prompt" in done.stdout
    assert "# Maintainability CI Report" not in done.stdout, (
        "the report interleaved with the artifact being piped:\n"
        f"{done.stdout[:400]}"
    )


def test_an_explicit_output_dash_still_prints_the_report(tmp_path: Path) -> None:
    """Suppression is about *implicit* printing, not about refusing the ask."""
    root = _tree(tmp_path / "both")
    done = _run(root, "--output", "-")

    assert "# Maintainability CI Report" in done.stdout


@pytest.mark.parametrize("flag", ["--write-baseline", "--html-output"])
def test_the_outputs_that_cannot_stream_refuse_by_name(tmp_path: Path, flag: str) -> None:
    """Refused with a reason, never accepted and quietly turned into a file.

    This is the whole defect restated: an output that takes `-` and does
    something else is worse than one that says it cannot.
    """
    root = _tree(tmp_path / "refuse")
    done = _run(root, flag, "-")

    assert done.returncode != 0, f"{flag} - was accepted; it cannot be a stream"
    assert "cannot be written to stdout" in done.stderr, (
        f"{flag} - failed without explaining why:\n{done.stderr[-400:]}"
    )
    assert flag in done.stderr, f"the refusal did not name {flag}"
    assert not (root / "-").exists(), f"{flag} - still created a file named '-'"
