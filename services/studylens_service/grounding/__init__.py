"""Grounded answers with citations.

Scaffolded in the Phase B4 architecture reset. **Not implemented.**

Grounded answering does not exist today. The renderer has no Ask feature backed
by retrieval; the content endpoint is an inspection API, not a corpus.

The target contract is an answer that must:

* cite every claim with an exact source locator,
* carry one of five explicit evidence states per citation,
* refuse to answer rather than invent when evidence is insufficient,
* keep model text separate from source text, never replacing it.

See ``docs/audit/CURRENT_ARCHITECTURE.md`` sections 9 and 12.
"""

from .protocols import (
    Citation,
    EvidenceState,
    GroundedAnswer,
    GroundingService,
    compose,
)

__all__ = [
    "Citation",
    "EvidenceState",
    "GroundedAnswer",
    "GroundingService",
    "compose",
]