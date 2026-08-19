"""Combining several tools' readings of one concept — ADR 006.

Tools that claim the same metric disagree. Measured on this repository's
``history.py``: lizard and radon both report ``change_coupling`` at cyclomatic
complexity 13, mccabe reports 8. All three call it "cyclomatic complexity";
radon and lizard count boolean operators and comprehensions, mccabe's path
graph does not.

So a single-tool number is a measurement of that tool's counting convention,
not of the code. The response is arithmetic rather than arbitration: take a
weighted mean, keep the spread, and report both. Choosing one tool would be
choosing a convention and hiding the choice.

**Agreement only counts when the sources are independent.** Two tools agreeing
because one is derived from the other is worse than one tool alone, because it
looks like confirmation — which is why xenon, a threshold gate over radon, is
deliberately not in the pool.
"""

from __future__ import annotations

from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean

from ._metrics_types import Measurement

# Equal weight unless a tool has a stated reason to be trusted more or less
# on a concept. Deliberately the default: an unequal weight is a judgment,
# and one nobody wrote down is worse than none.
DEFAULT_WEIGHT = 1.0

# Per (concept, tool) overrides. Empty on purpose — no measurement yet
# justifies weighting any of these tools differently, and inventing one to
# make the numbers nicer is exactly what this project keeps catching itself
# doing.
TOOL_WEIGHTS: dict[tuple[str, str], float] = {}


@dataclass(frozen=True)
class Combined:
    """One concept, on one unit, as every available tool saw it."""

    concept: str
    unit: str
    value: float
    low: float
    high: float
    tools: tuple[str, ...]
    path: str = ""

    @property
    def sources(self) -> int:
        return len(self.tools)

    @property
    def spread(self) -> float:
        return self.high - self.low

    @property
    def corroborated(self) -> bool:
        """Two or more independent tools measured this.

        Not a claim that they agreed — disagreement is informative and is
        carried in the spread. This says only that more than one convention
        was consulted.
        """
        return self.sources > 1


def weight_for(concept: str, tool: str) -> float:
    return TOOL_WEIGHTS.get((concept, tool), DEFAULT_WEIGHT)


def canonical_unit(unit: str, root: Path | None = None) -> str:
    """One name for the same thing, whatever tool said it.

    Tools disagree about identity as well as about values, and without
    reconciling that, corroboration is structurally impossible — measured
    before this existed: 1465 measurements from three tools produced
    **zero** corroborated readings, because every tool spelled the unit
    differently.

    Two normalisations. Paths become repo-relative: complexipy and
    multimetric report absolute paths, lizard relative ones. And a member
    name is reduced to its final segment, because complexipy reports
    ``Class::method`` where lizard reports ``method``.
    """
    path, separator, member = unit.partition("::")
    if root is not None:
        with suppress(ValueError, OSError):
            path = str(Path(path).resolve().relative_to(root.resolve()))
    if not separator:
        return path
    return f"{path}::{member.rsplit('::', 1)[-1]}"


def _ambiguous_units(
    measurements: list[Measurement], root: Path | None
) -> set[tuple[str, str]]:
    """Units one tool reported more than once under the same canonical name.

    lizard emits bare member names, so three classes' ``version_argv`` in
    one file are indistinguishable in its output. Pooling them and calling
    the result corroboration would manufacture agreement between readings
    that are not about the same code, so these stay single-source — the
    honest limit of what these two tools can jointly establish.
    """
    seen: dict[tuple[str, str, str], int] = defaultdict(int)
    for measurement in measurements:
        key = (measurement.concept, canonical_unit(measurement.unit, root), measurement.tool)
        seen[key] += 1
    return {(concept, unit) for (concept, unit, _tool), count in seen.items() if count > 1}


def combine(measurements: list[Measurement], root: Path | None = None) -> list[Combined]:
    """Group by concept and unit, then reduce each group to one reading.

    Ordered by concept and unit so two runs produce identical output and
    diff cleanly.
    """
    ambiguous = _ambiguous_units(measurements, root)
    grouped: dict[tuple[str, str], list[Measurement]] = defaultdict(list)
    occurrence: dict[tuple[str, str, str], int] = defaultdict(int)
    for measurement in measurements:
        unit = canonical_unit(measurement.unit, root)
        if (measurement.concept, unit) in ambiguous:
            # Each occurrence becomes its own reading. Suffixing by tool
            # alone was not enough: two readings from one tool then landed
            # in the same group and the later silently replaced the
            # earlier, losing a measurement instead of preserving both.
            key = (measurement.concept, unit, measurement.tool)
            occurrence[key] += 1
            unit = f"{unit}@{measurement.tool}#{occurrence[key]}"
        grouped[(measurement.concept, unit)].append(measurement)

    combined = [_reduce(concept, unit, group) for (concept, unit), group in grouped.items()]
    return sorted(combined, key=lambda item: (item.concept, item.unit))


