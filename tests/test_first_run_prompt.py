"""6.1: the interactive first-run prompt, held to the release-plan exit.

The exit condition is one sentence: *"Prompts only on a TTY with no
config; never in CI; the answer persists."* Today no sentence of it is
true — `analyzers.prompt_when_interactive` is `True` in `DEFAULTS` and in
this repository's own config, and nothing anywhere reads it. The key is
a promise stored in a file.

Three tests carry the exit condition's three clauses, and the first
fails on today's tree because nothing prompts. The other two pin the
behaviour that must *survive* the implementation: CI never blocks, and
an existing config is always respected. A first-run prompt that fires in
a pipeline is a hung build, which is worse than no prompt at all.

No new flags are asserted. `--depth` / `--license-policy` exist on
`tools/resolve_pool.py` only, and the audit CLI's non-interactive path
is the config file itself — the same file the prompt writes, which is
what makes the answer persist.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from maintainability_audit.cli import main
from maintainability_audit.config import CONFIG_FILENAME

# The selectors the prompt must ask about, in the catalog's own
# vocabulary — `DEPTH_ORDER` is ('baseline', 'moderate', 'heavy', 'all')
# and the policies are `LICENSE_POLICIES`' keys; an invented value here
# would test a prompt the catalog rejects. Answers chosen to differ from
# every default, so persistence is provable: a written file holding the
# defaults could have come from anywhere.
ANSWERS = {"depth": "heavy", "license_policy": "copyleft-weak"}


def _repo(tmp_path: Path) -> Path:
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
    return root


def _tty(monkeypatch: pytest.MonkeyPatch, answer: bool) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: answer, raising=False)


def _scripted_input(monkeypatch: pytest.MonkeyPatch, asked: list[str]):
    """Answer depth/policy questions from ANSWERS, recording each prompt."""

    def respond(prompt: str = "") -> str:
        asked.append(prompt)
        lowered = prompt.lower()
        if "depth" in lowered:
            return ANSWERS["depth"]
        if "policy" in lowered or "licen" in lowered:
            return ANSWERS["license_policy"]
        # Concerns or anything else: accept the offered default.
        return ""

    monkeypatch.setattr("builtins.input", respond)


def _forbidden_input(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(prompt: str = "") -> str:
        raise AssertionError(f"the CLI prompted on a non-TTY: {prompt!r}")

    monkeypatch.setattr("builtins.input", explode)


def test_first_run_on_a_tty_asks_and_the_answer_persists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Clause one and clause three: prompts on a TTY, and only once.

    The answers land in `maintainability-agent.json` at the repo root —
    the same file `discovered_config` already reads — so persistence is
    not a second mechanism, and the second run finds a config and asks
    nothing (clause: "so a second run does not ask again").
    """
    root = _repo(tmp_path)
    _tty(monkeypatch, True)
    asked: list[str] = []
    _scripted_input(monkeypatch, asked)

    assert main(["--root", str(root)]) == 0

    lowered = " ".join(asked).lower()
    assert asked, (
        "prompt_when_interactive is true, stdin is a TTY and no config exists, "
        "and the CLI asked nothing — the key is stored and never read (6.1)"
    )
    assert "depth" in lowered, f"the prompt never asked for depth: {asked}"
    assert "policy" in lowered or "licen" in lowered, (
        f"the prompt never asked for the license policy: {asked}"
    )

    written = root / CONFIG_FILENAME
    assert written.exists(), "the answers did not persist to the repo-root config"
    analyzers = json.loads(written.read_text(encoding="utf-8")).get("analyzers", {})
    assert analyzers.get("depth") == ANSWERS["depth"]
    assert analyzers.get("license_policy") == ANSWERS["license_policy"]

    # The second run has a config, so even on a TTY it must not ask.
    asked.clear()
    assert main(["--root", str(root)]) == 0
    assert not asked, f"a second run re-asked despite the written config: {asked}"


def test_ci_never_blocks_and_never_writes_a_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Clause two. A prompt in a pipeline is a hung build.

    `input` is patched to raise, so a prompt on this path is a loud
    failure rather than a build that waits forever on stdin. And no
    prompt-derived config may appear: CI writing configuration into the
    tree would make the next local run silently inherit answers nobody
    gave.
    """
    root = _repo(tmp_path)
    _tty(monkeypatch, False)
    _forbidden_input(monkeypatch)

    assert main(["--root", str(root)]) == 0
    assert not (root / CONFIG_FILENAME).exists(), (
        "a non-TTY run wrote a config file nobody answered questions for"
    )


def test_an_existing_config_is_respected_even_on_a_tty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Clause one's other half: "with no config" is a real condition.

    A repository that has already chosen its depth and policy must never
    be re-asked, and the file must come through byte-identical — the
    prompt's job is to create a config where none exists, not to revise
    one that does.
    """
    root = _repo(tmp_path)
    config = root / CONFIG_FILENAME
    config.write_text(
        json.dumps({"analyzers": {"depth": "light", "license_policy": "permissive"}}),
        encoding="utf-8",
    )
    before = config.read_text(encoding="utf-8")
    _tty(monkeypatch, True)
    _forbidden_input(monkeypatch)

    assert main(["--root", str(root)]) == 0
    assert config.read_text(encoding="utf-8") == before, (
        "the first-run prompt rewrote an existing config"
    )
