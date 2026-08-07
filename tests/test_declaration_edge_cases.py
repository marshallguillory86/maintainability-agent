"""Lexical and structural edge cases in declaration bounding.

Split from ``test_declaration_ranges.py`` (2026-08-06), which pins the
core TypeScript detection this release fixed. What lives here is the
awkward tail: comment/string/template noise, a brace inside a regex
literal that desyncs depth counting, multi-line parameter lists, inline
object return types, and expression bodies with no brace at all.

Each one is a case where the scanner could plausibly run past the body
it belongs to. The assertions are bounds, not exact-match trivia:
under-reporting a declaration is survivable, absorbing the rest of the
file is the bug this suite exists to prevent.
"""
from __future__ import annotations

from pathlib import Path

from maintainability_audit.cli import DEFAULT_CONFIG
from maintainability_audit.declarations import detect_functions
from maintainability_audit.metrics import read_lines


def detect(tmp_path: Path, source: str, filename: str) -> dict[str, object]:
    """Return ``{name: FunctionMetric}`` for one written source file."""
    path = tmp_path / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    metrics = detect_functions(tmp_path, path, read_lines(path), DEFAULT_CONFIG["thresholds"])
    return {metric.name: metric for metric in metrics}


def test_lexical_noise_does_not_shift_bounds(tmp_path: Path) -> None:
    """Braces inside line comments, block comments, string literals, and
    multi-line template literals are text, not structure."""
    source = '''\
export function label(kind: string): string {
  // a stray { in a comment
  const brace = "}}} not code {{{";
  /* another } here */
  return `
    shape = '{ }' for ${brace}${kind}
  `;
}

export function after(): number {
  return 2;
}
'''
    found = detect(tmp_path, source, "label.ts")

    assert found["label"].lines == 8
    assert found["after"].start_line == 10
    assert found["after"].lines == 3


def test_complexity_ignores_keywords_in_comments_and_strings(tmp_path: Path) -> None:
    """Scoring runs against a masked copy, so prose about `if` and a `?`
    inside a URL are not branches."""
    source = '''\
export function label(kind: string): string {
  // if the kind is empty we still return something
  return kind || "https://example.test/x?y=1&z=2";
}
'''
    found = detect(tmp_path, source, "label.ts")

    assert found["label"].complexity == 2  # the single `||`


def test_unclosed_brace_falls_back_to_indentation(tmp_path: Path) -> None:
    """A brace inside a regex literal desyncs depth counting. Indentation
    keeps the damage to one declaration instead of the rest of the file."""
    source = '''\
export function tokenize(input: string): string[] {
  return input.split(/[{]/);
}

export function after(): number {
  return 2;
}
'''
    found = detect(tmp_path, source, "tokenize.ts")

    assert found["tokenize"].lines == 3
    assert found["after"].lines == 3


def test_multi_line_arrow_parameter_list_is_bounded(tmp_path: Path) -> None:
    """The `=>` is not on the declaration line, so the open paren depth is
    what identifies this as a function rather than an expression."""
    source = '''\
export const submit = (
  form: FormData,
  signal: AbortSignal,
) => {
  send(form, signal);
};

export function after(): number {
  return 2;
}
'''
    found = detect(tmp_path, source, "submit.ts")

    assert found["submit"].lines == 6
    assert found["after"].start_line == 8


def test_inline_object_return_type_does_not_end_the_body_early(tmp_path: Path) -> None:
    """`function stats(): { total: number } {` closes a brace before the
    body opens. The body brace that follows on the same line wins."""
    source = '''\
export function stats(): { total: number } {
  return { total: 1 };
}

export function after(): number {
  return 2;
}
'''
    found = detect(tmp_path, source, "stats.ts")

    assert found["stats"].lines == 3
    assert found["after"].start_line == 5


def test_runaway_expression_body_is_capped_not_extended(tmp_path: Path) -> None:
    """A semicolon-free chained expression has no brace to bound it. It is
    capped at the declaration line rather than allowed to run on."""
    chain = "\n".join(f'  .replace(/{char}/g, "{index}")' for index, char in enumerate("abcdefghijkl"))
    source = f'export const slug = (value: string) => value\n{chain}\n\nexport function after(): number {{\n  return 2\n}}\n'
    found = detect(tmp_path, source, "slug.ts")

    assert found["slug"].lines == 1
    assert found["after"].lines == 3


def test_html_inline_script_function_is_bounded(tmp_path: Path) -> None:
    source = '''\
<!doctype html>
<html>
  <body>
    <script>
      function boot() {
        document.title = "ready";
      }
    </script>
  </body>
</html>
'''
    found = detect(tmp_path, source, "index.html")

    assert found["boot"].lines == 3
