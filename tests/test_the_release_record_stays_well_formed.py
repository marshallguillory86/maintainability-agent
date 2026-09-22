"""Guards on the release record that already held (D203, D204).

Covers existing behaviour: both assertions pass at those entries' base,
and that is the point. The release-process documents already named
`src/maintainability_audit/__init__.py` — they named it *alongside* two
files the version had left, which is the defect D203 fixed, not this.
And no version was documented twice, because only seven were documented
at all.

They are here because both properties become reachable once the
documents and the changelog are maintained rather than typed: an
instruction that says where not to write the version and never says
where to write it, and a changelog section duplicated by a backfill that
overlaps what was already there. The second is a live risk precisely
because D204 added twelve sections by hand under an existing heading.

Kept out of the two cited files so their citations stay evidence for
D203 and D204 rather than being diluted by assertions that prove nothing
those entries shipped.
"""

from __future__ import annotations

import re
from pathlib import Path

from test_the_release_process_describes_itself import _release_instruction_documents

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"

# Where a human may type the version. Everything else that carries it is
# derived (pyproject, config) or stamped from it by `tools/stamp_version.py`.
THE_ONE_WRITER = "__init__.py"


def test_every_release_instruction_names_the_one_writer() -> None:
    """Saying where not to write it is half an instruction."""
    documents = _release_instruction_documents()
    assert documents, "no document describes cutting a release, so this sweeps nothing"

    missing = [
        path.relative_to(ROOT).as_posix()
        for path in documents
        if THE_ONE_WRITER not in path.read_text(encoding="utf-8", errors="ignore")
    ]

    assert not missing, (
        f"these documents instruct a release without naming {THE_ONE_WRITER}, "
        f"the one file a person types the version into: {missing}"
    )


def test_every_documented_version_is_documented_once() -> None:
    """Two sections for one version make the extractor's output arbitrary.

    The release job's `awk` prints the lines between the matching
    heading and the next `## `, so a duplicate publishes whichever came
    first and silently drops the other.
    """
    documented = re.findall(
        r"^## (\d+\.\d+\.\d+)", CHANGELOG.read_text(encoding="utf-8"), re.MULTILINE
    )
    assert documented, "no version sections at all, so this sweeps nothing"

    seen: dict[str, int] = {}
    for version in documented:
        seen[version] = seen.get(version, 0) + 1
    repeated = sorted(version for version, count in seen.items() if count > 1)

    assert not repeated, f"CHANGELOG.md documents these versions twice: {repeated}"
