"""What this repository uploads to code scanning is what should become an alert (D187).

secure-code-agent writes two SARIF documents (its D22). `--sarif-output` is the
record: every result, a suppressed one carrying its `suppressions` entry and
reason. `--code-scanning-sarif-output` is the same document without the
suppressed results — the test tree, documentation, and every reviewed
`.scignore.yaml` entry.

The difference matters because code scanning opens an alert for every result it
is handed, `suppressions` array or not, and this repository's branch protection
requires every resulting review thread resolved before a merge. Uploading the
record put seventeen threads on one pull request, all of them `assert` in a
pytest file, and blocked it. That is not a one-off: it is the outcome for every
pull request that adds a test, forever, and the shape secure-code-agent already
fixed upstream and this repository had not adopted.

Nothing is hidden by the change. The record is still written, still kept as a
build artifact, and still carries every finding; so do the JSON report, the
Markdown report and the work order. What changes is which document becomes
somebody's blocking alert.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

#: The record. Never the thing uploaded to code scanning.
_RECORD = "secure-code.sarif"
#: The filtered document, which is.
_FILTERED = "secure-code.code-scanning.sarif"


def _uploads() -> list[tuple[str, str]]:
    """Every `sarif_file:` value handed to the code-scanning upload action."""
    found = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        for match in re.finditer(r"^\s*sarif_file:\s*(\S+)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE):
            found.append((path.name, match.group(1)))
    return found


def test_the_security_record_is_never_uploaded_to_code_scanning() -> None:
    """The record carries the test tree; code scanning turns each one into a thread."""
    uploads = _uploads()
    assert uploads, "no workflow uploads SARIF; this sweep would pass vacuously"
    record = [(name, value) for name, value in uploads if value == _RECORD]
    assert not record, (
        f"the full secure-code-agent record is uploaded to code scanning: {record}. "
        "Every suppressed finding becomes an alert, and under this repository's "
        "required-conversation-resolution policy, a blocking review thread."
    )


def test_the_filtered_document_is_what_is_uploaded() -> None:
    """Proving the record is absent is not proving the right file is present."""
    uploaded = {value for _, value in _uploads()}
    assert _FILTERED in uploaded, (
        f"no workflow uploads {_FILTERED}; the security findings that should "
        "become alerts would reach code scanning from nowhere"
    )


def test_the_audit_asks_the_delegate_to_write_the_filtered_document() -> None:
    """An upload step naming a file nothing writes fails the job, loudly but late."""
    writing = [
        path.name
        for path in sorted(WORKFLOWS.glob("*.yml"))
        if f"--code-scanning-sarif-output {_FILTERED}" in path.read_text(encoding="utf-8")
    ]
    assert writing, (
        f"no workflow passes --code-scanning-sarif-output {_FILTERED}; the upload "
        "step would name a file the security audit never produced"
    )


def test_the_filtered_document_is_not_committed() -> None:
    """Generated per run, like every other audit output this repository writes."""
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert _FILTERED in ignored, f"{_FILTERED} is not in .gitignore"
