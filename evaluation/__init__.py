"""Track D benchmark: scored, repeatable evaluation.

Scaffolded in the Phase B4 architecture reset. **Not implemented.**

This is the reserved home for the scored benchmark that ingestion pilots were
never it. Those pilots live in
``docs/archive/ingestion-pilots/`` and their runners in
``scripts/ingestion-evals/``; neither is scored and neither is repeatable
without a live provider or model download.

A Track D benchmark must be:

* **scored** — a numeric result per case, not a JSON report of raw predictions,
* **repeatable** — deterministic fixtures, fixed seeds, no live provider calls,
* **public-interface-only** — it calls the HTTP API or a package interface, never
  ``Worker`` internals or SQL, which several current evaluators do.

See ``docs/audit/CURRENT_ARCHITECTURE.md`` section 12.
"""

from .contracts import (
    BenchmarkCase,
    BenchmarkResult,
    BenchmarkSuite,
    BenchmarkRunner,
    run,
)

__all__ = [
    "BenchmarkCase",
    "BenchmarkResult",
    "BenchmarkRunner",
    "BenchmarkSuite",
    "run",
]