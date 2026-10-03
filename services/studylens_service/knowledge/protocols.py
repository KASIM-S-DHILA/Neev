"""Contracts for the knowledge index.

These are interfaces only. Every function here is unimplemented on purpose and
raises ``NotImplementedError``. Nothing in the application calls them yet.

ponytail: interfaces with no implementation exist so that later milestones have a
fixed contract to implement against. Delete the ones that are never needed
rather than letting the scaffold accrete.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence

# Content-unit statuses that may never enter a retrieval corpus. Mirrors
# studylens_service.schema / database content status vocabulary.
INELIGIBLE_CONTENT_STATUS = frozenset(
    {"needs_ocr", "empty", "unreadable", "too_large", "suspect"}
)


@dataclass(frozen=True)
class Chunk:
    """One indexable span of a content unit.

    ``locator`` must be the exact locator of the source content unit so a hit
    can always be traced back to where it came from. ``text_sha256`` pins the
    chunk content so an index built from changed text is detectable as stale.
    """

    source_version_id: str
    content_unit_id: str
    ordinal: int
    text: str
    text_sha256: str
    locator: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalQuery:
    """A student's question, scoped to one workspace."""

    workspace_id: str
    text: str
    subject_id: str | None = None
    topic_id: str | None = None
    limit: int = 8


@dataclass(frozen=True)
class RetrievalHit:
    """One retrieved chunk plus its score.

    ``score`` is provider/model specific and therefore comparable only within a
    single index. ``unverified`` carries the source warning state through so
    grounding can refuse to cite suspect material.
    """

    chunk: Chunk
    score: float
    unverified: bool = True
    reason: str | None = None


class KnowledgeIndex(Protocol):
    """The index contract a grounding implementation will depend on."""

    def build(self, workspace_id: str) -> int:
        """Index every eligible source version. Return the chunk count."""
        raise NotImplementedError

    def retrieve(self, query: RetrievalQuery) -> Sequence[RetrievalHit]:
        """Return ranked hits. Never return ineligible content."""
        raise NotImplementedError

    def invalidate(self, source_version_id: str) -> None:
        """Drop every chunk belonging to one source version."""
        raise NotImplementedError


def eligible_source_versions(rows: Sequence[dict]) -> Sequence[str]:
    """Select source version ids that may enter the index.

    The single eligibility gate, so that every later consumer agrees. A source
    version qualifies only when:

    * its original passed an integrity check (``verify_original`` succeeded), and
    * extraction reached a terminal ``succeeded`` or ``partial`` state, and
    * it exposes only ``text`` content units, and
    * its warnings and coverage gaps are preserved rather than dropped.

    Not implemented: it has no caller yet. It is the one place this rule may
    live, so do not re-derive it in grounding or retrieval.
    """
    raise NotImplementedError