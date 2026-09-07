"""Contract for the in-loop check: budgets answered before the write.

The roadmap's diagnosis of this project is that it is end-of-loop heavy —
"strong where it is cheapest to be strong, a CI gate after the work is
done, and thin during the loop, where a constraint is worth far more
because it prevents rather than rejects". 2.9.0 closed the pre-commit
half. This is the other half: an agent holding proposed content asks
whether it breaches a budget *before* writing it.

The difference from `--staged` is the whole point and is asserted below.
`--staged` needs a git index and answers pass/fail on what will be
committed. This needs no repository at all, takes the content it is given
as authoritative, and answers with **headroom** — a rejection tells an
author they are already over; a headroom figure tells them how much room
is left while they can still use it.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from maintainability_audit.config import DEFAULT_CONFIG

TIGHT = {"max_function_lines": 10, "warn_function_lines": 6,
         "max_file_lines": 40, "warn_file_lines": 20,
         "max_complexity": 15, "warn_complexity": 12}


def _config(**overrides: int) -> dict:
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["thresholds"].update(TIGHT)
    config["thresholds"].update(overrides)
    return config


def _function(name: str, body_lines: int) -> str:
    body = "".join(f"    value_{index} = {index}\n" for index in range(body_lines))
    return f"def {name}():\n{body}    return 0\n"


def _check(path: str, text: str, config: dict | None = None) -> dict:
    from maintainability_audit._in_loop import check_content

    return check_content(path, text, config or _config())


def test_it_needs_no_repository_and_no_git() -> None:
    """The loop is not a repository. Content in memory has no index.

    `--staged` reads `git show :path` and cannot answer without one.
    Asserted from a directory that is not a repository at all, because
    an agent mid-edit is not at a commit boundary and must not be made
    to reach one to get an answer.
    """
    result = _check("widget.py", _function("small", 2))
    assert result["path"] == "widget.py"
    assert result["scored"] is False


def test_the_given_content_is_authoritative_not_the_file_on_disk(tmp_path: Path) -> None:
    """What the agent is about to write, not what is already there.

    A check that read the path would answer about the previous version —
    the same class of mistake as a pre-commit hook reading the working
    tree instead of the index, one step earlier in the loop.
    """
    on_disk = tmp_path / "widget.py"
    on_disk.write_text(_function("enormous", 60), encoding="utf-8")

    result = _check(str(on_disk), _function("small", 2))
    assert result["findings"] == [], (
        "the check read the file on disk instead of the content it was given"
    )


def test_a_declaration_over_budget_is_reported_with_its_path_and_line() -> None:
    result = _check("widget.py", "\n\n" + _function("enormous", 40))
    breaches = [item for item in result["findings"]
                if item["finding_class"] == "oversized-declaration"]
    assert breaches, "an over-budget declaration was not reported"
    assert breaches[0]["name"] == "enormous"
    assert breaches[0]["line"] == 3, "the declaration's own start line was not reported"
    assert breaches[0]["target"], "a breach named no remedy"


def test_a_declaration_under_budget_reports_how_much_room_is_left() -> None:
    """The reason this exists rather than being `--staged` on one file.

    A gate says no once it is too late to be cheap. Headroom is usable
    while the author is still writing: eight of ten lines used, two left.
    """
    result = _check("widget.py", _function("nearly", 7))
    room = {entry["name"]: entry for entry in result["headroom"]}
    assert "nearly" in room, "a declaration under budget reported no headroom"
    entry = room["nearly"]
    assert entry["lines"] == 9
    assert entry["limit"] == 10
    assert entry["remaining"] == 1
    assert entry["band"] == "warn", "a declaration past the warn line was not banded"


def test_the_file_length_budget_reports_headroom_too() -> None:
    result = _check("widget.py", "x = 1\n" * 30)
    assert result["file"]["lines"] == 30
    assert result["file"]["limit"] == 40
    assert result["file"]["remaining"] == 10
    assert result["file"]["band"] == "warn"


def test_it_never_scores() -> None:
    """One file has no population, so no rate drawn from it means anything.

    Asserted as an absence *and* as a stated reason, because a consumer
    that reads no score and infers a good one is the failure the whole
    evidence model exists to prevent.
    """
    result = _check("widget.py", _function("enormous", 40))
    assert result["scored"] is False
    assert result["scored_reason"]
    for forbidden in ("score", "estimate", "grade", "verified_grade",
                      "maintainability_estimate"):
        assert forbidden not in result, f"the in-loop check produced a {forbidden}"


def test_an_unparsed_language_says_so_rather_than_passing_quietly() -> None:
    """Absence read as a pass is the defect this project keeps finding.

    A `.kt` file has no declaration scanner. Reporting no findings for it
    is true and useless; a caller must be able to tell "nothing wrong"
    from "nothing looked at".

    The exemplar was `.rb` until 2.11.0 read Ruby — the fifth fixture to
    move as this project learned another language. Kotlin is the durable
    choice: no tool in the analyzer catalog measures its complexity,
    which is why it was ruled out for a scanner rather than merely
    unscheduled.
    """
    result = _check("widget.kt", "fun thing(): Int {\n    return 1\n}\n")
    assert result["declarations_read"] is False
    assert result["findings"] == []
    assert "kt" in result["note"] or "not parsed" in result["note"].lower()


def test_a_parsed_language_says_that_too() -> None:
    result = _check("widget.py", _function("small", 1))
    assert result["declarations_read"] is True


def test_the_rendering_is_silent_when_there_is_nothing_to_say() -> None:
    from maintainability_audit._in_loop_view import render_check

    clean = _check("widget.py", _function("small", 1))
    assert render_check(clean) == []


def test_the_rendering_names_the_breach_and_the_room_left() -> None:
    from maintainability_audit._in_loop_view import render_check

    result = _check("widget.py", _function("enormous", 40) + _function("nearly", 7))
    printed = "\n".join(render_check(result))
    assert "enormous" in printed
    assert "nearly" in printed, "a declaration with headroom was not shown"
    assert "1 line left" in printed, "the remaining budget was not printed"


def test_the_json_is_parseable_and_declares_that_nothing_was_scored() -> None:
    from maintainability_audit._in_loop_view import check_json

    result = _check("widget.py", _function("enormous", 40))
    payload = json.loads(check_json(result))
    assert payload["scored"] is False
    assert payload["blocked"] is True
    assert payload["findings"], "the JSON carried no findings for a breach"


def test_the_cli_reads_the_content_from_stdin_and_exits_one_on_a_breach(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--check PATH`, content on stdin: the shape an agent can pipe into.

    Exit 1 blocks, 0 passes silently — the same contract `--staged` uses,
    so one habit covers both ends of the loop.
    """
    import io

    from maintainability_audit.cli import main

    config = tmp_path / "maintainability-agent.json"
    config.write_text(json.dumps({"version": 1, "thresholds": TIGHT}), encoding="utf-8")

    monkeypatch.setattr("sys.stdin", io.StringIO(_function("enormous", 40)))
    code = main(["--root", str(tmp_path), "--config", str(config), "--check", "widget.py"])
    assert code == 1
    assert "enormous" in capsys.readouterr().out

    monkeypatch.setattr("sys.stdin", io.StringIO(_function("small", 1)))
    assert main(["--root", str(tmp_path), "--config", str(config), "--check", "widget.py"]) == 0
    assert capsys.readouterr().out == "", "a clean check printed something"


