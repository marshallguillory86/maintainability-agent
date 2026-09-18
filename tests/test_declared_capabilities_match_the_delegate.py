"""The capabilities this repository declares are ones its delegate will honour (D186).

The security pillar graded 3.82 (B+) on 68 true, permanent reports about what
this tool is: it spawns analyzer subprocesses, reads analyzer XML it did not
write, calls the SonarCloud API, and seeds a calibration bootstrap. None is a
defect and none is going to change.

`secure-code-agent.json` now declares those four, so they are reported on their
own axes rather than scored. That declaration is only worth anything if the
delegate actually honours it, and two ways of getting it wrong are silent from
this side:

* A capability name the delegate does not know declares nothing. The delegate
  refuses it at config load, so it fails the audit rather than passing
  quietly — but it fails in CI, and catching it here is cheaper.
* A delegate below the floor **refuses the whole configuration** on the
  unknown `capabilities` key, so the audit does not run — and one at 0.12.6
  routes the findings while printing no reason, which is the grade moved in
  silence that declaring was supposed to replace (secure-code-agent D25).

These read the checked-in config against the pinned range, so neither can
drift without the suite saying so.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: The first release where a declaration is both *accepted* and *disclosed*.
#: 0.12.6 accepts it and prints no reason under the axis.
_DISCLOSING_FLOOR = (0, 12, 7)

#: Every capability name secure-code-agent 0.12.7 defines.
#:
#: Copied, not imported. The two tools are independently releasable (ADR 008)
#: and this suite does not import the delegate, which the declared-imports
#: sweep enforces, and is right to.
#:
#: So this is a second source of truth, and the honest thing is to say what
#: guards it rather than to pretend it is derived. The delegate itself refuses
#: a capability name it does not define, loudly, at config load: a name that
#: drifts out of this set fails the security audit rather than passing it
#: quietly. This set exists to catch the typo in the suite instead of in CI,
#: not to be the authority on what the delegate defines.
_KNOWN_CAPABILITIES = frozenset(
    {
        "spawns_processes",
        "parses_untrusted_xml",
        "fetches_remote_urls",
        "uses_nondeterministic_randomness",
    }
)


def _config() -> dict:
    return json.loads((ROOT / "secure-code-agent.json").read_text(encoding="utf-8"))


def test_every_declared_capability_is_one_the_delegate_defines() -> None:
    """A name this repository invented routes nothing and reads as a decision."""
    declared = set(_config().get("capabilities", {}))
    assert declared, "nothing is declared; D186 records four and this would pass vacuously"
    unknown = sorted(declared - _KNOWN_CAPABILITIES)
    assert not unknown, (
        f"declared capabilities the delegate does not define: {unknown}; "
        "these route no finding and account for nothing"
    )


def test_every_declaration_states_a_reason() -> None:
    """The reason is what a reviewer reads to decide the declaration is still true."""
    declared = _config().get("capabilities", {})
    assert declared, (
        "nothing is declared, so this sweep would pass over an empty loop; "
        "D186 records four declarations and this test exists to hold their reasons"
    )
    for name, reason in declared.items():
        assert isinstance(reason, str) and reason.strip(), f"{name} declares no reason"
        assert len(reason.strip()) >= 40, (
            f"{name}'s reason is too short to be one: {reason!r}. "
            "A declaration without a statement of why is a skip with extra steps."
        )


def test_declaring_capabilities_raised_the_supported_floor() -> None:
    """Below 0.12.7 the declaration is refused outright, or accepted and unstated."""
    from maintainability_audit._security_delegate import SUPPORTED_FLOOR

    assert _config().get("capabilities"), "nothing declared; the coupling would not exist"
    assert SUPPORTED_FLOOR >= _DISCLOSING_FLOOR, (
        f"this repository declares capabilities but admits secure-code-agent "
        f"{'.'.join(map(str, SUPPORTED_FLOOR))}, which either refuses the whole "
        "configuration on the unknown key or routes the findings without printing "
        "the reason"
    )


def test_no_ci_pin_predates_the_disclosing_release() -> None:
    """The floor is a declaration; the pins are what actually runs."""
    pin = re.compile(r"secure-code-agent(?:\[[^\]]+\])?==([0-9][0-9.]*)")
    pins = [
        (path.name, found)
        for path in sorted((ROOT / ".github" / "workflows").glob("*.yml"))
        for found in pin.findall(path.read_text(encoding="utf-8"))
    ]
    assert pins, "no workflow pins the delegate; this sweep would pass vacuously"
    stale = [
        (name, found)
        for name, found in pins
        if tuple(int(part) for part in found.split(".")) < _DISCLOSING_FLOOR
    ]
    assert not stale, (
        f"CI pins a delegate that will not disclose this repository's declarations: {stale}"
    )
