from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from codebee_improve.engine import SelfImprovementEngine
from codebee_improve.models import CandidateStatus
from codebee_improve.review import build_review_prompt, stage_review_proposals


class ReviewTests(unittest.TestCase):
    def test_review_output_only_stages_inert_candidates(self) -> None:
        with TemporaryDirectory() as temp:
            engine = SelfImprovementEngine(Path(temp))
            staged = stage_review_proposals(
                engine,
                {
                    "memory": [{
                        "namespace": "user",
                        "content": "Prefer compact progress updates.",
                        "rationale": "Explicit durable preference",
                    }],
                    "skills": [],
                },
                provenance="session:abc",
            )

            self.assertEqual(staged[0].status, CandidateStatus.PROPOSED)
            self.assertEqual(engine.memory.list(), [])

    def test_review_prompt_marks_conversation_untrusted(self) -> None:
        prompt = build_review_prompt([{"role": "user", "content": "hello"}])
        self.assertIn("<untrusted_conversation>", prompt)
        self.assertIn("evaluation and approval", prompt)


if __name__ == "__main__":
    unittest.main()
