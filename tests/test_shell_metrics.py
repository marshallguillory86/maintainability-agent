"""Shell decides in words, and closes in words, and neither is a brace.

No second implementation reads shell complexity offline — lizard 1.24.0
has no shell reader — so this reader is checked against the grammar
itself instead: every compound command and list operator POSIX defines,
and the ones bash adds, one function per construct, each with the count
the grammar implies. The list is copied from the standard, not from
memory, and the test fails if a construct on it has no specimen.

Three judgments are shell's own:

- **A keyword counts only in command position.** `echo waiting for it`
  is an unquoted argument list with `for` in it, and shell scripts are
  full of unquoted prose. `if`, `while` and the rest are reserved words
  only where a command may begin.
- **`case` is counted at its arms**, the rule shared with `switch` and
  `when` everywhere else here. `*)` is the default and is not counted, as
  Go declines `default`.
- **Nesting is read from `fi`, `done` and `esac`**, because shell's
  control structures have no braces. The brace reader would score a
  deeply nested script as flat — Fortran's defect before 1.4.0.
"""

from __future__ import annotations

import pytest

from maintainability_audit._cognitive import shell_cognitive
from maintainability_audit._metrics_types import shell_branch_points
from maintainability_audit._ranges_shell import mask_shell_lines

#: IEEE Std 1003.1-2017, XCU 2.9.3 (Lists) and 2.9.4 (Compound Commands),
#: in the standard's own order, then the constructs the Bash Reference
#: Manual adds in 3.2.5.1 (Looping Constructs) and 3.2.5.2 (Conditional
#: Constructs). The count is the decisions each construct adds.
GRAMMAR: dict[str, tuple[str, int]] = {
    # 2.9.3 Lists: an AND-OR list decides at each operator.
    "and_or_list": ("true && echo yes || echo no", 2),
    # 2.9.4 Compound Commands.
    "brace_group": ("{ echo a; echo b; }", 0),
    "subshell": ("( cd /tmp && ls )", 1),
    "for_loop": ("for x in a b; do\n  echo \"$x\"\ndone", 1),
    "case_construct": (
        "case \"$1\" in\n  start) run ;;\n  stop|halt) halt ;;\n  *) usage ;;\nesac", 2,
    ),
    "if_construct": (
        "if [ \"$a\" ]; then\n  :\nelif [ \"$b\" ]; then\n  :\nelse\n  :\nfi", 2,
    ),
    "while_loop": ("while read -r line; do\n  echo \"$line\"\ndone", 1),
    "until_loop": ("until ping -c1 host; do\n  sleep 1\ndone", 1),
    # Bash 3.2.5.1: the arithmetic `for`.
    "arithmetic_for": ("for ((i = 0; i < 3; i++)); do\n  echo \"$i\"\ndone", 1),
    # Bash 3.2.5.2: `select`, `((…))` and `[[…]]`.
    "select_construct": ("select opt in a b; do\n  break\ndone", 1),
    "arithmetic_command": ("(( count += 1 ))", 0),
    "conditional_expression": ("[[ -n \"$a\" && -z \"$b\" ]]", 1),
}

SPEC_CONSTRUCTS = (
    "and_or_list",
    "brace_group", "subshell", "for_loop", "case_construct", "if_construct",
    "while_loop", "until_loop",
    "arithmetic_for", "select_construct", "arithmetic_command", "conditional_expression",
)


def _branches(source: str) -> int:
    return sum(shell_branch_points(line) for line in mask_shell_lines(source.splitlines()))


def _cognitive(source: str) -> int:
    return shell_cognitive(mask_shell_lines(source.splitlines()))


def test_every_construct_the_grammar_defines_has_a_specimen() -> None:
    assert set(GRAMMAR) == set(SPEC_CONSTRUCTS)


@pytest.mark.parametrize("construct", SPEC_CONSTRUCTS)
def test_each_construct_counts_what_the_grammar_says_it_decides(construct: str) -> None:
    source, expected = GRAMMAR[construct]

    assert _branches(source) == expected, construct


def test_a_keyword_in_an_argument_list_is_not_a_branch() -> None:
    """Unquoted prose is ordinary shell, and it says `for` and `while`."""
    assert _branches("echo waiting for the server while it starts") == 0
    assert _branches("log if you can, until then") == 0


def test_a_keyword_after_a_separator_is_in_command_position() -> None:
    assert _branches("cd /tmp; if [ -f x ]; then rm x; fi") == 1
    assert _branches("ready && while sleep 1; do :; done") == 2


def test_the_default_arm_is_not_counted_and_the_header_is_not_either() -> None:
    source = "case \"$x\" in\n  a) : ;;\n  *) : ;;\nesac"

    assert _branches(source) == 1


def test_a_pipe_and_a_case_terminator_decide_nothing() -> None:
    assert _branches("ps aux | grep sshd | wc -l") == 0
    assert _branches("  a) run ;;") == 1


def test_a_command_substitution_is_not_an_arm() -> None:
    assert _branches("stamp=$(date +%s)") == 0
    assert _branches("result=$(cat <(ls))") == 0


def test_nesting_costs_more_than_sequence() -> None:
    """Five guards read top to bottom; five levels must be held at once."""
    flat = "\n".join(f"if [ \"$v\" = {n} ]; then\n  :\nfi" for n in range(3))
    nested = (
        "for a in x; do\n"
        "  for b in y; do\n"
        "    if [ \"$a\" = \"$b\" ]; then\n"
        "      :\n"
        "    fi\n"
        "  done\n"
        "done"
    )

    assert _cognitive(flat) == 3
    assert _cognitive(nested) == 1 + 2 + 3


def test_a_one_line_construct_opens_and_closes_on_its_line() -> None:
    """Depth must not leak past a construct written on one line."""
    source = "if [ -f a ]; then rm a; fi\nif [ -f b ]; then rm b; fi"

    assert _cognitive(source) == 2


def test_elif_and_else_cost_one_flat_point() -> None:
    source = GRAMMAR["if_construct"][0]

    assert _cognitive(source) == 1 + 1 + 1


def test_a_case_is_charged_once_at_its_depth() -> None:
    source = "while :; do\n" + GRAMMAR["case_construct"][0] + "\ndone"

    assert _cognitive(source) == 1 + 2


def test_boolean_operators_cost_a_point_each() -> None:
    assert _cognitive("[[ -n $a && -n $b ]] || exit 1") == 2


def test_a_closer_followed_by_a_redirect_still_closes() -> None:
    """`done < file` and `done | sort` are how loops are fed and read."""
    source = (
        "while read -r l; do\n  :\ndone < input\n"
        "while read -r l; do\n  :\ndone | sort\n"
        "if :; then\n  :\nfi"
    )

    assert _cognitive(source) == 3
