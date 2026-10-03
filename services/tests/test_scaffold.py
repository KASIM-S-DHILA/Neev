"""Placeholder contracts for the B4 scaffold.

Every test here is skipped with the milestone it belongs to. They exist so the
package layout is importable and so the eventual test surface is named, NOT to
report coverage. A placeholder that passes without asserting anything would be
worse than no placeholder.

When implementing a milestone, delete its skip and write real assertions. Do not
delete the skip without replacing the body.
"""

import unittest

from studylens_service import assessment, grounding, knowledge, learner, providers, tutor


class ScaffoldImportsTest(unittest.TestCase):
    """The packages must import cleanly, or nothing else can be scaffolded."""

    def test_packages_import_and_expose_their_contracts(self):
        self.assertTrue(knowledge.Chunk)
        self.assertTrue(knowledge.KnowledgeIndex)
        self.assertTrue(grounding.GroundedAnswer)
        self.assertTrue(grounding.EvidenceState)
        self.assertTrue(tutor.TutorTurn)
        self.assertTrue(assessment.Question)
        self.assertTrue(learner.LearnerEvent)
        self.assertTrue(providers.ProviderResponse)


class EligibilityGateTest(unittest.TestCase):
    @unittest.skip("not implemented: knowledge index")
    def test_only_verified_terminal_text_units_enter_the_index(self):
        raise NotImplementedError

    @unittest.skip("not implemented: knowledge index")
    def test_rebuilding_a_source_version_invalidates_its_chunks(self):
        raise NotImplementedError


class GroundingTest(unittest.TestCase):
    @unittest.skip("not implemented: grounding")
    def test_answer_refuses_when_no_eligible_evidence_exists(self):
        raise NotImplementedError

    @unittest.skip("not implemented: grounding")
    def test_every_claim_carries_an_exact_locator(self):
        raise NotImplementedError

    @unittest.skip("not implemented: grounding")
    def test_answer_is_only_as_strong_as_its_weakest_citation(self):
        raise NotImplementedError

    @unittest.skip("not implemented: grounding")
    def test_model_text_never_replaces_content_unit_text(self):
        raise NotImplementedError


class TutorTest(unittest.TestCase):
    @unittest.skip("not implemented: tutor")
    def test_hints_escalate_and_record_revelation(self):
        raise NotImplementedError


class AssessmentTest(unittest.TestCase):
    @unittest.skip("not implemented: assessment")
    def test_grades_are_append_only_and_carry_evidence_state(self):
        raise NotImplementedError


class LearnerModelTest(unittest.TestCase):
    @unittest.skip("not implemented: learner")
    def test_reading_completion_does_not_imply_mastery(self):
        raise NotImplementedError

    @unittest.skip("not implemented: learner")
    def test_state_is_recomputable_from_the_event_log(self):
        raise NotImplementedError


class ProviderTest(unittest.TestCase):
    @unittest.skip("not implemented: providers")
    def test_every_response_records_its_prompt_revision(self):
        raise NotImplementedError