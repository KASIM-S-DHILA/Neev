"""Learner model: an append-only event log and the state estimated from it.

Scaffolded in the Phase B4 architecture reset. **Not implemented.**

Named ``learner`` rather than ``learner_model`` so the package reads as a
domain boundary rather than a component.

Two rules shape everything here:

* Events are **append-only**. Derived state is recomputed from the log, never
  written back over it. There is no update path for a learner event.
* Reading completion is not mastery. Today's renderer shows a read checkbox and
  explicitly labels mastery as not assessed. Keep that distinction.

See ``docs/audit/CURRENT_ARCHITECTURE.md`` sections 9 and 12.
"""

from .protocols import (
    LearnerEvent,
    LearnerEventKind,
    LearnerState,
    Mastery,
    estimate,
    next_review,
)

__all__ = [
    "LearnerEvent",
    "LearnerEventKind",
    "LearnerState",
    "Mastery",
    "estimate",
    "next_review",
]