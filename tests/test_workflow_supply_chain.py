"""D41/D43: what the release pipeline trusts, and how it passes arguments.

Two supply-chain defects an audit found in the workflows, both of the
kind no product test would ever reach — CI configuration is code that
runs with more authority than the package does, and nothing was reading
it.

`release.yml` handed OIDC publication authority (`id-token: write`) to
`pypa/gh-action-pypi-publish@release/v1`. A branch reference resolves
to whatever it points at when the job starts, so whoever controls that
reference at run time runs in the job that can publish this package.

`action.yml` interpolated `${{ inputs.* }}` straight into a `run:`
script. GitHub substitutes those *before* bash parses the script, so an
input is not an argument — it is source code.

Parsed by hand rather than with PyYAML on purpose: this repository
keeps its `test` extra thin, and `test_declared_imports` refuses a
dev-only parser in tests. The shapes read here — `uses:` lines, a
`run:` block, an `env:` block — are simple enough that indentation
tracking is honest, and a wrong parse fails loudly rather than passing.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
COMPOSITE = ROOT / "action.yml"

#: A 40-character hex commit. Nothing else is immutable: tags move,
#: branches move, and `release/v1` is a branch wearing a version's name.
PINNED = re.compile(r"^[^@\s]+@[0-9a-f]{40}(\s+#.*)?$")

#: This repository's own action, referenced by the workflows that test
#: it. Pinning it to a SHA would mean a workflow could never exercise
#: the commit under review, which is the opposite of what CI is for.
OWN_ACTION = "marshallguillory86/maintainability-agent"


def _uses(path: Path) -> list[tuple[str, str]]:
    """Every `uses:` in a file, with the line it came from."""
    found = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = re.search(r"^\s*(?:-\s*)?uses:\s*(\S+.*?)\s*$", line)
        if match:
            found.append((f"{path.name}:{number}", match.group(1)))
    return found


@pytest.mark.parametrize("path", [*WORKFLOWS, COMPOSITE], ids=lambda p: p.name)
def test_every_third_party_action_is_pinned_to_a_commit(path: Path) -> None:
    """A tag is a promise the tag's owner can rewrite."""
    unpinned = [
        f"{where} -> {ref}"
        for where, ref in _uses(path)
        if not ref.startswith(OWN_ACTION) and not PINNED.match(ref)
    ]
    assert not unpinned, (
        "third-party actions referenced mutably; whoever controls these "
        "references at run time runs in this job: " + "; ".join(unpinned)
    )


def test_the_publishing_job_is_pinned_hardest_of_all() -> None:
    """The one job that can publish this package to the world.

    Called out separately from the sweep above because a generic rule
    is easy to relax for a specific case, and this is the case nobody
    should relax it for.
    """
    release = ROOT / ".github" / "workflows" / "release.yml"
    publishers = [
        ref for _where, ref in _uses(release)
        if "pypi-publish" in ref
    ]
    assert publishers, "release.yml no longer publishes; update this test"
    for ref in publishers:
        assert PINNED.match(ref), (
            f"the PyPI publish step is a moving reference: {ref}"
        )


def _run_blocks(path: Path) -> list[str]:
    """Every `run:` script body, by indentation.

    A `run: |` block continues while lines are indented past the key.
    That is the whole grammar this needs, and getting it wrong shows up
    as an empty list, which the caller asserts against.
    """
    blocks: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^(\s*)run:\s*(\|.*)?$", line)
        if not match:
            continue
        indent = len(match.group(1))
        body = []
        for following in lines[index + 1:]:
            if following.strip() and len(following) - len(following.lstrip()) <= indent:
                break
            body.append(following)
        blocks.append("\n".join(body))
    return blocks


def test_the_composite_action_never_interpolates_inputs_into_bash() -> None:
    """Inputs are data, and `${{ }}` in a `run:` makes them source.

    Checked against the `run:` scripts specifically. `${{ }}` elsewhere
    in the file — `env:` values, `if:` conditions — is exactly how a
    value is supposed to reach a step.
    """
    blocks = _run_blocks(COMPOSITE)
    assert blocks, "no run: blocks found; the parser or the file changed shape"

    offenders = [block.strip()[:70] for block in blocks if "${{" in block]
    assert not offenders, (
        "composite-action steps interpolate expressions into shell source; "
        "pass them through `env:` and quote the variable instead: "
        + "; ".join(offenders)
    )


def test_the_composite_action_still_passes_every_input_through() -> None:
    """Moving inputs to `env:` must not quietly drop one.

    A step that stops forwarding `--changed-only` would look exactly
    like a passing test and behave like a full-repository audit on
    every pull request.
    """
    text = COMPOSITE.read_text(encoding="utf-8")
    # Scoped to the `inputs:` block. A bare two-space-indented key also
    # matches `steps:` under `runs:`, and the first version of this
    # check duly demanded an `INPUT_STEPS` — a parser that reads the
    # wrong section produces confident nonsense.
    block = text.split("\ninputs:\n", maxsplit=1)
    assert len(block) == 2, "action.yml declares no inputs section"
    body = re.split(r"^\S", block[1], maxsplit=1, flags=re.MULTILINE)[0]
    declared = re.findall(r"^  ([a-z][a-z0-9-]*):$", body, re.MULTILINE)
    assert declared, "no inputs parsed from action.yml"

    for name in declared:
        variable = "INPUT_" + name.replace("-", "_").upper()
        assert variable in text, (
            f"input {name!r} is declared but never reaches the command"
        )
