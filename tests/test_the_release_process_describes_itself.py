"""The written release process matches the process the gates enforce (D203).

D198 reduced the version to one literal. D200 stamped the four documents
that have to state it. Neither touched the instructions, so for two
releases `release.yml`'s header and `CONTRIBUTING.md` both told a
releaser to bump the version in `pyproject.toml`, `__init__.py` and
`config.py` — two of which D198 had removed, and both of which the suite
now refuses. Neither named `tools/stamp_version.py`, which is the step
that replaced the chore they were describing.

That is worse than a stale comment. A person following the documented
process arrives at a red build caused by the documentation, and the
first thing anyone does with a test that fails on correct-looking work
is suspect the test. Instructions that fight the gates are how a correct
gate gets weakened.

The claim is universal and its population is derived: **no document that
walks a releaser through cutting a release may send them to a file the
version does not live in, or omit the step that writes the documents
they no longer type.** The forbidden filenames are the copies D198
removed. The documents are found by searching the tree for the act only
a release has — annotating and pushing a version tag — so a third
document growing its own copy of the process is in the population the
moment it exists.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Files that were told to hold a copy of the version and no longer do.
# Named by the defect that removed them, not by guesswork.
REMOVED_COPIES = ("pyproject.toml", "config.py")


def _release_instruction_documents() -> list[Path]:
    """Every tracked text file that walks a releaser through cutting a release.

    Identified by the step only a release process has — telling someone
    to annotate and push a version tag — rather than by a phrase like
    "bump the version", which `docs/migration-1.0.md` uses about a
    report's `schema_version`. Keying on the phrase put a document in
    this population that has nothing to do with releasing.
    """
    return sorted(
        path
        for path in [*ROOT.glob("*.md"), *(ROOT / "docs").glob("*.md"),
                     *(ROOT / ".github" / "workflows").glob("*.yml")]
        if "git tag -a v" in path.read_text(encoding="utf-8", errors="ignore")
    )


def test_no_document_sends_a_releaser_to_a_file_the_version_left() -> None:
    """The instruction and the gate have to name the same file.

    Scoped to the text around the instruction rather than the whole
    document: `CONTRIBUTING.md` legitimately mentions `pyproject.toml`
    elsewhere, and a whole-file search would force the prose to avoid a
    filename instead of avoiding the wrong instruction.
    """
    documents = _release_instruction_documents()
    # Clause two: an empty population passes every assertion below.
    assert documents, "no document describes cutting a release, so this sweeps nothing"

    offenders: list[str] = []
    for path in documents:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in re.finditer(r"bump the version", text, re.IGNORECASE):
            window = text[match.start(): match.start() + 400]
            for removed in REMOVED_COPIES:
                # A mention that says the file *derives* the version is
                # the correction, not the defect.
                if removed in window and not re.search(
                    rf"{re.escape(removed)}[^\n]*\b(deriv|re-export|reexport)", window
                ) and not re.search(
                    rf"\b(deriv|re-export|reexport)[^\n]*{re.escape(removed)}", window
                ):
                    offenders.append(f"{path.relative_to(ROOT)} → {removed}")

    assert not offenders, (
        "release instructions still send a releaser to a file that no longer "
        f"holds the version; following them fails the suite: {offenders}"
    )


def test_every_release_instruction_names_the_stamping_step() -> None:
    """The step that replaced the chore, in the document describing the chore.

    `tools/stamp_version.py` is what makes the four stamped documents
    impossible to forget, and v3.7.9 was tagged and lost its release to
    forgetting one of them by hand. A process document that omits it is
    describing the world before D200.
    """
    documents = _release_instruction_documents()
    assert documents, "no document describes cutting a release, so this sweeps nothing"

    missing = [
        path.relative_to(ROOT).as_posix()
        for path in documents
        if "stamp_version.py" not in path.read_text(encoding="utf-8", errors="ignore")
    ]

    assert not missing, (
        f"these documents describe a release without the stamping step: {missing}"
    )
