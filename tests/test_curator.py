from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from codebee_improve.curator import Curator
from codebee_improve.engine import SelfImprovementEngine
from codebee_improve.models import Evaluation


class CuratorTests(unittest.TestCase):
    def test_dry_run_never_mutates_and_flags_stale_skill(self) -> None:
        with TemporaryDirectory() as temp:
            engine = SelfImprovementEngine(Path(temp), require_approval=False)
            candidate = engine.propose_skill(
                name="old-procedure",
                description="Old procedure.",
                instructions="Do old thing.",
                rationale="Historical",
                provenance="session:test",
            )
            engine.record_evaluation(candidate.id, Evaluation.passing(0.8, ["test"]))
            engine.promote(candidate.id)
            old = datetime.now(timezone.utc) - timedelta(days=120)
            engine.skills.set_last_used("old-procedure", old)

            report = Curator(engine).review(stale_after_days=30, dry_run=True)

            self.assertTrue(any(a.target == "old-procedure" for a in report.actions))
            self.assertIsNotNone(engine.skills.read("old-procedure"))


if __name__ == "__main__":
    unittest.main()
