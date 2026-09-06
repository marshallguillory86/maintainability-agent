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

    A `.rb` file has no declaration scanner. Reporting no findings for it
    is true and useless; a caller must be able to tell "nothing wrong"
    from "nothing looked at".
    """
    result = _check("widget.rb", "def thing\n  1\nend\n")
    assert result["declarations_read"] is False
    assert result["findings"] == []
    assert "rb" in result["note"] or "not parsed" in result["note"].lower()


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
