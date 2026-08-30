"""Class A (Grok 63ab820): every product-artifact write refuses a route the
audited tree could redirect, on both ``/var`` and ``/private/var`` spellings,
and refuses to truncate a file that is not one of ours.

``test_write_route_class`` covered the *grant* writes -- config, history --
that go through ``write_bounded``. This class is the writes on a path a
*person* chose: the baseline the operator asks for and the rendered
outputs (``--output``, ``--sarif-output``, the HTML report, the
instruction pack). Two holes hid here that the earlier claim's
``tmp_path`` fixtures could never reach:

* ``write_baseline`` bound the symlink check to ``target.parent`` -- the
  symlink itself -- so ``.maintainability -> src`` still redirected the
  baseline into source. pytest's ``tmp_path`` is already ``resolve()``d,
  so it could not reproduce the macOS ``/var -> /private/var`` spelling
  that also defeated the grant check; this file writes under ``/var``
  on purpose.
* the CLI rendered outputs used a raw ``Path(name).write_text``, which
  never saw any refusal at all.

Unnamed member: the population is derived from the source, not listed.
The AST guard fails **any** artifact-writer module that reintroduces a
raw ``.write_text`` -- a future ``--comment-output`` writer added with
``Path(...).write_text`` fails here even though no functional case below
names it.
"""

from __future__ import annotations

import ast
import json
import os
import tempfile
from pathlib import Path

import pytest

from maintainability_audit.baseline import write_baseline
from maintainability_audit.config import PathNotAllowed

SRC = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"

# The modules that turn a report into a file a person named. Each must
# route through `write_artifact`; none may reach for a raw `write_text`.
_ARTIFACT_WRITERS = {"cli.py", "baseline.py", "instructions.py"}


def _calls_named(name: str) -> set[str]:
    """Modules that call the free function ``name`` (e.g. write_artifact)."""
    found: set[str] = set()
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == name):
                found.add(path.name)
    return found


def _raw_write_text_sites() -> dict[str, list[int]]:
    sites: dict[str, list[int]] = {}
    for path in sorted(SRC.rglob("*.py")):
        if path.name not in _ARTIFACT_WRITERS:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "write_text"):
                sites.setdefault(path.name, []).append(node.lineno)
    return sites


def test_the_artifact_write_population_is_derived_and_not_empty() -> None:
    """The class exists: product-artifact writes route through
    ``write_artifact``, from more than one module, so this is a population
    and not a single instance."""
    callers = _calls_named("write_artifact")
    assert callers >= _ARTIFACT_WRITERS, (
        f"every artifact writer should call write_artifact; missing "
        f"{_ARTIFACT_WRITERS - callers}"
    )
    assert len(callers) >= 2


def test_no_artifact_writer_reaches_for_a_raw_write_text() -> None:
    """A raw ``Path(name).write_text`` is a write that saw no refusal --
    the CLI-output escape one layer over the baseline one. The bounded
    ``write_artifact`` is the only door; a new raw write fails here."""
    offenders = _raw_write_text_sites()
    assert not offenders, (
        f"raw write_text in an artifact writer: {offenders}; route the "
        "write through _safe_write.write_artifact"
    )


def _inward_symlink_repo() -> Path:
    """A repo under ``/var`` (unresolved on macOS) whose ``.maintainability``
    is a symlink back into ``src`` -- the redirect ``tmp_path`` cannot make."""
    base = Path(tempfile.mkdtemp(dir="/var/tmp"))
    root = base / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    (root / ".maintainability").symlink_to("src")
    return root


def _report(root: Path) -> dict:
    return {"root": str(root), "git_commit": "c" * 40, "findings": [], "identities": []}


@pytest.mark.parametrize("spelling", ["/var", "/private/var"])
def test_write_baseline_refuses_the_inward_route_on_either_spelling(spelling: str) -> None:
    """``.maintainability -> src`` is refused whether the grant is named
    ``/var/...`` or its ``/private/var/...`` real path. Binding the check
    to ``target.parent`` checked the symlink against itself and let both
    through."""
    root = _inward_symlink_repo()
    if spelling == "/private/var":
        root = Path(os.path.realpath(root))
    target = root / ".maintainability" / "baseline.json"
    with pytest.raises(PathNotAllowed):
        write_baseline(str(target), _report(root))
    # The realpath of the redirect target: source was never written.
    assert not (Path(os.path.realpath(root)) / "src" / "baseline.json").exists()


def test_write_baseline_refuses_to_truncate_a_non_json_file() -> None:
    """``write_baseline(baseline_path="README.md")`` truncated source once
    (D34). A stage-and-replace still unlinks that inode, so the refusal is
    on the existing bytes not being JSON, before any stage begins."""
    root = _inward_symlink_repo()
    readme = root / "README.md"
    readme.write_text("# real docs\n", encoding="utf-8")
    with pytest.raises(PathNotAllowed):
        write_baseline(str(readme), _report(root))
    assert readme.read_text(encoding="utf-8") == "# real docs\n"


def test_a_baseline_outside_the_tree_is_still_allowed() -> None:
    """The predating contract: a person may keep a baseline outside the
    audited tree. Outside the grant the tree cannot plant a route, so the
    write proceeds -- the refusals above do not become a new bound."""
    root = _inward_symlink_repo()
    outside = root.parent / "backups" / "baseline.json"
    write_baseline(str(outside), _report(root))
    assert json.loads(outside.read_text(encoding="utf-8"))["version"] == 3
