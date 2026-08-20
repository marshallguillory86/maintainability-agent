"""Install the packaged agent skill — the D12 drift fix.

The skill teaching agents how to drive this tool ships inside the
package, and this module copies it into an agent's skills directory.
The defect this closes was found in the field: the repository's skill
went chat-primary (D12) while the installed copy on the operator's
machine kept teaching the dead CLI-first recipe for three days —
nothing syncs installed copies on its own. ``--install-skill`` after
every upgrade is that sync, and the packaged copy is pinned
byte-for-byte to the repository's ``skills/`` tree by test, so the
same drift cannot reopen internally.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from .config import VERSION

_SKILL_NAME = "maintainability-agent"


def install_skill(skills_dir: Path) -> list[str]:
    """Copy the packaged skill into ``skills_dir``; return what was written.

    Overwrites on purpose: the installed copy has exactly one honest
    state — identical to the packaged one. A locally edited skill is
    drift, not customization; repository-specific rules belong in the
    repository's own instruction files, which generated standards
    already defer to.
    """
    package_root = resources.files("maintainability_audit") / "_skill_data"
    target_root = skills_dir / _SKILL_NAME
    written: list[str] = []
    for relative, entry in sorted(_files_under(package_root)):
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(entry.read_bytes())
        written.append(str(target))
    written.append(f"skill {_SKILL_NAME} synced to version {VERSION}")
    return written


def _files_under(node, prefix: str = ""):
    """Every file below a Traversable, with its relative posix path.

    ``importlib.resources`` Traversables have no ``rglob`` — an
    installed package may live in a zip, so the walk uses only the
    Traversable protocol.
    """
    for child in node.iterdir():
        relative = f"{prefix}{child.name}"
        if child.is_dir():
            yield from _files_under(child, f"{relative}/")
        else:
            yield relative, child
