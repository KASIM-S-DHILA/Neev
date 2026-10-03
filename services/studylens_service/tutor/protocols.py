"""Contracts for tutoring.

Interfaces only. Nothing calls them yet.

ponytail: a tutor turn may reference the student's material, but it must never
write to ``content_units.text``. Source text is immutable input; tutor output is
a separate, labelled artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence

from ..grounding.protocols import Citation, GroundedAnswer


@dataclass(frozen=True)
class TutorTurn:
    """One exchange in a tutoring session."""

    role: str
    """Either ``student`` or ``tutor``."""

    text: str
    citations: Sequence[Citation] = field(default_factory=tuple)
    revealed_solution: bool = False
    """True once the tutor has given the answer outright.

    The session estimator uses this to distinguish a hint from a walkthrough.
    """


class TutorService(Protocol):
    """The contract a tutor implementation will satisfy."""

    def respond(
        self,
        workspace_id: str,
        history: Sequence[TutorTurn],
        student_message: str,
    ) -> TutorTurn:
        """Produce the next tutor turn, grounded in the student's material."""
        raise NotImplementedError


def next_hint(history: Sequence[TutorTurn]) -> str:
    """Choose how revealing the next hint should be. Not implemented.

    Escalation order intended: restate the question -> point at the concept ->
    point at the exact source location -> give a partial step -> give the
    solution. Two turns at the same level means escalate.
    """
    raise NotImplementedError