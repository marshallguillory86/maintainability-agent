"""Shell: functions bounded by braces, in a language where `#` is not always a comment.

A shell function is braced like C, so the walk is `scan_bounded`'s. What
is worth testing is where shell's text is not what the C-family masker
thinks it is:

- **`#` starts a comment only at the start of a word.** `$#` is the
  argument count and `${#list[@]}` a length; blanking from either to the
  end of the line would hide the `if` that tests it.
- **`//` and `/*` are not comments.** `rm -rf "$dir"/*` is ordinary
  shell, and the C masker would blank the rest of the line — or the rest
  of the file, waiting for a `*/` that never comes.
- **A heredoc body is text**, and routinely contains braces, `fi` and
  function-shaped lines: generated scripts, usage text, config files.
- **A double-quoted string may span lines**, which usage messages do.

Three definition forms are POSIX or bash and all are common: `name() {`,
`function name {` and `function name() {`. The body may open on the next
line, and may be a subshell `( … )` rather than a brace group.
"""

from __future__ import annotations

from pathlib import Path

from maintainability_audit._ranges_shell import mask_shell_lines, shell_declaration_ranges


def _ranges(source: str) -> list[tuple[int, int, str, str]]:
    found, _masked = shell_declaration_ranges(source.splitlines())
    return [(r.start, r.end, r.name, r.kind) for r in found]


def test_each_definition_form_is_a_function_bounded_by_its_braces() -> None:
    source = (
        "posix() {\n"
        "  echo one\n"
        "}\n"
        "function keyword {\n"
        "  echo two\n"
        "}\n"
        "function both() {\n"
        "  echo three\n"
        "}\n"
    )

    assert _ranges(source) == [
        (1, 3, "posix", "function"),
        (4, 6, "keyword", "function"),
        (7, 9, "both", "function"),
    ]


def test_a_body_may_open_on_the_next_line() -> None:
    """The brace-on-its-own-line style, common in older scripts."""
    source = "setup()\n{\n  mkdir -p out\n}\necho done\n"

    assert _ranges(source) == [(1, 4, "setup", "function")]


def test_a_subshell_body_is_bounded_by_its_parentheses() -> None:
    """`name() ( … )` runs the body in a subshell. It is still the body."""
    source = "isolated() (\n  cd /tmp\n  ls\n)\nafter() {\n  :\n}\n"

    assert _ranges(source) == [
        (1, 4, "isolated", "function"),
        (5, 7, "after", "function"),
    ]


def test_namespaced_and_hyphenated_names_are_read_whole() -> None:
    """`lib::log` is the Google style guide's package form; bash allows `-`."""
    source = "lib::log() {\n  :\n}\nmy-helper() {\n  :\n}\n"

    assert [name for _s, _e, name, _k in _ranges(source)] == ["lib::log", "my-helper"]


def test_a_nested_definition_is_part_of_its_parent() -> None:
    """Stepped over, as a local function is in every other language here."""
    source = "outer() {\n  inner() {\n    :\n  }\n  inner\n}\n"

    assert _ranges(source) == [(1, 6, "outer", "function")]


def test_a_heredoc_is_text_whatever_it_contains() -> None:
    source = (
        "emit() {\n"
        "  cat <<'EOF'\n"
        "fake() {\n"
        "}\n"
        "EOF\n"
        "  echo after\n"
        "}\n"
    )

    assert _ranges(source) == [(1, 7, "emit", "function")]


def test_an_indented_heredoc_ends_at_its_tab_stripped_terminator() -> None:
    """`<<-` strips leading tabs, so the terminator may be indented."""
    source = "emit() {\n\tcat <<-END\n\t}\n\tEND\n\techo after\n}\n"

    assert _ranges(source) == [(1, 6, "emit", "function")]


def test_a_brace_inside_a_string_does_not_close_the_body() -> None:
    source = (
        "quote() {\n"
        "  echo \"}\"\n"
        "  echo '}'\n"
        "  echo done\n"
        "}\n"
    )

    assert _ranges(source) == [(1, 5, "quote", "function")]


def test_a_double_quoted_string_may_span_lines() -> None:
    source = 'usage() {\n  echo "run it\n}\n  like this"\n}\n'

    assert _ranges(source) == [(1, 5, "usage", "function")]


def test_a_commented_out_definition_is_not_a_definition() -> None:
    source = "# old() {\n#   :\n# }\nreal() {\n  :\n}\n"

    assert _ranges(source) == [(4, 6, "real", "function")]


def test_the_argument_count_and_a_length_are_not_comments() -> None:
    """`$#` and `${#x}` are code; masking from them hides what follows."""
    masked = mask_shell_lines([
        'if [ $# -eq 0 ]; then exit 1; fi',
        'n=${#items[@]}; if [ "$n" -gt 1 ]; then :; fi',
        'echo hi # a real comment with if in it',
    ])

    assert "then exit 1; fi" in masked[0]
    assert "then :; fi" in masked[1]
    assert "if in it" not in masked[2] and "echo hi" in masked[2]


def test_a_path_glob_is_not_a_c_comment() -> None:
    """`/*` opens nothing in shell, and must not blank what follows."""
    masked = mask_shell_lines(['rm -rf "$dir"/* && echo cleaned', "echo next"])

    assert "&& echo cleaned" in masked[0]
    assert masked[1] == "echo next"


def test_masking_preserves_every_line_length() -> None:
    """Reported line numbers and columns must still match the source."""
    source = ['a() {', '  cat <<EOF', 'text }', 'EOF', '  echo "x # y"  # note', '}']

    assert [len(line) for line in mask_shell_lines(source)] == [len(line) for line in source]


def test_a_shell_file_is_graded_end_to_end(tmp_path: Path) -> None:
    """Every suffix the language uses reaches this scanner."""
    from maintainability_audit.config import DEFAULT_CONFIG
    from maintainability_audit.declarations import detect_functions

    body = "deploy() {\n  if [ -n \"$1\" ]; then\n    echo \"$1\"\n  fi\n}\n"
    for suffix in (".sh", ".bash", ".zsh"):
        path = tmp_path / f"script{suffix}"
        path.write_text(body, encoding="utf-8")
        found = detect_functions(tmp_path, path, body.splitlines(), DEFAULT_CONFIG["thresholds"])

        assert [(m.name, m.lines, m.complexity) for m in found] == [("deploy", 5, 2)], suffix


def test_the_default_configuration_opens_shell() -> None:
    """Parsed and listed go together; see `_config_defaults`."""
    from maintainability_audit.config import DEFAULT_CONFIG

    listed = set(DEFAULT_CONFIG["paths"]["include_extensions"])
    assert {".sh", ".bash", ".zsh"} <= listed