def test_the_cli_refuses_the_flags_it_would_have_to_ignore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A flag accepted and ignored teaches the caller it was honoured.

    The refusal *sentence* is asserted, not the flag name: argparse
    prints a usage banner listing every flag on any error, so checking
    for the name alone passes on a tree where `--check` does not exist
    (D109).
    """
    import io

    from maintainability_audit.cli import main

    monkeypatch.setattr("sys.stdin", io.StringIO("x = 1\n"))
    with pytest.raises(SystemExit) as exit:
        main(["--root", str(tmp_path), "--check", "widget.py", "--staged"])
    assert exit.value.code == 2
    assert "--check does not take" in capsys.readouterr().err


def test_it_runs_in_a_directory_that_is_not_a_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Covers existing behaviour: check_content does not consult git.

    The original test ran inside this repository. A git spawn would
    still have succeeded. This one chdirs to a directory with no .git.
    """
    monkeypatch.chdir(tmp_path)
    assert not (tmp_path / ".git").exists()
    result = _check("widget.py", _function("small", 2))
    assert result["path"] == "widget.py"
    assert result["scored"] is False


def test_check_json_carries_the_result_scored_flag_not_a_hardcoded_false() -> None:
    """JSON must report what the result said, not a constant.

    check_json currently writes `"scored": False` regardless of the
    result. A planted True must survive, or the field is theatre.
    """
    from maintainability_audit._in_loop_view import check_json

    payload = json.loads(check_json({
        "path": "widget.py",
        "findings": [{"finding_class": "oversized-declaration"}],
        "headroom": [],
        "file": {"lines": 1, "limit": 40, "remaining": 39, "band": "ok"},
        "declarations_read": True,
        "note": "",
        "scored": True,
        "scored_reason": "planted",
    }))
    assert payload["scored"] is True, (
        "check_json hardcoded scored false and ignored the result"
    )