def _reduce(concept: str, unit: str, group: list[Measurement]) -> Combined:
    # One reading per tool by construction: a tool that reported this unit
    # more than once made it ambiguous, and `combine` has already split
    # those apart rather than pooling them into a false agreement.
    readings = {measurement.tool: measurement.value for measurement in group}

    weights = {tool: weight_for(concept, tool) for tool in readings}
    total = sum(weights.values()) or 1.0
    value = sum(readings[tool] * weights[tool] for tool in readings) / total

    return Combined(
        concept=concept,
        unit=unit,
        value=value,
        low=min(readings.values()),
        high=max(readings.values()),
        tools=tuple(sorted(readings)),
        path=group[0].path,
    )


def agreement(combined: list[Combined]) -> dict[str, float]:
    """Mean relative spread per concept, for the reported interval.

    Zero means every tool that spoke agreed exactly. Larger numbers widen
    the interval: the point is not to hide disagreement behind an average
    but to let it show as uncertainty.

    Relative rather than absolute so concepts on different scales are
    comparable — a spread of 5 means something different on cyclomatic
    complexity than on a maintainability index.
    """
    by_concept: dict[str, list[float]] = defaultdict(list)
    for item in combined:
        if not item.corroborated:
            continue
        denominator = abs(item.value) or 1.0
        by_concept[item.concept].append(item.spread / denominator)
    return {concept: fmean(spreads) for concept, spreads in by_concept.items()}


def single_source_concepts(combined: list[Combined]) -> set[str]:
    """Concepts only one tool spoke to.

    Reported because a lone reading carries a convention nobody checked,
    and the interval should be wider for it than for a corroborated one.
    """
    corroborated = {item.concept for item in combined if item.corroborated}
    return {item.concept for item in combined} - corroborated


def finding_identity(finding: object) -> tuple[str, int | None, str]:
    """What makes two findings the same finding — never concept alone.

    A CORRECTNESS bug filed under style and a naming convention filed
    under style share a concept and nothing else (D15). Identity is
    the located rule: path, line, and the rule that fired. Any seam
    that collapses or corroborates findings must use this, so two
    verdict emitters can only ever agree about the same defect at the
    same place — agreement manufactured from a shared concept label is
    the false corroboration ADR 006 exists to prevent. Disclosed
    limitation (close-out audit): a finding with no rule falls back to
    its message, and concept is deliberately excluded — two rule-less
    findings with equal message and location share an identity even
    across concepts. Today identity only orders the document; any
    future collapse must revisit this.
    """
    return (
        _finding_field(finding, "path") or "",
        _finding_field(finding, "line"),
        _finding_field(finding, "rule") or _finding_field(finding, "message") or "",
    )


def _finding_field(finding: object, name: str) -> object:
    if isinstance(finding, dict):
        return finding.get(name)
    return getattr(finding, name, None)


def normalize_source_path(root: Path, path: str) -> str:
    """One file, two spellings, identified against the tree (D15).

    SpotBugs reports package-relative paths (``com/foo/Bar.java``)
    where source adapters report repo-relative ones
    (``src/main/java/com/foo/Bar.java``). When the spelling does not
    exist under ``root`` but exactly one file ends with it, they are
    the same file and the repo-relative spelling wins. Zero or several
    candidates refuses the identification and returns the original —
    an ambiguous guess would relocate a finding, which is worse than
    two spellings. Disclosed limitation (close-out audit): a refusal
    is not marked — the kept spelling looks the same as an identified
    one, so a reader cannot tell "one match" from "gave up".
    """
    if not path or (root / path).exists():
        return path
    suffix = f"/{path}"
    matches = [
        candidate for candidate in root.rglob(Path(path).name)
        if candidate.as_posix().endswith(suffix)
    ]
    if len(matches) == 1:
        with suppress(ValueError):
            return matches[0].resolve().relative_to(root.resolve()).as_posix()
    return path
