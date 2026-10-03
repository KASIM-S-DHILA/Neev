"""Knowledge index: chunking, eligibility, retrieval.

Scaffolded in the Phase B4 architecture reset. **Not implemented.**

The target pipeline is:

    eligible source versions -> chunk -> embed -> index -> retrieve -> hits

Retrieval does not exist yet. Today the closest thing is
``GET /workspaces/{id}/source-versions/{id}/content``, which is an *inspection*
API: it returns scoped ordered units including units whose status is
``needs_ocr``, ``suspect``, ``unreadable``, ``too_large`` or ``empty``. It is not
a retrieval corpus and must never be used as one.

See ``docs/audit/CURRENT_ARCHITECTURE.md`` sections 9 and 12.
"""

from .protocols import (
    Chunk,
    KnowledgeIndex,
    RetrievalHit,
    RetrievalQuery,
    eligible_source_versions,
)

__all__ = [
    "Chunk",
    "KnowledgeIndex",
    "RetrievalHit",
    "RetrievalQuery",
    "eligible_source_versions",
]