def test_a_complexity_fail_is_not_reported_as_a_negative_line_overage() -> None:
    """The printed figure is about the budget that actually failed.

    A nine-line function over max_complexity and under max_function_lines
    currently renders `— -71 over` because over_by is always
    lines - max_function_lines.
    """
    from maintainability_audit._in_loop_view import render_check

    source = (
        "def branchy(value):\n"
        "    if value == 0:\n"
        "        return 1\n"
        "    elif value == 1:\n"
        "        return 2\n"
        "    elif value == 2:\n"
        "        return 3\n"
        "    else:\n"
        "        return 0\n"
    )
    result = _check("widget.py", source, _config(max_complexity=3, warn_complexity=2,
                                                 max_function_lines=80))
    breaches = [item for item in result["findings"]
                if item["finding_class"] == "oversized-declaration"]
    assert breaches, "a complexity fail was not reported"
    assert breaches[0]["over_by"] > 0, (
        f"a complexity fail was reported as a negative line remainder: "
        f"over_by={breaches[0]['over_by']}"
    )
    printed = "\n".join(render_check(result))
    assert "— -" not in printed, (
        "the renderer printed a negative line overage for a complexity fail"
    )


def _class(name: str, methods: int, body: int) -> str:
    lines = [f"class {name}:"]
    for index in range(methods):
        lines.append(f"    def method_{index}(self):")
        lines += [f"        x_{step} = {step}" for step in range(body)]
        lines.append("        return x_0")
    return "\n".join(lines) + "\n"


def test_a_class_is_measured_against_the_class_budget_not_the_function_one() -> None:
    """`max_class_lines` has shipped since before this feature existed.

    A class is a container: the per-function budget is the wrong yardstick
    for it, which `config-schema.md` has said all along (300 default
    against 80). The first version of this check used
    `max_function_lines` for every declaration, so an ordinary 111-line
    class reported `-31 lines left` against a budget it was nowhere near.
    Found in a field check by Gemini, using nothing but the CLI.
    """
    # Methods deliberately small and the file budget deliberately wide:
    # the only budget under test is the class's own, and a fixture that
    # breaches two others tells you nothing about which one answered.
    config = _config(max_file_lines=1000, warn_file_lines=900)
    config["thresholds"].update({"max_class_lines": 300, "warn_class_lines": 200})
    result = _check("widget.py", _class("BigService", 20, 2), config)

    room = {entry["name"]: entry for entry in result["headroom"]}
    assert "BigService" in room, "the class reported no headroom at all"
    assert room["BigService"]["limit"] == 300, (
        f"a class was measured against {room['BigService']['limit']}, "
        "which is the function budget, not the class budget"
    )
    assert room["BigService"]["band"] == "ok"
    declarations = [item for item in result["findings"]
                    if item["finding_class"] == "oversized-declaration"]
    assert declarations == [], "a class well inside its budget was reported"


def test_no_headroom_entry_ever_reports_a_negative_remainder() -> None:
    """Headroom is what is left. A negative is a breach, and breaches are findings.

    `! BigService — 111 of 80 lines, -31 lines left` was printed beside an
    exit code of 0. A warning that shows a negative remaining count while
    passing is not a warning, it is a contradiction the reader has to
    resolve themselves.
    """
    config = _config()
    config["thresholds"].update({"max_class_lines": 300, "warn_class_lines": 200})
    for text in (_class("BigService", 5, 20), _function("enormous", 40),
                 _function("nearly", 7), "x = 1\n" * 30):
        result = _check("widget.py", text, config)
        for entry in result["headroom"]:
            assert entry["remaining"] >= 0, (
                f"{entry['name']} sits in headroom with {entry['remaining']} "
                "remaining; a negative remainder belongs in findings"
            )


