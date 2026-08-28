from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from codebee_improve.engine import SelfImprovementEngine
from codebee_improve.models import CandidateStatus, Evaluation


class EngineTests(unittest.TestCase):
    def test_candidate_requires_evaluation_and_approval_before_promotion(self) -> None:
        with TemporaryDirectory() as temp:
            engine = SelfImprovementEngine(Path(temp), require_approval=True)
            candidate = engine.propose_memory(
                namespace="project",
                content="Verify behavior with a representative regression test.",
                rationale="Repeated regression",
                provenance="session:test",
            )

            with self.assertRaises(PermissionError):
                engine.promote(candidate.id)

            engine.record_evaluation(
                candidate.id,
                Evaluation(
                    baseline_score=0.40,
                    candidate_score=0.85,
                    tests_passed=True,
                    security_passed=True,
                    evidence=["tests/test_engine.py"],
                ),
            )
            engine.approve(candidate.id, actor="owner")
            promoted = engine.promote(candidate.id, actor="owner")

            self.assertEqual(promoted.status, CandidateStatus.PROMOTED)
            self.assertIn(
                "representative regression",
                engine.memory.snapshot(["project"]).render(),
            )

    def test_failed_security_evaluation_cannot_be_approved(self) -> None:
        with TemporaryDirectory() as temp:
            engine = SelfImprovementEngine(Path(temp))
            candidate = engine.propose_skill(
                name="safe-refactoring",
                description="Refactor through reversible steps.",
                instructions="Run tests after each small change.",
                rationale="Reduce regressions",
                provenance="session:test",
            )
            engine.record_evaluation(
                candidate.id,
                Evaluation(
                    baseline_score=0.5,
                    candidate_score=0.9,
                    tests_passed=True,
                    security_passed=False,
                    evidence=["security review failed"],
                ),
            )

            with self.assertRaises(ValueError):
                engine.approve(candidate.id, actor="owner")

    def test_skill_rollback_restores_previous_version(self) -> None:
        with TemporaryDirectory() as temp:
            engine = SelfImprovementEngine(Path(temp), require_approval=False)
            first = engine.propose_skill(
                name="debugging",
                description="Debug systematically.",
                instructions="Reproduce, isolate, fix, verify.",
                rationale="Initial procedure",
                provenance="session:one",
            )
            engine.record_evaluation(first.id, Evaluation.passing(0.8, ["initial test"]))
            engine.promote(first.id)

            second = engine.propose_skill(
                name="debugging",
                description="Debug systematically.",
                instructions="Reproduce, isolate, add regression test, fix, verify.",
                rationale="Add regression protection",
                provenance="session:two",
            )
            engine.record_evaluation(second.id, Evaluation.passing(0.9, ["updated test"]))
            engine.promote(second.id)
            engine.rollback(second.id, actor="owner")

            self.assertNotIn("regression test", engine.skills.read("debugging").instructions)
            self.assertEqual(engine.get_candidate(second.id).status, CandidateStatus.ROLLED_BACK)

    def test_interrupted_skill_promotion_retries_without_new_version(self) -> None:
        with TemporaryDirectory() as temp:
            engine = SelfImprovementEngine(Path(temp), require_approval=False)
            candidate = engine.propose_skill(
                name="resilient-flow",
                description="Handle interrupted operations.",
                instructions="Retry using the same candidate identifier.",
                rationale="Crash safety",
                provenance="session:test",
            )
            engine.record_evaluation(candidate.id, Evaluation.passing(0.9, ["fault injection"]))

            # Simulate artifact write succeeding before lifecycle finalization.
            stored = engine._load()
            stored[candidate.id].status = CandidateStatus.PROMOTING
            engine._save(stored)
            provenance = f"candidate:{candidate.id}|{candidate.provenance}"
            engine.skills.promote(
                "resilient-flow",
                "Handle interrupted operations.",
                "Retry using the same candidate identifier.",
                provenance=provenance,
            )

            engine.promote(candidate.id)

            self.assertEqual(engine.skills.read("resilient-flow").version, 1)


if __name__ == "__main__":
    unittest.main()
