"""Repository invariants the test suite must not violate.

The benchmark placeholder contracts are skipped, naming the surface without
asserting nothing and passing. Each skip names its milestone.

``TestIsolationTest`` is real and runs: it enforces two rules that already
broke once during the B1 cleanup. See evaluation/README.md.
"""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


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


class TestIsolationTest(unittest.TestCase):
    def test_no_test_builds_paths_under_the_docs_archive(self):
        # docs/archive/ is retained historical evidence and may be reorganised.
        # A test that depends on it couples the suite to documentation layout,
        # which already broke once: B1 moved the pilot result out from under
        # test_cloud_vision.py. Anything a test needs belongs in
        # tests/fixtures/ingestion/.
        #
        # Checks path *construction* via the AST rather than raw text, so
        # comments and error messages that name the archive as the restore
        # source do not trip the rule.
        offenders = []
        for path in sorted((ROOT / "services/tests").glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div):
                    continue
                literals = {
                    part.value
                    for part in ast.walk(node)
                    if isinstance(part, ast.Constant) and isinstance(part.value, str)
                }
                if any("archive" in literal for literal in literals):
                    offenders.append(f"{path.name}:{node.lineno}")
        self.assertEqual(
            offenders,
            [],
            "tests must not build paths under docs/archive/: " + ", ".join(offenders),
        )

    def test_every_referenced_ingestion_fixture_exists(self):
        # Catches a deleted or renamed fixture at import time rather than as a
        # mid-suite failure that looks like a product bug.
        fixtures = ROOT / "tests/fixtures/ingestion"
        expected = [
            "phase-04/digital-notes.pdf",
            "phase-04/corrupt-notes.pdf",
            "phase-04/encrypted-notes.pdf",
            "phase-04/mixed-language.txt",
            "phase-04/mixed-notes.pdf",
            "phase-04/gold.json",
            "phase-05/scan.png",
            "phase-05/gold.json",
            "phase-06/clean.wav",
            "phase-06/noisy.wav",
            "phase-06/silence.wav",
            "phase-06/tone.wav",
            "phase-06/gold.json",
            "phase-07/lecture.mp4",
            "phase-07/delayed-audio.mp4",
            "phase-07/gold.json",
            "phase-07b/slides.mp4",
            "phase-07b/whiteboard.mp4",
            "phase-07b/gold.json",
            "pilot/groq-vision-results.json",
        ]
        missing = [name for name in expected if not (fixtures / name).is_file()]
        self.assertEqual(missing, [], "missing ingestion fixtures: " + ", ".join(missing))