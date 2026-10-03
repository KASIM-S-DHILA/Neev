"""Placeholder contracts for the Track D benchmark scaffold.

Skipped, for the same reason as services/tests/test_scaffold.py: naming the
surface is useful, asserting nothing is not. Each skip names the milestone.

There is no suite, no fixture and no runner yet. See evaluation/README.md.
"""

import unittest


class BenchmarkContractTest(unittest.TestCase):
    @unittest.skip("not implemented: track D benchmark")
    def test_case_cannot_reach_beyond_its_named_public_interface(self):
        raise NotImplementedError

    @unittest.skip("not implemented: track D benchmark")
    def test_suite_runs_offline_without_a_live_provider(self):
        raise NotImplementedError

    @unittest.skip("not implemented: track D benchmark")
    def test_passing_is_derived_from_expectations_not_asserted_by_the_case(self):
        raise NotImplementedError