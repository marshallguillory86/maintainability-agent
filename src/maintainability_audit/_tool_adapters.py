"""The registry of hand-written adapters, and the lookup over it.

Deliberately thin. It names which tools have bespoke integrations and
nothing else, so adding one touches this file and the module holding the
class — never the shared plumbing in ``_adapters``.

Split by emitter kind, which is the distinction the whole design turns
on: a metric emitter can supply denominators, a verdict emitter cannot.
"""

from __future__ import annotations

from collections.abc import Callable

from ._adapters import BaseAdapter
from ._metric_adapters import (
    ComplexipyAdapter,
    InterrogateAdapter,
    JscpdAdapter,
    LizardAdapter,
    MultimetricAdapter,
    RadonAdapter,
)
from ._verdict_adapters import (
    EslintAdapter,
    PydocstyleAdapter,
    RuffAdapter,
    VultureAdapter,
)

ADAPTERS: dict[str, Callable[[], BaseAdapter]] = {
    "complexipy": ComplexipyAdapter,
    "eslint": EslintAdapter,
    "interrogate": InterrogateAdapter,
    "jscpd": JscpdAdapter,
    "lizard": LizardAdapter,
    "multimetric": MultimetricAdapter,
    "pydocstyle": PydocstyleAdapter,
    "radon": RadonAdapter,
    "ruff": RuffAdapter,
    "vulture": VultureAdapter,
}


def adapter_for(slug: str) -> BaseAdapter | None:
    """The hand-written adapter for one slug, or None.

    Only the bespoke ones. Declared tools live in ``_generic``, and
    composing the two is ``_analysis``'s job — reaching for ``_generic``
    from here would make the two modules mutually dependent, which the
    acyclicity test catches and is right to.
    """
    factory = ADAPTERS.get(slug)
    return factory() if factory else None
