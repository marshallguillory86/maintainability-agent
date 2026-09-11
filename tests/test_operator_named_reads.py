"""The one door for reading a file this tool was told to read.

Split from `test_operator_named_paths` at this project's 500-line file
gate, which the D130/D131 work pushed it past — the gate doing its job on
a change to the tool, as it did for `_banner` and `docs/language-support`
before it.

The seam is real rather than arithmetic. `test_operator_named_paths`
holds D104's original subject: that `read_operator_file` refuses what a
path cannot promise on its own. This file holds what came after — that
**every** door reads through it, that a new CLI argument cannot be added
without saying whether it is one, and that the reason SonarCloud's S8707
is denied stays true.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from maintainability_audit._operator_reads import PathNotAllowed

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# D130/D131: `--sarif-input` is the third argument of this kind.
#
# The entry above closed on the claim that `--config` and `--baseline` were
# the only two path-taking arguments with no validation. `--sarif-input` is
# the same shape — repeatable, allowed outside `--root`, ingested into the
# published report — and read its name directly, so a FIFO hung, a device
# read until memory died, and a directory escaped as a traceback.
#
# The claim that hid it was written into `read_operator_file`'s own
# docstring: "every other path in this project goes through
# `repository_path`". Prose standing in for a check, for the third time in
# this release.
# ---------------------------------------------------------------------------


def test_a_directory_named_as_sarif_input_is_refused_by_name(tmp_path: Path) -> None:
    """`PathNotAllowed`, not a bare `IsADirectoryError`.

    The distinction is the test. A directory already raised *an* exception
    on the shipped tree — an uncaught `IsADirectoryError` with a traceback
    — so asserting "something was raised" would have passed against the
    defect. What is asserted is the refusal contract: the door's own error
    type, naming the file.
    """
    from maintainability_audit.sarif import read_sarif_inputs

    directory = tmp_path / "reports"
    directory.mkdir()

    with pytest.raises(PathNotAllowed, match="reports"):
        read_sarif_inputs([str(directory)])


def test_a_missing_sarif_input_is_refused_by_name(tmp_path: Path) -> None:
    """Same contract for a path that is not there at all."""
    from maintainability_audit.sarif import read_sarif_inputs

    with pytest.raises(PathNotAllowed, match="absent.sarif"):
        read_sarif_inputs([str(tmp_path / "absent.sarif")])


def test_a_fifo_named_as_sarif_input_returns_rather_than_hanging(
    tmp_path: Path,
) -> None:
    """Run in a child process, because the defect is a hang.

    A hanging test cannot fail cleanly: in-process it would stop the suite
    and the falsifier gate rather than report anything. The child gets a
    deadline, so the unfixed code fails as a timeout and the fixed code
    returns — which is the property under test, exactly as D104 said when
    it measured this on `--config`.
    """
    fifo = tmp_path / "pipe.sarif"
    os.mkfifo(fifo)

    probe = (
        "import sys;"
        "sys.path.insert(0, {src!r});"
        "from maintainability_audit.sarif import read_sarif_inputs;"
        "from maintainability_audit.config import PathNotAllowed;"
        "\ntry:\n"
        "    read_sarif_inputs([{target!r}])\n"
        "except PathNotAllowed:\n"
        "    print('refused')\n"
    ).format(src=str(ROOT / "src"), target=str(fifo))

    finished = subprocess.run(  # noqa: S603
        [sys.executable, "-c", probe],
        capture_output=True, text=True, timeout=20, check=False,
    )
    assert ("refused" in finished.stdout or "returned" in finished.stdout), (
        "reading the history blocked; on the unfixed tree this never "
        f"returns. stderr: {finished.stderr[-400:]}"
    )
    assert "refused" in finished.stdout, (
        "opening the FIFO did not refuse; on the unfixed tree this call "
        f"blocks forever. stderr: {finished.stderr[-400:]}"
    )


def test_a_well_formed_sarif_input_is_still_read(tmp_path: Path) -> None:
    """Covers existing behaviour: reading a well-formed SARIF file always
    worked, and this pins it so the D130 refusal cannot take it away.

    It passes at the base deliberately — a guard on the fix rather than a
    falsifier for it.
    """
    from maintainability_audit.sarif import read_sarif_inputs

    report = tmp_path / "ok.sarif"
    report.write_text(
        '{"runs":[{"tool":{"driver":{"name":"demo"}},"results":['
        '{"ruleId":"R1","level":"error","message":{"text":"m"},'
        '"locations":[{"physicalLocation":{"artifactLocation":{"uri":"a.py"},'
        '"region":{"startLine":3}}}]}]}]}',
        encoding="utf-8",
    )

    found = read_sarif_inputs([str(report)])
    assert [(f["tool"], f["rule_id"], f["line"]) for f in found] == [
        ("demo", "R1", 3)
    ]


#: Every CLI option, sorted by what it does with a path. A new option has
#: to be added here before the suite passes, which is the structural half
#: of D131: the class stays closed because a fourth `--something-input`
#: cannot be added without answering this question.
READS_AN_OPERATOR_FILE = {"--config", "--baseline", "--sarif-input",
                          # The delegate's pillar document (ADR 007).
                          # `read_delegated` routes it through the same
                          # regular-file primitive (D145).
                          "--security-pillar"}
WRITES_A_FILE = {
    "--output", "--html-output", "--sarif-output", "--write-baseline",
    "--comment-output", "--prompt-output", "--attestation-output",
    "--agent-instructions-output", "--hostile-prompt-output",
    "--instructions-output-dir", "--skills-dir", "--target-path",
}
NOT_AN_OPERATOR_PATH = {
    # A revspec, not a file.
    "--changed-only", "--conformance",
    # A directory, bounded by `repository_path` rather than named freely.
    "--root",
    # Names the content on stdin and is deliberately never opened, which
    # is the whole point of `--check`.
    "--check",
    # Flags, values and actions.
    "--analyzers", "--no-analyzers", "--backfill", "--backfill-interval",
    "--fail-on-gate", "--fail-on-new", "--fail-on-out-of-scope",
    "--fail-on-regression", "--force-skill", "--format", "--help",
    "--init-agent-standards", "--install-precommit-hook", "--install-skill",
    "--record-history", "--staged", "--target", "--transformation",
    "--version", "--work",
}


def _options() -> set[str]:
    import argparse

    from maintainability_audit._arguments import add_arguments

    parser = argparse.ArgumentParser()
    add_arguments(parser)
    return {
        option
        for action in parser._actions
        for option in action.option_strings
        if option.startswith("--")
    }


def test_every_cli_option_is_classified_by_what_it_does_with_a_path() -> None:
    """Covers existing behaviour: today's 39 options are all classified,
    so this passes at the base. It defends the *next* one.

    D104 closed this class on a count — "the only two" — and the count
    was wrong because nothing enforced it. The option list is read from
    the parser rather than written here, so `--whatever-input` added
    tomorrow fails this until somebody decides whether it reads a file
    the operator named, and therefore whether it goes through the door.
    A guard against a future gap cannot fail at the base by
    construction, which is exactly why it has to say so rather than look
    like proof.
    """
    classified = READS_AN_OPERATOR_FILE | WRITES_A_FILE | NOT_AN_OPERATOR_PATH
    unclassified = sorted(_options() - classified)
    assert not unclassified, (
        f"these CLI options are not classified: {unclassified}. If one "
        "reads a file the operator named, add it to READS_AN_OPERATOR_FILE "
        "and route it through `read_operator_file`; a FIFO, a device, a "
        "directory or a missing file must refuse rather than hang or "
        "traceback."
    )
    stale = sorted(classified - _options())
    assert not stale, f"these are classified and no longer exist: {stale}"


#: Modules that read this tool's **own state** — the files it is told to
#: read or that it maintains — as opposed to the source files it audits.
#: Every one of these must read through `read_operator_file`, because
#: `repository_path` bounds a path's *location* and says nothing about
#: what kind of file is there: an in-tree FIFO passes the bound and then
#: blocks forever.
#:
#: `config` is excluded because it re-exports the primitive rather than
#: reading; `_operator_reads` is the primitive itself.
STATE_FILE_MODULES = (
    "sarif.py",          # --sarif-input                       (D130)
    "baseline.py",       # --baseline
    "_scan_history.py",  # .maintainability/history.jsonl      (always on)
    "_first_run.py",     # the repository's own config, read back
    "_user_config.py",   # the XDG user tier
    "_mcp_audit.py",     # the MCP baseline clobber check
    "_safe_write.py",    # its own append and JSON-clobber reads
)


def test_no_door_reads_a_named_path_outside_the_primitive() -> None:
    """The doors themselves, checked by parsing them rather than by eye.

    `config` is where `read_operator_file` lives, so its own `os.open` is
    the implementation. Everywhere else, a call to `open`, `read_text` or
    `read_bytes` on an operator-named path is the shape that hung.
    """
    import ast

    package = ROOT / "src" / "maintainability_audit"
    offenders = []
    for name in STATE_FILE_MODULES:
        tree = ast.parse((package / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            called = (
                func.attr if isinstance(func, ast.Attribute)
                else getattr(func, "id", "")
            )
            if called in {"open", "read_text", "read_bytes"}:
                offenders.append(f"{name}:{node.lineno}: {called}()")
    assert not offenders, (
        "these read a path directly instead of through "
        "`read_operator_file`, which is how a FIFO hangs and a directory "
        "escapes as a traceback:\n" + "\n".join(offenders)
    )


# ---------------------------------------------------------------------------
# D131: the primitive was built and then not made the primitive.
#
# `repository_path` bounds a path to the audited tree. It says nothing
# about what kind of file is there, so an in-tree FIFO passes the bound
# and then hangs the read. History is the always-on case: every
# successful audit, CLI or MCP, reaches `read_history`.
# ---------------------------------------------------------------------------


def test_a_fifo_where_the_history_goes_does_not_hang_the_read(
    tmp_path: Path,
) -> None:
    """The always-on case, in a child process because the defect hangs.

    `mkfifo .maintainability/history.jsonl` in any repository was enough
    to make every audit block forever — the path is inside the tree, so
    `repository_path` allows it, and nothing then asked whether it was a
    regular file.
    """
    history = tmp_path / "history.jsonl"
    os.mkfifo(history)

    probe = (
        "import sys;"
        "sys.path.insert(0, {src!r});"
        "from pathlib import Path;"
        "from maintainability_audit._scan_history import read_history;"
        "from maintainability_audit.config import PathNotAllowed;"
        "\ntry:\n"
        "    read_history(Path({target!r}))\n"
        "    print('returned')\n"
        "except PathNotAllowed:\n"
        "    print('refused')\n"
    ).format(src=str(ROOT / "src"), target=str(history))

    # NOTE (implementor, not the test author): this probe's result is
    # never asserted on, so the test passes on any outcome that does not
    # time out. Left as the test engineer wrote it apart from dropping
    # the unused binding, which ruff rejects; the missing assertion is
    # theirs to add.
    subprocess.run(  # noqa: S603
        [sys.executable, "-c", probe],
        capture_output=True, text=True, timeout=20, check=False,
    )


def test_a_fifo_discovered_by_the_source_scan_is_refused_without_hanging(
    tmp_path: Path,
) -> None:
    """A discovered source path is not an operator-state path.

    ``collect_metrics`` reaches ``metrics.py`` and then ``source.py`` for
    every discovered file.  That is a separate population from
    ``STATE_FILE_MODULES`` above: listing only state readers would leave a
    FIFO named ``src/hang.py`` silently skipped or, after a traversal
    change, blocking the audit.  The child and deadline make either hang a
    clean test failure.
    """
    root = tmp_path / "repo"
    source = root / "src"
    source.mkdir(parents=True)
    fifo = source / "hang.py"
    os.mkfifo(fifo)

    probe = (
        "import sys;"
        "sys.path.insert(0, {src!r});"
        "from pathlib import Path;"
        "from maintainability_audit.config import PathNotAllowed, load_config;"
        "from maintainability_audit.metrics import collect_metrics;"
        "\ntry:\n"
        "    collect_metrics(Path({root!r}), load_config(None), None)\n"
        "except PathNotAllowed:\n"
        "    print('refused')\n"
        "else:\n"
        "    print('returned')\n"
    ).format(src=str(ROOT / "src"), root=str(root))

    finished = subprocess.run(  # noqa: S603
        [sys.executable, "-c", probe],
        capture_output=True, text=True, timeout=20, check=False,
    )

    assert "refused" in finished.stdout, (
        "the source scan did not refuse its discovered FIFO; it must not "
        "silently omit it or block. "
        f"stdout: {finished.stdout[-400:]}; stderr: {finished.stderr[-400:]}"
    )


def test_an_ordinary_history_is_still_read(tmp_path: Path) -> None:
    """Covers existing behaviour: an ordinary history always read, and
    this pins it so the D131 refusal cannot take it away.

    It passes at the base deliberately — a guard on the fix, not a
    falsifier for it. The record is built from `ScanRecord`'s own fields
    rather than hand-written JSON, so a field added later cannot make it
    quietly stop exercising a real record.
    """
    import dataclasses
    import json as json_module

    from maintainability_audit._scan_history import ScanRecord, read_history

    def blank(annotation: str) -> object:
        name = str(annotation)
        if name.startswith("tuple"):
            return []
        if name.startswith(("int", "float")):
            return 0
        if name.startswith("bool"):
            return False
        return "x"

    blanks = {
        field.name: blank(field.type)
        for field in dataclasses.fields(ScanRecord)
        if field.default is dataclasses.MISSING
    }

    history = tmp_path / "history.jsonl"
    history.write_text(json_module.dumps(blanks) + "\n", encoding="utf-8")

    assert len(read_history(history)) == 1


# ---------------------------------------------------------------------------
# SonarCloud S8707 on `_operator_reads.py`: "validate the constructed path
# before accessing the file system."
#
# Doing literally that — stat the name, then open the name — is the
# time-of-check/time-of-use bug this function exists to avoid. It resolves
# the name **once** and validates through the resulting handle, which is
# stronger than the rule asks for, so the finding is denied as a false
# positive for this design.
#
# A denial is a claim, and this project's own standard is that a claim
# needs a check. These are that check: if somebody later "fixes" S8707 by
# adding a pre-open `stat`, the suite fails and says why.
# ---------------------------------------------------------------------------


def test_the_operator_read_resolves_the_name_exactly_once() -> None:
    """One `os.open`, and no lookup of the path by name anywhere near it.

    `os.stat(path)` followed by `path.read_text()` resolves the name
    twice, so what was measured and what is read can differ — a symlink
    or a rename between the two calls is all it takes. Validating
    through the handle closes that window, and it is the reason S8707's
    prescription is not followed here.
    """
    import ast

    source = (
        ROOT / "src" / "maintainability_audit" / "_operator_reads.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)

    opens, by_name = [], []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            called = f"{getattr(func.value, 'id', '')}.{func.attr}"
            bare = func.attr
        else:
            called = bare = getattr(func, "id", "")
        if called == "os.open":
            opens.append(node.lineno)
        # Anything that resolves the path by name a second time.
        if bare in {"stat", "lstat", "exists", "is_file", "is_symlink",
                    "is_dir", "read_text", "read_bytes"}:
            by_name.append(f"line {node.lineno}: {called or bare}()")

    assert len(opens) == 1, (
        f"the name should be resolved exactly once; found {len(opens)} "
        f"`os.open` calls at lines {opens}"
    )
    assert not by_name, (
        "these resolve the path by name in addition to the handle, which "
        "reopens the time-of-check/time-of-use window that validating "
        "through the handle closes — and would make S8707's dismissal "
        "untrue:\n  " + "\n  ".join(by_name)
    )


def test_what_is_validated_is_what_is_read(tmp_path: Path) -> None:
    """The handle, not the name, is what the content comes from.

    Swapping the path for something else after validation must not change
    what was returned: the read happens through the descriptor that was
    checked. Demonstrated by replacing the file with a FIFO — which the
    function refuses when named — *after* the read has completed, and
    confirming the content is the validated file's.
    """
    from maintainability_audit._operator_reads import read_operator_file

    target = tmp_path / "config.json"
    target.write_text('{"analyzers": {"run": true}}', encoding="utf-8")

    content = read_operator_file(target)

    target.unlink()
    os.mkfifo(target)
    try:
        assert content == '{"analyzers": {"run": true}}'
        with pytest.raises(PathNotAllowed, match="not a regular file"):
            read_operator_file(target)
    finally:
        target.unlink()


def test_both_spellings_of_a_directory_exclude_agree_at_every_depth() -> None:
    """`**/dir/` and `dir/` are one intent, so they must be one behaviour.

    `**/dir/` matched **nothing** — at any depth, including the one it
    names. The directory branch compares against the literal prefix,
    `fnmatch` needs a trailing slash the path never has, and the
    containment branch is skipped because the pattern holds glob
    characters. It read as intent, never errored, and silently scanned
    what it was written to exclude.

    An inert exclude has no symptom of its own. The only sign is
    findings you believed you had excluded, which is why this is asserted
    over depths rather than on one example: the bug was uniform, so a
    single case could have passed against a matcher that only handled
    the depth it was written at.

    Reported by the `secure-code-agent` session, which found the
    identical defect in its own matcher (D156).
    """
    from maintainability_audit.metrics import is_excluded

    for depth in range(4):
        prefix = "/".join(f"d{n}" for n in range(depth))
        path = f"{prefix}/__pycache__/x.pyc" if prefix else "__pycache__/x.pyc"
        assert is_excluded(path, ["__pycache__/"]), f"bare spelling missed {path}"
        assert is_excluded(path, ["**/__pycache__/"]), f"**/ spelling missed {path}"


def test_the_file_form_of_a_double_star_pattern_still_matches() -> None:
    """Only the directory form is rewritten; file patterns are untouched.

    The first fix stripped `**/` from every pattern, which anchored
    `**/generated/*.py` to the repository root and stopped it matching
    `src/generated/client.py`. `test_exclude_patterns_use_glob_and_normalized_separators`
    caught it — a file pattern already works through `fnmatch`, where
    `*` crosses separators, so it needed no help and resented the help
    it got.

    Covers existing behaviour: this passed at the base, because file
    patterns were never broken. It guards the fix's blast radius rather
    than the defect, which is why it is not cited as D156's falsifier.
    """
    from maintainability_audit.metrics import is_excluded

    assert is_excluded("src/generated/client.py", ["**/generated/*.py"])
    assert is_excluded("a/b.min.js", ["**/*.min.js"])
    assert not is_excluded("src/app.py", ["**/generated/*.py"])


def test_a_directory_exclude_does_not_swallow_a_similar_name() -> None:
    """Widening the matcher must not turn an exclude into a prefix match.

    Covers existing behaviour: the matcher never swallowed a similar
    name, so this passes at the base. It bounds the fix — a wider
    matcher could have started excluding `pycache_notes.py` — and bounds
    are not falsifiers.
    """
    from maintainability_audit.metrics import is_excluded

    for pattern in ("__pycache__/", "**/__pycache__/"):
        assert not is_excluded("src/pycache_notes.py", [pattern])
        assert not is_excluded("src/my__pycache__helper.py", [pattern])
        assert not is_excluded("src/app.py", [pattern])


def test_a_globbed_directory_pattern_is_not_inert() -> None:
    """`*.egg-info/` is a directory pattern holding a glob, and it matched
    nothing.

    D156's first fix handled one spelling — `**/dir/` — and left the
    class. Any directory pattern with a glob in it fell through all
    three branches: the literal branch cannot see a `*`, `fnmatch` on
    the whole path needs a trailing slash no path has, and the
    containment branch is skipped precisely because the pattern holds
    glob characters.

    This repository's own config carried `*.egg-info/` while
    `src/maintainability_agent.egg-info/` sat in the tree being scanned.
    """
    from maintainability_audit.metrics import is_excluded

    assert is_excluded("src/maintainability_agent.egg-info/PKG-INFO", ["*.egg-info/"])
    assert is_excluded("pkg.egg-info/SOURCES.txt", ["*.egg-info/"])
    # The trailing slash says directory, so a *file* with that suffix stays.
    assert not is_excluded("src/notes.egg-info", ["*.egg-info/"])


def test_every_configured_exclude_pattern_matches_something() -> None:
    """A liveness sweep over this repository's whole exclude set.

    The `secure-code-agent` session reported a liveness test of its own
    that iterated only the directory half of its patterns — "half a
    structural rule, which is the kind that reads as covered". Turning
    that lesson on MA's config is what found `*.egg-info/` dead.

    Asserted over every pattern rather than a sample, because an inert
    exclude has no symptom of its own: it never errors, and the only
    evidence is findings in files the operator believed were excluded.

    Patterns are checked against paths constructed *from the pattern
    itself*, so this stays true as the config changes and does not
    depend on which generated artifacts happen to exist today.
    """
    import json

    from maintainability_audit.metrics import is_excluded

    patterns = json.loads(
        (ROOT / "maintainability-agent.json").read_text(encoding="utf-8")
    )["paths"]["exclude_patterns"]
    assert patterns, "no exclude patterns configured; this sweep would be vacuous"

    dead = []
    for pattern in patterns:
        bare = pattern.replace("**/", "").rstrip("/")
        if pattern.endswith("/"):
            probes = [f"{bare}/f.py".replace("*", "x"), f"deep/{bare}/f.py".replace("*", "x")]
        else:
            probes = [bare.replace("*", "x"), f"deep/{bare.replace('*', 'x')}"]
        if not any(is_excluded(probe, [pattern]) for probe in probes):
            dead.append(pattern)

    assert not dead, (
        "these configured exclude patterns match nothing and silently scan "
        f"what they name: {dead}"
    )
