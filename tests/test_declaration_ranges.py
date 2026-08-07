"""Where a JS/TS/HTML declaration ends.

Split out of ``test_audit_components.py`` (2026-08-06) so neither file
warns past the audit's own file-length threshold. Grading of what these
ranges produce lives in ``test_declaration_grading.py``.

The bug: ``_regex_function_ranges`` ended every declaration at "next
match minus one", and the pattern list could not see ``export
function``, generic signatures, or object/class methods. In a
TypeScript API client that made a 4-line ``csrfToken`` report 262 lines
and complexity 35 — the distance from its first line to end-of-file —
and graded a clean file an F. 18 of 18 function findings on that repo
were false.

Every assertion here checks a *bound*: no reported range may run past
the body it belongs to. Missing a declaration is survivable; absorbing
the rest of the file is not.
"""
from __future__ import annotations

from pathlib import Path

from maintainability_audit.cli import DEFAULT_CONFIG
from maintainability_audit.metrics import detect_functions, read_lines

TS_CLIENT = '''\
/**
 * Thin API client. Braces in this comment { } must not count.
 */
const CSRF = /(?:^|;\\s*)bh_csrf=([^;]+)/;

function csrfToken(): string {
  const match = document.cookie.match(CSRF);
  return match ? decodeURIComponent(match[1]) : "";
}

async function request<T>(method: string, path: string): Promise<T> {
  const response = await fetch(path, { method, headers: { "X-CSRF": csrfToken() } });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as T;
}

export const api = {
  get<T>(path: string): Promise<T> {
    return request<T>("GET", path);
  },
  delete<T>(path: string): Promise<T> {
    return request<T>("DELETE", path);
  },
};

export function buildQuery(params: Record<string, string>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    search.set(key, value);
  }
  return search.toString();
}

export const listAll = async (page = 1) => api.get(buildQuery({ page: String(page) }));
'''


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def detect(tmp_path: Path, source: str, filename: str) -> dict[str, object]:
    """Return ``{name: FunctionMetric}`` for one written source file."""
    path = tmp_path / filename
    write(path, source)
    metrics = detect_functions(tmp_path, path, read_lines(path), DEFAULT_CONFIG["thresholds"])
    return {metric.name: metric for metric in metrics}


# ---------------------------------------------------------------------------
# TypeScript / JavaScript
# ---------------------------------------------------------------------------

def test_short_ts_function_is_not_extended_to_end_of_file(tmp_path: Path) -> None:
    """The headline bug: `csrfToken` reported 262 lines / complexity 35.

    It is four lines. Nothing after it is part of its body.
    """
    found = detect(tmp_path, TS_CLIENT, "client.ts")

    assert found["csrfToken"].lines == 4
    assert found["csrfToken"].complexity == 2
    assert found["csrfToken"].status == "ok"


def test_export_function_is_detected(tmp_path: Path) -> None:
    """`export function` never matched the old pattern, which is why the
    declaration before it swallowed the rest of the file."""
    found = detect(tmp_path, TS_CLIENT, "client.ts")

    assert found["buildQuery"].start_line == 28
    assert found["buildQuery"].lines == 7


def test_generic_signature_is_detected(tmp_path: Path) -> None:
    """`async function request<T>(` has `<T>` between the name and the
    paren, so the old adjacency requirement missed it."""
    found = detect(tmp_path, TS_CLIENT, "client.ts")

    assert found["request"].start_line == 11
    assert found["request"].lines == 7


def test_object_literal_members_are_bounded_but_the_literal_is_not_a_function(tmp_path: Path) -> None:
    """`export const api = {` is a literal, not a function. Its methods
    are declarations, and `delete` is an ordinary name on a REST client.
    The trailing expression-bodied arrow stays one line."""
    found = detect(tmp_path, TS_CLIENT, "client.ts")

    assert "api" not in found
    assert found["get"].lines == 3
    assert found["delete"].lines == 3
    assert found["listAll"].lines == 1


def test_class_methods_and_field_arrows_are_bounded(tmp_path: Path) -> None:
    source = '''\
export class Store {
  private items: string[] = [];

  get size(): number {
    return this.items.length;
  }

  add = (item: string) => {
    this.items.push(item);
  };

  async load(key: string): Promise<void> {
    this.items = await fetch(key).then((r) => r.json());
  }
}

export function tail(): number {
  return 1;
}
'''
    found = detect(tmp_path, source, "store.ts")

    assert found["Store"].kind == "class"
    assert found["Store"].lines == 15
    assert found["size"].lines == 3
    assert found["add"].lines == 3
    assert found["load"].lines == 3
    assert found["tail"].start_line == 17


def test_calls_and_control_flow_are_not_declarations(tmp_path: Path) -> None:
    """`useEffect(() => {` opens a line with an identifier, a paren, and a
    brace — the same shape as a method. Its argument list not closing on
    the line is what gives it away. `if`/`switch`/`for`/`while` share the
    shape too, and are rejected by name."""
    source = '''\
export default function Panel(kind: string) {
  useEffect(() => {
    subscribe();
  }, []);
  describe("noop", () => {
    expect(1).toBe(1);
  });
  if (kind === "a") {
    return 1;
  }
  switch (kind) {
    case "b":
      return 2;
  }
  for (const c of kind) {
    void c;
  }
  while (false) {
    break;
  }
  return 0;
}
'''
    found = detect(tmp_path, source, "Panel.tsx")

    assert set(found) == {"Panel"}
    assert found["Panel"].lines == 22


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
