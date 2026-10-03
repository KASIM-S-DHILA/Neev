"""Assessment: generate and grade questions against a student's material.

Scaffolded in the Phase B4 architecture reset. **Not implemented.**

There are no question, assessment, or grade tables. Grading must be recorded as
append-only events in :mod:`studylens_service.learner`, never by overwriting a
stored attempt.

See ``docs/audit/CURRENT_ARCHITECTURE.md`` sections 9 and 12.
"""

from .protocols import Assessment, Grade, Question, generate, grade

__all__ = ["Assessment", "Grade", "Question", "generate", "grade"]