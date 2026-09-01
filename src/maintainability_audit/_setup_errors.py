"""The setup precondition's one exception, on its own module so
the persist helpers and the ask surface both raise and catch it
without importing each other (#127 broke that cycle here)."""
from __future__ import annotations


class SetupRequired(RuntimeError):
    """A read was asked for a repository that has not been set up.

    The tool answers this case with questions. A resource cannot: it has
    no elicitation seam and returns text or nothing. So it refuses, and
    names the door that can ask — which is better than the alternative
    an audit found on this path, serving the fallback-tier report D26
    exists to prevent (D30).
    """
