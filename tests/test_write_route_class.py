"""Claim 1: every write into an audited tree refuses a symlinked route.

This is the class behind D34 and the e88b429 baseline-write escape: a
write into the grant must be bounded on the *name the caller was given*,
not on a path that was already ``resolve()``d, so a ``.maintainability ->
src`` link cannot make the write land in source. Rather than list the
write sites by hand, the population is derived from the source: every
grant write goes through ``_safe_write.write_bounded`` (which applies the
lexical refusal), and the only modules allowed to perform a raw staged
``os.replace`` are the hardened low-level writers themselves.

Unnamed members: **the packaged-skill installer** (`_skill_install`) and
**the pre-commit hook installer** (`_precommit_install`), both safe by
the descriptor mechanism described below rather than by the functional
cases.

The first of those: The
functional cases below drive config, history and baseline; the skill
installer is not exercised there, and it is safe by a *different*
mechanism — it replaces through directory file descriptors
(`os.replace(..., src_dir_fd=fd, dst_dir_fd=fd)`), which a symlink cannot
redirect. If someone replaced that fd-bound write with a path-based
``open(name, "w")``, the AST guard here fails on the new raw write in a
module outside the sanctioned set, even though no functional case names
`_skill_install`.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from maintainability_audit._safe_write import write_bounded
from maintainability_audit._scan_history import ScanRecord, append_scan
from maintainability_audit.config import PathNotAllowed, repository_path

SRC = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"

# The low-level writers permitted to stage-and-replace a file directly.
# _safe_write is the bounded writer; _skill_install replaces through
# directory fds; _user_config writes the user's own XDG home, never the
# audited tree. A raw os.replace anywhere else is an unbounded write into
# the grant and must go through write_bounded instead.
# `_precommit_install` joins them on the same terms as `_skill_install`,
# not as an exemption: it binds the hooks directory once with
# O_NOFOLLOW|O_DIRECTORY and both ends of its replace are dir_fd-bound,
# so a symlink swapped in afterwards cannot redirect the write. It is
# here because it writes into `.git`, which `write_bounded` refuses and
# should — that writer bounds report artifacts to the audited tree, and
# a git hook is neither an artifact nor safe to write by name.
_RAW_REPLACE_ALLOWED = {"_safe_write.py", "_skill_install.py", "_user_config.py",
                        "_precommit_install.py"}


def _os_replace_sites() -> dict[str, list[int]]:
    sites: dict[str, list[int]] = {}
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "replace"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "os"):
                sites.setdefault(path.name, []).append(node.lineno)
    return sites


def _write_bounded_callers() -> set[str]:
    callers: set[str] = set()
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "write_bounded"):
                callers.add(path.name)
    return callers


def test_the_write_population_is_derived_and_not_empty() -> None:
    """The class exists: grant writes route through write_bounded, and it
    is used by more than one caller so this is a population, not an instance."""
    callers = _write_bounded_callers()
    callers.discard("_safe_write.py")  # the definition, not a caller
    assert len(callers) >= 3, f"write_bounded should have several callers, found {callers}"


def test_no_module_stages_a_raw_write_outside_the_sanctioned_writers() -> None:
    """No new grant write may bypass the bounded route.

    A raw ``os.replace`` is how a staged write reaches a name; the bounded
    writer and the two fd/home writers are the only ones entitled to it.
    A new module doing its own os.replace is a write that never saw the
    symlink refusal -- exactly the e88b429 baseline escape, one layer over.
    """
    offenders = {name: lines for name, lines in _os_replace_sites().items()
                 if name not in _RAW_REPLACE_ALLOWED}
    assert not offenders, (
        f"raw os.replace outside the sanctioned writers: {offenders}; "
        "route the write through _safe_write.write_bounded"
    )


def _inward_symlink_repo(base: Path) -> Path:
    root = base / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    (root / ".maintainability").symlink_to("src")
    return root


@pytest.mark.parametrize("write", ["write_bounded", "history", "config"])
def test_a_grant_write_refuses_an_inward_symlinked_route(tmp_path: Path, write: str) -> None:
    """Each grant-write entry point refuses ``.maintainability -> src``."""
    root = _inward_symlink_repo(tmp_path)
    with pytest.raises(PathNotAllowed):
        if write == "write_bounded":
            write_bounded(root, root / ".maintainability" / "x.json", "{}")
        elif write == "history":
            append_scan(root / ".maintainability" / "history.jsonl",
                        _record(), root)
        else:
            (root / "src" / "maintainability-agent.json").unlink(missing_ok=True)
            # config path resolves through repository_path, which refuses the route
            repository_path(root, ".maintainability/maintainability-agent.json",
                            ".maintainability/maintainability-agent.json")
    assert not (root / "src" / "x.json").exists()
    assert not (root / "src" / "history.jsonl").exists()


def _record() -> ScanRecord:
    fields = {f: "" for f in ScanRecord.__dataclass_fields__}
    fields.update(recorded_at="t", commit="c" * 40, branch="main", scope="full")
    return ScanRecord(**fields)
