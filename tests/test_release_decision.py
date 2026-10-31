"""The release decision owns version-bump releases instead of a human tag.

The workflow must be able to distinguish a merged version bump from a tag
retry without consulting GitHub state in several places. These tests pin the
small pure decision table first, so a missing or contradictory branch cannot
silently publish or create a second tag.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from release_decision import decide  # noqa: E402

VERSION = "4.2.1"


def test_main_version_bump_dispatch_releases_and_creates_the_tag() -> None:
    """A merged version bump dispatch runs the deploy and needs one new tag."""
    assert decide("workflow_dispatch", "refs/heads/main", VERSION, []) == {
        "release": True,
        "create_tag": True,
        "tag": "v4.2.1",
    }


def test_main_version_bump_dispatch_already_tagged_is_a_recovery_release() -> None:
    """A recovery dispatch still releases, but PyPI skips an existing version and no tag is cut."""
    assert decide("workflow_dispatch", "refs/heads/main", VERSION, ["v4.2.1"]) == {
        "release": True,
        "create_tag": False,
        "tag": "v4.2.1",
    }


def test_main_version_bump_push_releases_and_creates_the_tag() -> None:
    """cut-release.yml reads a merged version bump as a release that needs one new tag."""
    assert decide("push", "refs/heads/main", VERSION, []) == {
        "release": True,
        "create_tag": True,
        "tag": "v4.2.1",
    }


def test_main_push_without_version_bump_does_not_release() -> None:
    """cut-release.yml reads a merge without a version bump as no release."""
    assert decide("push", "refs/heads/main", VERSION, ["v4.2.1"]) == {
        "release": False,
        "create_tag": False,
        "tag": "v4.2.1",
    }


def test_matching_tag_push_releases_without_creating_a_tag() -> None:
    """A matching tag retry publishes the existing tag and leaves it untouched."""
    assert decide("push", "refs/tags/v4.2.1", VERSION, []) == {
        "release": True,
        "create_tag": False,
        "tag": "v4.2.1",
    }


def test_mismatched_tag_push_names_both_versions() -> None:
    """A wrong tag must fail loudly with the tag and packaged versions named."""
    with pytest.raises(ValueError, match=r"4\.2\.0.*4\.2\.1|4\.2\.1.*4\.2\.0"):
        decide("push", "refs/tags/v4.2.0", VERSION, [])


def test_workflow_dispatch_releases_without_creating_a_tag() -> None:
    """A dispatch from another branch releases, but the build's ancestry gate refuses it."""
    assert decide("workflow_dispatch", "refs/heads/recovery", VERSION, []) == {
        "release": True,
        "create_tag": False,
        "tag": "v4.2.1",
    }


def test_other_branch_push_does_not_release() -> None:
    """A push to any non-main branch must stay out of the release path."""
    assert decide("push", "refs/heads/feature", VERSION, []) == {
        "release": False,
        "create_tag": False,
        "tag": "v4.2.1",
    }
