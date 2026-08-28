"""D85: the version string is a claim, and follows the evidence.

An audit preparing v1.0 acceptance testing found the artifact naming
itself `0.9.1` and `Development Status :: 3 - Alpha`. A tester running
8.8 would report a version that is not the thing under test, and this
project has already shipped nine releases whose contents did not match
what they claimed (D23).

Two properties, because two different things can drift.

*Agreement*: `pyproject`, `config.VERSION` and `__init__.__version__`
are three copies of one fact and have to say the same thing.

*Earned*: `docs/release-plan.md` tags 1.0 at 8.10, after acceptance
(8.8) and a hostile audit of the artifact that passed it (8.9). So a
plain `1.0.0` may not appear here while those gates are open. A release
candidate may -- that is what a candidate is.
"""

from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "release-plan.md"


def _declared() -> str:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return metadata["project"]["version"]


def test_every_copy_of_the_version_says_the_same_thing() -> None:
    """Three files hold one fact."""
    from maintainability_audit import __version__
    from maintainability_audit.config import VERSION

    declared = _declared()
    assert declared == VERSION and __version__ == declared, (
        f"pyproject says {declared!r}, config.VERSION says {VERSION!r}, "
        f"__init__ says {__version__!r}"
    )


def test_a_final_1_0_0_is_not_claimed_before_its_gates_close() -> None:
    """8.10 tags 1.0; nothing else gets to.

    A candidate suffix is allowed and is the honest name for an artifact
    under acceptance testing. A bare `1.0.0` is the tag, and the tag is
    the last step of the plan rather than a decision taken here.
    """
    declared = _declared()
    if not re.fullmatch(r"1\.0\.0", declared):
        return

    plan = PLAN.read_text(encoding="utf-8")
    gate = next(line for line in plan.splitlines() if line.startswith("| 8.10"))
    assert "Only after 8.9" not in gate, (
        "the package calls itself 1.0.0 while release-plan 8.10 still says "
        f"the tag waits on 8.9: {gate}"
    )


def test_the_maturity_classifier_matches_the_version() -> None:
    """Alpha, Beta and Production are claims about the same artifact."""
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    status = [
        c for c in metadata["project"]["classifiers"]
        if c.startswith("Development Status")
    ]
    assert len(status) == 1, status
    declared = _declared()

    if declared.startswith("1.") and "rc" in declared:
        expected = "Development Status :: 4 - Beta"
    elif declared.startswith("1.") or declared.startswith("2."):
        expected = "Development Status :: 5 - Production/Stable"
    else:
        expected = "Development Status :: 3 - Alpha"
    assert status[0] == expected, (
        f"version {declared!r} against {status[0]!r}; a release candidate "
        "for 1.0 is not Alpha, and a released 1.0 is not Beta"
    )


def test_security_support_covers_the_shipped_version() -> None:
    """A version nobody supports is a version nobody should install."""
    supported = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    declared = _declared()
    series = declared.split("rc")[0]
    family = ".".join(series.split(".")[:2])
    assert f"`{family}" in supported or f"`{declared}" in supported, (
        f"SECURITY.md does not list {declared} as supported"
    )


def _every_declared_copy() -> dict[str, str]:
    """Every file that states the package version, found by sweep.

    Not a hand-typed list of three. D100's claim quantifies over *every*
    copy, so the population is derived: a fourth holder added tomorrow
    is covered without anyone remembering this test exists.
    """
    literal = re.compile(r'(?:^version|\bVERSION|__version__)\s*=\s*"([^"]+)"', re.M)
    found: dict[str, str] = {}
    for path in [ROOT / "pyproject.toml", *sorted((ROOT / "src").rglob("*.py"))]:
        for match in literal.finditer(path.read_text(encoding="utf-8")):
            found[str(path.relative_to(ROOT))] = match.group(1)
    return found


def _latest_release_tag() -> str:
    """The newest release tag, read from git rather than from a plan.

    An earlier version of this check read the release plan's 8.8 row.
    That was the wrong anchor: a row in a document is a sentence anyone
    can edit, and citing it made the bar sound like it was about a 1.0
    programme. It is not. The operative fact is simpler — what has
    actually been released — and a tag is the record of that.
    """
    listed = subprocess.run(
        ["git", "-C", str(ROOT), "tag", "--list", "v*", "--sort=-v:refname"],
        capture_output=True,
        text=True,
        check=True,
    )
    tags = [line.strip() for line in listed.stdout.splitlines() if line.strip()]
    assert tags, (
        "no v* tags are visible, so release history cannot be read; this "
        "check fails rather than passing on an empty tag list, which is "
        "what a shallow clone without fetched tags would produce"
    )
    return tags[0]


def _major(version: str) -> int:
    matched = re.match(r"(\d+)", version)
    assert matched, f"version {version!r} does not begin with a number"
    return int(matched.group(1))


def test_no_copy_claims_a_major_line_above_the_latest_release() -> None:
    """D100: the version cannot outrun the releases.

    D85 promoted every copy to `1.0.0rc1` while the newest tag was
    `v0.9.1`, and its falsifier allowed it because that check only ever
    refused a bare `1.0.0`. A candidate suffix is not a smaller claim
    than the release — it is the same claim about the same major line,
    made more quietly.

    So the bar is the major line, and it is read from the tags. Nothing
    may declare 1.x until a 1.x is tagged, and on the day one is the bar
    lifts by itself. No document has a vote.
    """
    copies = _every_declared_copy()
    assert len(copies) >= 3, (
        f"the sweep found {len(copies)} version declarations; it should find "
        f"at least pyproject, config.VERSION and __init__: {copies}"
    )

    tag = _latest_release_tag()
    released = _major(tag.lstrip("v"))
    ahead = {p: v for p, v in copies.items() if _major(v) > released}
    assert not ahead, (
        f"the package declares a major line above the newest release {tag}: "
        f"{ahead}. A release candidate is still that claim."
    )
