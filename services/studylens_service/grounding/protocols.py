"""Contracts for grounded answering.

Interfaces only. Every function raises ``NotImplementedError`` and nothing in the
application calls them yet.

ponytail: the five-state evidence enum is deliberately explicit rather than a
confidence float. A float cannot be cited or refused; a state can.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, Sequence

from ..knowledge.protocols import RetrievalHit, RetrievalQuery


class EvidenceState(Enum):
    """How much a single citation can be trusted.

    The renderer must show this. It is the student's only signal that an answer
    rests on unverified material.
    """

    VERIFIED = "verified"
    """Locator checked against the stored original and content hash."""

    UNVERIFIED = "unverified"
    """Real extracted text, but never checked against the original."""

    MODEL_DERIVED = "model_derived"
    """Produced by a model, not present in the source text."""

    INSUFFICIENT = "insufficient"
    """Retrieved, but does not support the claim."""

    REFUSED = "refused"
    """No eligible evidence; the answer must decline rather than guess."""


@dataclass(frozen=True)
class Citation:
    """One claim-to-source link with an exact locator."""

    source_version_id: str
    content_unit_id: str
    locator: dict
    quote: str
    state: EvidenceState
    prompt_version: str | None = None


@dataclass(frozen=True)
class GroundedAnswer:
    """A composed answer plus the evidence it rests on.

    ``answer_text`` is model output and is always unverified. It never replaces
    ``content_units.text``; the existing pipeline already keeps those separate
    and this contract preserves that.
    """

    answer_text: str
    citations: Sequence[Citation] = field(default_factory=tuple)
    refused: bool = False

    def weakest_state(self) -> EvidenceState:
        """Return the least trustworthy citation state present.

        An answer is only as strong as its weakest citation. Used by the
        renderer to decide whether to show a review banner.
        """
        if not self.citations:
            return EvidenceState.REFUSED
        return max(
            (citation.state for citation in self.citations),
            key=lambda state: _SEVERITY[state],
        )


_SEVERITY = {
    EvidenceState.VERIFIED: 0,
    EvidenceState.UNVERIFIED: 1,
    EvidenceState.MODEL_DERIVED: 2,
    EvidenceState.INSUFFICIENT: 3,
    EvidenceState.REFUSED: 4,
}


class GroundingService(Protocol):
    """The contract an answer composer will implement."""

    def answer(self, query: RetrievalQuery, hits: Sequence[RetrievalHit]) -> GroundedAnswer:
        """Compose an answer, citing each claim, or refuse."""
        raise NotImplementedError


def compose(query: RetrievalQuery, hits: Sequence[RetrievalHit]) -> GroundedAnswer:
    """Compose a grounded answer. Not implemented."""
    raise NotImplementedError