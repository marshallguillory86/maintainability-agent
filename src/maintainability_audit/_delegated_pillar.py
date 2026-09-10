"""Reading a delegated pillar's own report of itself.

[ADR 007](adr-007-pillars-and-practice.md) makes the five pillars of the
source framework the top-level taxonomy and declares **Security
delegated to `secure-code-agent`**, reported as `NotApplicable` so that
silence is never read as safety. That entry was always a placeholder for
an artifact that did not exist yet: the other tool measures the pillar,
so the other tool has to be the one that reports it.

`secure-code-agent` 0.5.0 ships the emitter — `--security-pillar <path>`
writes `security-pillar.json`, schema `secure-code-agent/security-pillar`
— and it was built against *this* vocabulary rather than its own. The
scope words, the two-axis split and the posture matrix with its
thresholds all come from `_pillars.py`, because two tools saying "level
3" or "healthy" about one repository have to mean the same thing by it
or the joined view is worse than either alone.

This module reads the document and checks it is the one expected. The
*shaping* of the pillar entry lives in `_pillars` beside the entries it
sits among — scoring may not import a scanner, and reading a path the
audited tree chooses is what makes this one. Neither half computes a
number: a delegated pillar's numbers belong to the tool that measured
them, and a consumer that recomputed anything would be a second opinion
nobody asked for.

**Absence is the normal case and stays the documented one.** No file
means the pillar reports exactly what it reported before — delegated,
`NotApplicable`, naming the other tool. That path is not a failure and
does not warn: most repositories run one tool.

**A file that cannot be trusted is refused rather than partly believed.**
Wrong schema, unreadable JSON, a shape that is not an object — each
returns `None`, and the pillar falls back to the honest placeholder. The
alternative is a security posture assembled from a document this tool
does not actually understand, which is worse than no posture at all.

A trailing note on where this sits: it reads a path from the audited
tree, so it is a scanner rather than part of the rubric.
`test_scoring_never_imports_scanners_or_assembly` holds that boundary,
and `report` is what joins the two.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._operator_reads import PathNotAllowed, read_source_file

#: Written beside the other artifacts a repository keeps about itself.
#: The path is a convention rather than a search: a document this tool
#: trusts for a whole pillar should be somewhere a reader can find, not
#: wherever a glob happened to match.
DEFAULT_PILLAR_PATH = ".maintainability/security-pillar.json"

#: The contract this module understands. A document announcing anything
#: else is refused rather than read hopefully — the schema string is the
#: producer's promise about the shape, and guessing past it is how a
#: consumer starts reporting fields that mean something different.
SCHEMA = "secure-code-agent/security-pillar"
SCHEMA_VERSION = 1

#: What the pillar block takes from the document. Named rather than
#: copied wholesale so a field added upstream cannot silently appear in
#: this tool's report carrying meaning nobody here has checked.
CARRIED = (
    "practice",
    "condition",
    "condition_letter",
    "posture",
    "verified_grade",
    "evidence_status",
    "evidence_reasons",
    "coverage",
    "findings_by_severity",
    "reported_not_scored",
    "loc_scanned",
)


def read_delegated(root: Path, relative: str = DEFAULT_PILLAR_PATH) -> dict[str, Any] | None:
    """The delegated pillar's own report, or `None` when there is none.

    `None` for every reason a reader might not get a usable document:
    the file is absent, it is not a regular file, it does not parse, it
    is not an object, or it announces a schema this tool does not know.
    All five collapse to one answer because the caller does the same
    thing with each — keep the placeholder that names the other tool.

    Read through the regular-file primitive like every other path the
    audited tree chooses (D145): a FIFO here would hang the audit rather
    than fail it.
    """
    path = Path(root) / relative
    if not path.exists():
        return None
    try:
        payload = json.loads("\n".join(read_source_file(path)))
    except (OSError, ValueError) as error:
        if isinstance(error, PathNotAllowed):
            raise
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema") != SCHEMA:
        return None
    if payload.get("schema_version") != SCHEMA_VERSION:
        return None
    return payload
