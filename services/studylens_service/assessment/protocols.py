"""Contracts for assessment.

Interfaces only. Nothing calls them yet.

ponytail: a Grade carries its own provenance. A model-produced grade is not the
same as a checked one, and the learner model must be able to weight them
differently without re-deriving that from a float.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, Sequence

from ..grounding.protocols import Citation, EvidenceState

QuestionKind = Literal["recall", "explain", "transfer"]


@dataclass(frozen=True)
class Question:
    """One generated question bound to the material it came from."""

    prompt: str
    kind: QuestionKind
    citations: Sequence[Citation] = field(default_factory=tuple)
    expected_points: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class Grade:
    """A graded attempt.

    ``evidence_state`` is the state of the *grading*, not of the source, so a
    perfectly sourced question can still be graded by an unverified model.
    """

    correct: bool
    score: float
    evidence_state: EvidenceState
    feedback: str
    missing_points: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class Assessment:
    """A set of questions presented as one sitting."""

    workspace_id: str
    subject_id: str
    questions: Sequence[Question] = field(default_factory=tuple)


class AssessmentService(Protocol):
    """The contract an assessment implementation will satisfy."""

    def generate(self, workspace_id: str, subject_id: str, count: int) -> Assessment:
        """Generate a grounded assessment. Raises if no eligible material."""
        raise NotImplementedError

    def grade(self, assessment: Assessment, answers: Sequence[str]) -> Sequence[Grade]:
        """Grade every answer in order."""
        raise NotImplementedError


def generate(workspace_id: str, subject_id: str, count: int) -> Assessment:
    """Generate an assessment. Not implemented."""
    raise NotImplementedError


def grade(assessment: Assessment, answers: Sequence[str]) -> Sequence[Grade]:
    """Grade an assessment. Not implemented."""
    raise NotImplementedError