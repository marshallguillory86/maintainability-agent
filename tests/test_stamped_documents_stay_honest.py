"""The stamped documents are current, and their history is intact (D200).

Covers existing behaviour: both assertions pass at this change's base.
The four documents were already current, because each is guarded by its
own test after going stale once — the README line through five releases,
the Action example from 1.0.1 to 3.7.5, the SECURITY table eight release
lines. And the base commit has no stamping tool, so nothing there could
have rewritten prose.

They are here because `tools/stamp_version.py` now edits those files on
every release, which makes two new things possible: it stamps three of
four and reports success, or it edits a sentence that was never a claim
about the current version.

The second is not hypothetical. The first version of that tool matched
any `N.N.x` in `SECURITY.md` and rewrote the sentence recording that an
audit "found this table still naming `0.1.x` eight release lines later"
— erasing the evidence for the guard it was maintaining. It was caught
by reading the diff, which is not a mechanism.

Kept out of `test_version_stamping` so that file's citations stay
evidence for D200 rather than being diluted by assertions that prove
nothing it shipped.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _version() -> str:
    source = (ROOT / "src" / "maintainability_audit" / "__init__.py").read_text(
        encoding="utf-8"
    )
    return re.search(r'__version__ = "([^"]+)"', source).group(1)


def test_every_guarded_document_carries_the_version() -> None:
    """The four documents that must state it, read back from the files."""
    version = _version()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    plan = (ROOT / "docs" / "release-plan.md").read_text(encoding="utf-8")
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")

    assert f"Version **{version}**." in readme
    assert f"maintainability-agent@v{version}" in readme
    assert f"| Last tagged version | v{version} |" in plan
    assert f"| `{version.rsplit('.', 1)[0]}.x` | ✅ |" in security


def test_the_security_policy_still_records_why_it_is_guarded() -> None:
    """The sentence the first stamping tool destroyed.

    A tool that maintains a guard by deleting the reason for the guard
    has removed more than it added.
    """
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")

    assert "naming `0.1.x` eight release lines later" in security, (
        "the record of why the supported-versions table is guarded is gone"
    )
