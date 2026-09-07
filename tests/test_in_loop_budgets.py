"""What `--check` refuses, and what it says is left.

Split from `test_in_loop_check` at this project's 500-line file gate,
which this branch's work pushed it past.

The seam is what the tests are about. `test_in_loop_check` holds the
door's own contract — no repository, no git, the content on stdin is
authoritative, it never scores. This file holds the four defects Grok's
audit found *at* that door: a diff refused in every language (D133), a
cognitive-only failure reporting a negative overage (D132), flags
accepted and then ignored (D134), and headroom that watched only the
line budget (D135).
"""

from __future__ import annotations

import copy
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


def _check(path: str, text: str, config: dict | None = None) -> dict:
    from maintainability_audit._in_loop import check_content

    return check_content(path, text, config or _config())


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


def test_a_cognitive_only_failure_does_not_report_a_negative_line_overage() -> None:
    """The figure must be about the budget that failed.

    `_DECLARATION_BUDGETS` named length and cyclomatic complexity only.
    A function over `max_cognitive_complexity` but inside both of those
    produced an empty breach list, and the fallback then subtracted the
    *length* limit from the line count — printing `-73 over`, a negative
    overage of a budget the function was comfortably inside, for a breach
    that was real.

    `_breaches_for`'s own comment says a figure has to be about the thing
    that failed or it is worse than no figure. The fallback reintroduced
    exactly what that comment says was removed (D132).
    """
    nested = (
        "def nested(a, b, c, d, e):\n"
        "    if a:\n"
        "        if b:\n"
        "            if c:\n"
        "                if d:\n"
        "                    if e:\n"
        "                        return 1\n"
        "    return 0\n"
    )
    result = _check(
        "src/nested.py",
        nested,
        _config(max_cognitive_complexity=1, max_function_lines=80,
                max_complexity=50),
    )

    findings = result["findings"]
    assert findings, "a function over the cognitive budget reported nothing"
    finding = findings[0]

    assert finding["over_by"] is None or finding["over_by"] > 0, (
        f"reported {finding['over_by']} over — a negative overage names a "
        "budget that did not fail"
    )
    budgets = {breach["budget"] for breach in finding["breaches"]}
    assert "cognitive" in budgets, (
        f"the breach list names {budgets}, none of which is the budget that "
        "actually failed"
    )


#: Flags `--staged` refuses that `--check` did not. Both doors write
#: nothing, run nothing and apply no repository gates, so a flag one has
#: to ignore the other has to ignore. Two hand-kept lists drifted by
#: exactly these five (D134).
DRIFTED_REFUSALS = (
    "--comment-output", "--attestation-output", "--agent-instructions-output",
    "--hostile-prompt-output", "--transformation",
)


@pytest.mark.parametrize("flag", DRIFTED_REFUSALS)
def test_check_refuses_every_flag_staged_refuses(
    flag: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--staged` named this class and `--check` did not apply it.

    A flag accepted and ignored teaches the caller it was honoured.
    `_check_action` returns before `write_outputs`, so
    `--check --comment-output x.md` exited 0 or 1 and wrote nothing at
    all — the caller was told the check ran and the comment was written,
    and one of those was false.
    """
    import io

    from maintainability_audit.cli import main

    monkeypatch.setattr("sys.stdin", io.StringIO("x = 1\n"))
    with pytest.raises(SystemExit) as exit:
        main(["--root", str(tmp_path), "--check", "widget.py",
              flag, str(tmp_path / "out.md")])

    assert exit.value.code == 2, f"{flag} was accepted by --check"
    assert "--check does not take" in capsys.readouterr().err


def test_the_two_doors_refuse_the_same_flags() -> None:
    """The structural half: one list, not two kept in step by hand.

    `--check` and `--staged` write nothing, run nothing and apply no
    repository gates. Any flag one of them would have to ignore, the
    other would too — so deriving the second set from the first makes
    drift impossible rather than merely detected. A flag added to
    `_STAGED_REFUSES` tomorrow covers `--check` on the same commit.
    """
    from maintainability_audit.cli import _CHECK_REFUSES, _STAGED_REFUSES

    missing = sorted(set(_STAGED_REFUSES) - set(_CHECK_REFUSES))
    assert not missing, (
        f"--staged refuses {missing} and --check does not; a flag accepted "
        "and ignored teaches the caller it was honoured"
    )
    assert "staged" in _CHECK_REFUSES, "--check must still refuse --staged"


def test_headroom_covers_complexity_not_only_lines() -> None:
    """The product claim is remaining budget, not only a verdict.

    `_headroom` and `_band` used the line limit alone, so a short but
    complex function reported `band: ok` with comfortable headroom while
    sitting over the cyclomatic warn line. In text that is silence; in
    JSON it is a budget that looks fine. Complexity is a budget these
    declarations *fail* on (D132) and never showed a remainder for
    (D135).
    """
    body = "".join(f"    if a{n}:\n        return {n}\n" for n in range(11))
    source = f"def branchy({', '.join(f'a{n}' for n in range(11))}):\n{body}    return 0\n"

    result = _check(
        "src/branchy.py",
        source,
        _config(max_function_lines=80, warn_function_lines=60,
                max_complexity=50, warn_complexity=10),
    )

    room = next(item for item in result["headroom"] if item["name"] == "branchy")
    assert room["band"] != "ok", (
        "a function over the cyclomatic warn line reported band=ok, so text "
        "stays silent and JSON headroom looks fine"
    )
    budgets = {b["budget"]: b for b in room.get("budgets", [])}
    assert "complexity" in budgets, (
        f"headroom names {sorted(budgets)}; the budget it is near is missing"
    )
    assert budgets["complexity"]["remaining"] == 50 - budgets["complexity"]["value"]


def test_headroom_still_reports_the_line_budget() -> None:
    """Covers existing behaviour: the line remainder was always reported
    and this pins it against the D135 change.

    Passes at the base deliberately — a guard, not a falsifier.
    """
    source = "def small(a):\n    return a\n"
    result = _check("src/small.py", source,
                    _config(max_function_lines=80, warn_function_lines=60))

    room = next(item for item in result["headroom"] if item["name"] == "small")
    assert room["band"] == "ok"
    assert room["remaining"] == 78
