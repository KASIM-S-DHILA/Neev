"""Tutoring: guided explanation and Socratic dialogue.

Scaffolded in the Phase B4 architecture reset. **Not implemented.**

The renderer labels Ask as disabled and Practice/Today as future work. There is
no tutor logic, table, or router.

The target constraint is that a tutor turn must ground in the student's own
material through :mod:`studylens_service.grounding` and must record what it did
as an append-only event in :mod:`studylens_service.learner`.

See ``docs/audit/CURRENT_ARCHITECTURE.md`` sections 9 and 12.
"""

from .protocols import TutorTurn, TutorService, next_hint

__all__ = ["TutorTurn", "TutorService", "next_hint"]