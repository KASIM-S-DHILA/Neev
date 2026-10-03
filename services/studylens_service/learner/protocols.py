"""Contracts for the learner model.

Interfaces only. Nothing calls them yet.

ponytail: there is deliberately no ``update_mastery`` function. Mastery is
derived from the event log on demand, so there is no stored value that can drift
out of agreement with the events that produced it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Sequence

from ..grounding.protocols import EvidenceState

LearnerEventKind = Literal[
    "source_opened",
    "content_read",
    "question_answered",
    "hint_requested",
    "solution_revealed",
    "assessment_submitted",
]


@dataclass(frozen=True)
class LearnerEvent:
    """One immutable observation. Never updated, never deleted.

    ``at`` is a monotonic sequence number rather than a timestamp: reordering or
    clock skew must not be able to rewrite a learner's history.
    """

    workspace_id: str
    kind: LearnerEventKind
    topic_id: str
    at: int
    source_version_id: str | None = None
    correct: bool | None = None
    evidence_state: EvidenceState | None = None
    metadata: dict = field(default_factory=dict)


class Mastery(Enum):
    """Explicit, student-visible mastery. Never inferred from reading alone."""

    NOT_STARTED = "not_started"
    EXPOSED = "exposed"
    PRACTISED = "practised"
    PROFICIENT = "proficient"
    DECAYED = "decayed"


@dataclass(frozen=True)
class LearnerState:
    """State derived from an event log. Safe to discard and recompute."""

    workspace_id: str
    mastery_by_topic: dict[str, Mastery] = field(default_factory=dict)
    event_count: int = 0


def estimate(events: Sequence[LearnerEvent], workspace_id: str) -> LearnerState:
    """Derive learner state from the append-only log. Not implemented."""
    raise NotImplementedError


def next_review(state: LearnerState, topic_id: str) -> str:
    """Return the next review time for one topic. Not implemented.

    Intended to use a spaced-repetition schedule (FSRS-like) with forgetting
    curves, so recency alone does not drive review order.
    """
    raise NotImplementedError