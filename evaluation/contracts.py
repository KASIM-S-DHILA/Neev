"""Contracts for the scored benchmark.

Interfaces only. Nothing calls them yet.

ponytail: ``BenchmarkCase`` carries ``public_interface`` so a case cannot quietly
reach into ``Worker`` or SQL. Several existing evaluators do exactly that; making
the allowed call surface an explicit field is what keeps the benchmark
comparable across refactors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, Sequence


@dataclass(frozen=True)
class BenchmarkCase:
    """One scored scenario.

    ``fixture`` must live under ``tests/fixtures/`` and be committed, so the
    case is reproducible offline. ``public_interface`` names the only entry point
    the case may use.
    """

    name: str
    fixture: str
    public_interface: str
    """For example ``GET /health`` or ``studylens_service.grounding.compose``."""

    expected: dict = field(default_factory=dict)
    """Machine-checkable expectations: route, state, citation count, and so on."""

    tags: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class BenchmarkResult:
    """One case outcome.

    ``passed`` is derived from ``expected``, never asserted by the case itself, so
    a benchmark cannot report success by writing ``passed: true``.
    """

    case: str
    passed: bool
    score: float
    detail: str = ""
    failures: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class BenchmarkSuite:
    """A named, versioned set of cases.

    ``revision`` must change whenever a case's fixture or expectation changes,
    so a score can always be tied to the exact thing that was measured.
    """

    name: str
    revision: str
    cases: Sequence[BenchmarkCase] = field(default_factory=tuple)

    def total(self) -> int:
        return len(self.cases)


class BenchmarkRunner(Protocol):
    """The contract a benchmark harness implements."""

    def run(self, suite: BenchmarkSuite) -> Sequence[BenchmarkResult]:
        """Run every case offline and return one result each."""
        raise NotImplementedError


def run(suite: BenchmarkSuite) -> Sequence[BenchmarkResult]:
    """Run a benchmark suite. Not implemented."""
    raise NotImplementedError