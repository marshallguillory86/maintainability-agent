"""Stamping the release version touches the claims and nothing else (D200).

The version lives once in code (D198). It cannot live once in prose:
four documents have to state it, and each was guarded after going stale.
The README's version line sat at 1.0.0 through five releases; its Action
example pinned v1.0.0 from 1.0.1 to 3.7.5, and `action.yml` runs
`pip install -e "$GITHUB_ACTION_PATH"`, so that pin is what a reader
actually installs.

Those guards are right. What was wrong is that a person typed the number
into each document, and v3.7.9 was tagged and failed its release because
the release plan's row was missed — a check that only fires once the tag
exists, which is after anyone would have noticed.

**This does not improve `change_coupling`,** and the tool says so in its
own docstring. Those files still move together because they must. The
chore is removed, not the coupling.

The first version of the tool rewrote this repository's history. Its
`SECURITY.md` rule matched any `N.N.x`, including the sentence recording
that an audit "found this table still naming `0.1.x` eight release lines
later" — the evidence for the entry that explains why the row is guarded.
A stamping tool that edits prose about the past is worse than the chore
it replaces, so the rules are anchored; `test_stamped_documents_stay_honest`
holds that the sentence survives, and passes at this change's base.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "stamp_version.py"


def _run(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL)], cwd=cwd, capture_output=True, text=True, check=False
    )


def _version() -> str:
    source = (ROOT / "src" / "maintainability_audit" / "__init__.py").read_text(
        encoding="utf-8"
    )
    return re.search(r'__version__ = "([^"]+)"', source).group(1)


def test_the_tree_is_already_stamped() -> None:
    """Run on a clean checkout, it changes nothing.

    Not a tautology: it is the property that makes the tool safe to run
    at any time, and the one that fails the moment a release forgets it.
    """
    result = _run(ROOT)

    assert result.returncode == 0, result.stderr
    assert "already current" in result.stdout, result.stdout


def test_a_document_that_stops_matching_is_refused_not_skipped() -> None:
    """Silently stamping three of four is how v3.7.9 was tagged.

    A rule whose pattern no longer matches means the tool has quietly
    stopped maintaining that document. It exits non-zero and names the
    pattern rather than reporting success.
    """
    import shutil
    import tempfile

    scratch = Path(tempfile.mkdtemp())
    copy = scratch / "repo"
    copy.mkdir()
    for relative in ("README.md", "SECURITY.md", "docs/release-plan.md",
                     "src/maintainability_audit/__init__.py", "tools/stamp_version.py"):
        target = copy / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    # Remove the row one rule depends on.
    plan = copy / "docs" / "release-plan.md"
    plan.write_text(
        re.sub(r"\| Last tagged version \| v[0-9][0-9.]* \|", "", plan.read_text(encoding="utf-8")),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(copy / "tools" / "stamp_version.py")],
        cwd=copy, capture_output=True, text=True, check=False,
    )

    assert result.returncode == 1, result.stdout
    assert "Last tagged version" in result.stderr, result.stderr
