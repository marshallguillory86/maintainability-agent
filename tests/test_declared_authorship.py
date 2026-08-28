"""Who did the work, held against the record rather than remembered.

Split out of ``test_written_record.py`` at this repository's own
file-length gate, the same way that file was split out of
``test_chat_primary_docs.py``. That one asks whether the written record
is true; this asks whether it can say who wrote it.

D100 is why. The package promoted itself to a 1.0 release candidate and,
asked who decided that, the record could only guess — every agent here
commits under the same git identity, so `git log` settles nothing.

What lives here is a declaration check, not a proof. An entry that omits
its `*Roles:*` line fails; an entry that names the wrong agent passes.
Cryptographic proof needs per-agent signing keys and
`required_signatures` on the branch, and `RULES.md` says plainly that
none of that is in place.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs/defect-register-chat-surface.md"


def test_entries_from_d89_record_who_did_the_work() -> None:
    """D100: the record has to be able to say who decided something.

    Asked who promoted the version to a 1.0 candidate, the register
    could not answer. D85 carries no `*Roles:*` line, and every agent
    here commits under the same git identity, so `git log` settles
    nothing either.

    The convention began at D89 and eleven entries have followed it
    since, on nothing but habit. This is the lint that makes it a rule.
    The cutoff is D89 because that is where the practice actually
    starts — not D100, which would be picking a number that makes the
    check easy. D1-D88 cannot be reconstructed and are left stated in
    D100 rather than invented.
    """
    register = REGISTER.read_text(encoding="utf-8")
    heads = list(re.finditer(r"^### D(\d+) — .*$", register, re.MULTILINE))
    assert heads, "no register entries found; this sweep matched nothing"

    governed = []
    missing = []
    for index, head in enumerate(heads):
        number = int(head.group(1))
        if number < 89:
            continue
        governed.append(number)
        end = heads[index + 1].start() if index + 1 < len(heads) else len(register)
        if "*Roles:*" not in register[head.start():end]:
            missing.append(f"D{number}")

    assert governed, (
        "no entry at or after D89, so this check proved nothing; it must "
        "fail rather than pass vacuously"
    )
    assert not missing, (
        "entries from D89 must record who found, fixed and tested them; "
        f"missing a *Roles:* line: {missing}"
    )
