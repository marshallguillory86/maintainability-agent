"""Private declarations nothing references.

Finding unreferenced code is easy to do badly. A naive "no callers" scan
reports a library's whole public surface, every framework hook, and every
dynamic-dispatch target — all of them called, just not from anywhere a
scanner can see. A finding class that is mostly wrong is worse than none,
because it teaches people to skim past the report.

Two false-positive classes surfaced when this was first run against the
reference corpus, and both are pinned below so they cannot return:

- **References inside f-strings.** The first version counted identifiers
  over the comment/string-masked copy, which blanked live code. Flask's
  ``_get_werkzeug_version`` is called from inside an f-string and was
  reported dead.
- **Object-literal methods.** ``beforeBreadcrumb(crumb) { … }`` inside a
  Sentry config object binds no name and is invoked by whoever receives
  the object. A real repo's callback was reported dead.
"""
from __future__ import annotations

from pathlib import Path

from maintainability_audit.config import load_config
from maintainability_audit.deadcode import dead_declarations
from maintainability_audit.metrics import iter_files


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def scan(root: Path) -> set[str]:
    write(root / "README.md", "# Test\n")
    return {item["name"] for item in dead_declarations(root, iter_files(root, load_config(None)))}


# ---------------------------------------------------------------------------
# What must be found
# ---------------------------------------------------------------------------

def test_an_unreferenced_private_function_is_reported(tmp_path: Path) -> None:
    write(tmp_path / "app.py", "def _orphan(value):\n    return value * 2\n\n\ndef used():\n    return 1\n")

    assert "_orphan" in scan(tmp_path)


def test_an_unexported_javascript_function_is_reported(tmp_path: Path) -> None:
    write(tmp_path / "app.ts", "function orphan(value) {\n  return value * 2;\n}\n\nexport function used() {\n  return 1;\n}\n")

    assert "orphan" in scan(tmp_path)


# ---------------------------------------------------------------------------
# What must never be reported
# ---------------------------------------------------------------------------

def test_a_public_function_is_never_reported(tmp_path: Path) -> None:
    """Privacy is the load-bearing assumption. Without it, every library's
    public surface looks dead."""
    write(tmp_path / "app.py", "def public_helper(value):\n    return value * 2\n")
    write(tmp_path / "lib.ts", "export function publicHelper(v) {\n  return v * 2;\n}\n")

    assert scan(tmp_path) == set()


def test_a_reference_inside_an_f_string_counts_as_a_use(tmp_path: Path) -> None:
    """Regression: flask's `_get_werkzeug_version` is called from inside an
    f-string and was reported dead when counting ran over masked source."""
    write(
        tmp_path / "app.py",
        'def _version():\n    return "1.0"\n\n\ndef agent():\n    return f"Tool/{_version()}"\n',
    )

    assert "_version" not in scan(tmp_path)


def test_an_object_literal_method_is_not_a_candidate(tmp_path: Path) -> None:
    """Regression: a Sentry `beforeBreadcrumb` callback binds no name and is
    called by the library that receives the object."""
    write(
        tmp_path / "main.ts",
        "init({\n  beforeBreadcrumb(crumb) {\n    if (crumb) {\n      return null;\n    }\n    return crumb;\n  },\n});\n",
    )

    assert "beforeBreadcrumb" not in scan(tmp_path)


def test_a_decorated_declaration_is_not_a_candidate(tmp_path: Path) -> None:
    """A decorator means something else calls this — a route table, a
    fixture registry — and that reference is not a visible call site."""
    write(tmp_path / "app.py", "import functools\n\n\n@functools.cache\ndef _cached(value):\n    return value\n")

    assert "_cached" not in scan(tmp_path)


def test_dunder_methods_are_never_reported(tmp_path: Path) -> None:
    """The runtime calls these; nothing in the source needs to."""
    write(tmp_path / "app.py", "class Thing:\n    def __repr__(self):\n        return 'Thing'\n")

    assert scan(tmp_path) == set()


def test_test_files_are_excluded(tmp_path: Path) -> None:
    write(tmp_path / "tests" / "test_app.py", "def _helper():\n    return 1\n")

    assert scan(tmp_path) == set()


def test_a_private_function_used_elsewhere_is_not_reported(tmp_path: Path) -> None:
    write(tmp_path / "a.py", "def _shared():\n    return 1\n")
    write(tmp_path / "b.py", "from a import _shared\n\n\ndef go():\n    return _shared()\n")

    assert "_shared" not in scan(tmp_path)
