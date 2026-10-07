from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from aeon_worker.models import TaskSpec
from aeon_worker.runner import TaskRunner, TaskStore
from aeon_worker.tools import WorkspaceTools
from tests.test_aeon_worker import ScriptedProvider, action


PLAN = {"task_type": "general", "deliverables": ["answer.json"], "outcome": "Checked calculation"}
BRIEF = "Produce answer.json. Verify arithmetic using a local command."


class CommandEvidenceTests(unittest.TestCase):
    def test_explanations_do_not_require_execution_and_explicit_flag_does(self):
        self.assertFalse(TaskSpec("Explain how to verify arithmetic using a local command.", ".").require_local_check)
        self.assertFalse(TaskSpec("Do not run a local command; write a guide.", ".").require_local_check)
        self.assertTrue(TaskSpec("Produce a checked file.", ".", require_local_check=True).require_local_check)

    def test_model_verification_claim_without_command_cannot_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            provider = ScriptedProvider(PLAN, action("write_file", path="answer.json", content='{"total": 6}'), action("finish"), {"issues": []})
            result = TaskRunner(TaskStore(root / "state"), provider).start(TaskSpec(BRIEF, str(root / "workspace"), max_revisions=0))
            self.assertEqual(result["status"], "partial")
            self.assertTrue(any("local verification command" in gap for gap in result["unresolved_gaps"]))

    def test_real_check_script_proves_current_artifacts_and_survives_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            provider = ScriptedProvider(PLAN, action("write_file", path="answer.json", content='{"total": 6}'), action("write_file", path="verify.py", content="import json\nfrom pathlib import Path\nassert json.loads(Path('answer.json').read_text())['total'] == 6\n"), action("run_check", check="python_script", path="verify.py"))
            runner = TaskRunner(TaskStore(root / "state"), provider)
            spec = TaskSpec(BRIEF, str(root / "workspace"), max_steps=3)
            first = runner.start(spec)
            self.assertEqual(first["status"], "partial")
            runner.provider = ScriptedProvider(action("finish"), {"issues": []})
            result = runner.resume(spec.task_id, additional_steps=2)
            self.assertEqual(result["status"], "completed")
            state = runner.store.load(spec.task_id)
            self.assertEqual(state["command_checks"][0]["returncode"], 0)

    def test_changed_artifact_invalidates_previous_successful_check(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            provider = ScriptedProvider(PLAN, action("write_file", path="answer.json", content='{"total": 6}'), action("write_file", path="verify.py", content="import json\nfrom pathlib import Path\nassert json.loads(Path('answer.json').read_text())['total'] == 6\n"), action("run_check", check="python_script", path="verify.py"), action("write_file", path="answer.json", content='{"total": 999}'), action("finish"), {"issues": []})
            result = TaskRunner(TaskStore(root / "state"), provider).start(TaskSpec(BRIEF, str(root / "workspace"), max_revisions=0))
            self.assertEqual(result["status"], "partial")

    def test_zero_discovered_tests_are_not_successful_verification(self):
        with tempfile.TemporaryDirectory() as folder:
            tools = WorkspaceTools(Path(folder) / "workspace", Path(folder) / "evidence", TaskSpec("Write a file", folder).grant)
            result = tools.run_check("python_tests")
            self.assertEqual(result["tests_run"], 0)
            self.assertFalse(result["verification_passed"])


if __name__ == "__main__":
    unittest.main()
