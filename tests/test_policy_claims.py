"""The policy documents, held against the code they describe.

Split from `test_written_record` at this project's 500-line file gate.

The seam is the subject. `test_written_record` is about the defect
register — that an entry closes on a falsifier a reader can run, that a
decision names a decider, that no document calls an entry open which the
register closed. These are about the *other* promises the repository
publishes: which release line `SECURITY.md` supports, the guarantee it
states on the tool's behalf, and whether the declared Python floor
actually supports the syntax in use.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs" / "defect-register-chat-surface.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_the_security_policy_supports_the_shipped_release_line() -> None:
    """D45: a policy naming a dead version line supports nothing.

    `SECURITY.md` still said `0.1.x` at version 0.9.1 — eight release
    lines of drift, which read literally meant the shipped release
    received no security fixes. Nobody noticed because nothing looked.

    Checked against `config.VERSION` rather than a written-in number,
    so the next release either updates the table or fails here.
    """
    from maintainability_audit.config import VERSION

    line = ".".join(VERSION.split(".")[:2])
    policy = _read(ROOT / "SECURITY.md")
    assert f"`{line}.x`" in policy, (
        f"SECURITY.md does not name the shipped release line {line}.x; "
        "its supported-versions table has drifted from the package"
    )


def test_the_security_policy_states_the_guarantee_the_code_keeps() -> None:
    """This claim has now been wrong in both directions.

    `SECURITY.md` first asserted the agent "does not execute scanned
    code" while eslint was being invoked in a mode that *requires* the
    audited repository's configuration and then runs it. That was
    corrected to say the agent does execute it, with the question left
    open as D39 and D44.

    Decision 9 then settled it and the code caught up — eslint refused,
    pylint and mypy isolated, the child's environment scrubbed — and
    this file kept describing the defect for another day. A promise
    that has become true while its own documentation denies it is the
    same defect class as the reverse, and neither direction is caught
    by a check that only forbids one sentence.

    So this reads the file against the code rather than against a
    phrase: whatever the policy says, the adapter that cannot run
    without the tree's configuration must be refused, and the two
    isolated tools must carry their flags.
    """
    from maintainability_audit._generic import DECLARED, declared_adapter
    from maintainability_audit._tool_adapters import ADAPTERS, adapter_for

    policy = " ".join(_read(ROOT / "SECURITY.md").lower().split())
    denies = "does not execute code from the repository" in policy
    claims_it_does = "it does execute code from the repository" in policy

    refused = {
        slug for slug in ADAPTERS
        if getattr(adapter_for(slug), "executes_audited_configuration", False)
    }
    isolated = {
        slug for slug in DECLARED
        if any(
            item.startswith(("--rcfile=", "--config-file="))
            for item in declared_adapter(slug).invocation(ROOT, excludes=()).argv
        )
    }
    honoured = bool(refused) and isolated == set(DECLARED)

    assert denies or claims_it_does, (
        "SECURITY.md says nothing either way about executing repository "
        "code, which is the one thing a reader comes to this file for"
    )
    assert denies == honoured, (
        "SECURITY.md and the code disagree about executing repository "
        f"code. policy denies it: {denies}. refused adapters: "
        f"{sorted(refused)}, isolated declared tools: {sorted(isolated)} "
        f"of {sorted(DECLARED)}"
    )
    assert not claims_it_does or not honoured, (
        "SECURITY.md still describes the defect Decision 9 closed"
    )


def test_the_declared_python_floor_supports_the_features_in_use() -> None:
    """D42: metadata that promises a Python the code cannot run on.

    `requires-python` said `>=3.10` while three runtime modules import
    `enum.StrEnum`, which is 3.11. Pip installed happily on 3.10 and
    the import then failed — and nothing caught it, because CI runs
    3.12 and the composite action pins 3.11, so no machine in the
    pipeline ever stood where the metadata said a user could stand.

    I first recorded that no honest test was possible here, on the
    grounds that any such check restates a constant. That was wrong.
    This does not restate the floor; it ties the floor to the language
    features actually imported, which is the relationship that broke.
    A CI matrix entry on the floor version is still worth having, and
    is still recorded as follow-up — but it is not the only check
    available.
    """
    import re as _re

    features = {
        # feature -> (minimum minor version, why)
        "StrEnum": (11, "enum.StrEnum landed in 3.11"),
        "ExceptionGroup": (11, "ExceptionGroup landed in 3.11"),
        "tomllib": (11, "tomllib landed in 3.11"),
        "override": (12, "typing.override landed in 3.12"),
    }

    declared = _re.search(
        r'requires-python\s*=\s*">=3\.(\d+)"',
        _read(ROOT / "pyproject.toml"),
    )
    assert declared, "pyproject.toml no longer declares a requires-python floor"
    floor = int(declared.group(1))

    package = ROOT / "src" / "maintainability_audit"
    for module in sorted(package.rglob("*.py")):
        # Imports and decorators only. A first version matched the bare
        # word anywhere and flagged `_economics.py` for the English
        # "override" in a docstring — a check that cries wolf is a check
        # somebody turns off.
        lines = [
            line for line in _read(module).splitlines()
            if line.startswith(("import ", "from ")) or line.lstrip().startswith("@")
        ]
        text = "\n".join(lines)
        for feature, (needs, why) in features.items():
            if _re.search(rf"\b{feature}\b", text) and needs > floor:
                raise AssertionError(
                    f"{module.relative_to(ROOT)} uses {feature} ({why}) but "
                    f"pyproject declares >=3.{floor}; pip would install on "
                    f"3.{floor} and the import would fail"
                )