def test_content_that_does_not_parse_says_so_instead_of_reading_as_clean() -> None:
    """A diff piped in place of a file exited 0 and claimed it had read it.

    Python's parser refuses a unified diff, so nothing was found, and
    `declarations_read: true` then told the caller the file had been read
    and was clean. That is absence read as a pass — the defect this
    feature's own docstring says it exists to avoid — arriving through
    the most likely mistake an agent can make.
    """
    diff = (
        "--- a/src/foo.py\n"
        "+++ b/src/foo.py\n"
        "@@ -1,3 +1,4 @@\n"
        " def hello():\n"
        '+    print("world")\n'
        "     return 1\n"
    )
    result = _check("src/foo.py", diff)
    assert result["declarations_read"] is False, (
        "content that does not parse was reported as read"
    )
    assert result["note"], "nothing said that the content could not be parsed"
    assert "parse" in result["note"].lower()


def test_content_that_parses_is_still_reported_as_read() -> None:
    """Covers existing behaviour: valid content already reported True.

    Paired with the test above so a fix cannot satisfy it by reporting
    every file as unparsed.
    """
    result = _check("widget.py", _function("small", 1))
    assert result["declarations_read"] is True


#: One diff, named with each suffix `--check` claims to parse. The Python
#: case closed when Gemini found it; the class did not. `_parses` returned
#: `True` for every suffix except `.py`, so the same diff read as clean in
#: every brace language (D133).
DIFF_SUFFIXES = (".js", ".ts", ".java", ".c", ".go", ".rb", ".php", ".rs", ".swift")


@pytest.mark.parametrize("suffix", DIFF_SUFFIXES)
def test_a_piped_diff_is_refused_for_every_language_not_only_python(
    suffix: str,
) -> None:
    """The sentence in the docs was true of Python and of nothing else.

    > A diff piped into `--check` is not file content. **It will say it
    > could not parse**; do not read that as clean.

    It said that because `ast.parse` refuses a diff. Every other suffix
    took the `return True` above it, so `declarations_read` was true, the
    note was empty and the process exited 0 — the same shape Gemini
    found, in the twelve languages the fix did not reach.
    """
    diff = (
        f"--- a/src/thing{suffix}\n"
        f"+++ b/src/thing{suffix}\n"
        "@@ -1,3 +1,4 @@\n"
        " function hello() {\n"
        "+    log(1)\n"
        "     return 1\n"
        " }\n"
    )
    result = _check(f"src/thing{suffix}", diff)

    assert result["declarations_read"] is False, (
        f"a unified diff named {suffix} was reported as read"
    )
    assert "parse" in result["note"].lower(), (
        f"nothing said the {suffix} content could not be parsed"
    )


@pytest.mark.parametrize("suffix", DIFF_SUFFIXES)
def test_ordinary_source_is_not_called_a_diff(suffix: str) -> None:
    """Covers existing behaviour: ordinary brace source already read as
    read, and this pins it so the D133 refusal cannot take it away.

    It is the guard Grok named — do not mark valid brace source unparsed
    because it minted zero declarations — so it passes at the base by
    construction. Only the unified-diff *format* is refused.
    """
    source = "function hello() {\n    return 1;\n}\n"
    result = _check(f"src/thing{suffix}", source)

    assert result["declarations_read"] is True, (
        f"ordinary {suffix} source was reported as unparsed"
    )


def test_a_line_that_merely_mentions_a_hunk_header_is_not_a_diff() -> None:
    """Covers existing behaviour: a string mentioning a hunk header was
    never a diff, and this pins it against the D133 refusal.

    It passes at the base — nothing was refused there — so it guards the
    fix rather than proving it. Mention versus assertion, which this
    project has now met in suppression markers, escape phrases and risk
    patterns: the refusal needs the diff's *shape*, the `---`/`+++`
    header pair and a hunk header, not a substring anybody can write in
    a literal.
    """
    source = 'const help = "paste a hunk like @@ -1,3 +1,4 @@ here";\n'
    result = _check("src/thing.js", source)

    assert result["declarations_read"] is True, (
        "a string mentioning a hunk header was mistaken for a diff"
    )
