from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aeon_worker import AEONWorker, AgentRequest, CallbackAdapter, ModelReply
from aeon_worker.runner import _decision_history
from aeon_worker.tools import WorkspaceTools
from aeon_worker.models import ActionGrant
from aeon_worker.verification import InspectionCache, verify_artifacts


class SDKTests(unittest.TestCase):
    def test_history_compaction_does_not_expand_short_results(self):
        text = "x" * 2500
        rows = _decision_history([{"tool": "read_file", "result": {"content": text}}])
        self.assertLess(len(rows[0]["result"]["content"]), len(text))
        self.assertTrue(rows[0]["result"]["content"].endswith("x" * 800))

    def test_callback_runs_checked_artifact_and_receives_budget(self):
        seen = []
        def callback(request: AgentRequest) -> ModelReply:
            seen.append(request)
            if "artifacts" in request.payload and "mechanical_findings" in request.payload:
                data = {"issues": []}
            elif "available_tools" not in request.payload:
                data = {"task_type": "general", "deliverables": ["answer.json"]}
            elif not request.payload["artifacts"]:
                data = {"tool": "write_file", "args": {"path": "answer.json", "content": '{"answer": 42}'}}
            else:
                data = {"tool": "finish", "args": {}}
            return ModelReply(data, "custom", "deterministic-test", 30, 20, 10)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worker = AEONWorker(adapter=CallbackAdapter(callback), task_root=root / "state")
            result = worker.run("Produce answer.json. No web research.", root / "work")
            self.assertEqual(result["status"], "completed")
            self.assertTrue(result["audit_valid"])
            self.assertEqual(result["model_tokens"], 120)
            self.assertEqual(result["efficiency"]["model_calls"], 4)
            self.assertEqual(json.loads((root / "work" / "answer.json").read_text()), {"answer": 42})
            self.assertEqual(worker.result(result["task_id"]), result)
            self.assertTrue(all(512 <= request.max_output_tokens <= 8192 for request in seen))

    def test_custom_adapter_not_called_when_request_cannot_fit(self):
        with tempfile.TemporaryDirectory() as temporary:
            callback = unittest.mock.Mock()
            worker = AEONWorker(adapter=CallbackAdapter(callback), task_root=Path(temporary) / "state")
            result = worker.run("Produce a file", Path(temporary) / "work", max_model_tokens=100)
            callback.assert_not_called()
            self.assertEqual(result["reason"], "model_token_budget")

    def test_callback_rejects_invalid_usage_and_wraps_failures(self):
        from aeon_world.gateway import ProviderError
        adapter = CallbackAdapter(lambda request: ModelReply({}, "test", "test", -1))
        with self.assertRaisesRegex(ProviderError, "usage"):
            adapter.complete("system", {}, max_output_tokens=512)
        adapter = CallbackAdapter(lambda request: (_ for _ in ()).throw(RuntimeError("secret-credential")))
        with self.assertRaises(ProviderError) as caught:
            adapter.complete("system", {}, max_output_tokens=512)
        self.assertNotIn("secret-credential", str(caught.exception))

    def test_inspection_cache_invalidates_local_asset_changes_and_failures(self):
        html = '<html lang="en"><head><title>Test</title><meta name="viewport" content="width=device-width"><link href="style.css" rel="stylesheet"></head><body>Test</body></html>'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = WorkspaceTools(root / "work", root / "evidence", ActionGrant())
            tools.write_file("index.html", html)
            tools.write_file("style.css", "body {color: blue}")
            cache = InspectionCache()
            with patch.object(tools, "inspect_site", return_value={"issues": [], "screenshots": []}) as inspect:
                verify_artifacts(tools, ["index.html"], "website", [], inspection_cache=cache)
                verify_artifacts(tools, ["index.html"], "website", [], inspection_cache=cache)
                self.assertEqual(inspect.call_count, 1)
                tools.write_file("style.css", "body {width: 9000px}")
                inspect.return_value = {"issues": ["mobile: horizontal overflow"], "screenshots": []}
                self.assertTrue(verify_artifacts(tools, ["index.html"], "website", [], inspection_cache=cache)[0])
                verify_artifacts(tools, ["index.html"], "website", [], inspection_cache=cache)
                self.assertEqual(inspect.call_count, 3)
                self.assertEqual(cache.hits, 1)
            tools.close()

    def test_remote_inspections_are_never_cached(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = WorkspaceTools(root / "work", root / "evidence", ActionGrant())
            tools.write_file("index.html", '<html lang="en"><head><title>T</title><meta name="viewport"></head><body>T</body></html>')
            with patch.object(tools, "inspect_site", return_value={"issues": [], "screenshots": [], "remote_requests": ["https://example.com/app.js"]}) as inspect:
                cache = InspectionCache()
                for _ in range(2):
                    verify_artifacts(tools, ["index.html"], "website", [], inspection_cache=cache)
                self.assertEqual(inspect.call_count, 2)
            tools.close()

    def test_cli_smoke_and_custom_factory_work_without_model_keys(self):
        import io
        from contextlib import redirect_stdout
        from aeon_worker.cli import main
        from aeon_worker.demo import SMOKE_BRIEF
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for command in (["smoke", "--workspace", str(root / "smoke")],
                            ["--adapter", "aeon_worker.demo:create_adapter", "task", "start", "--brief", SMOKE_BRIEF, "--workspace", str(root / "custom")]):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = main(["--task-root", str(root / "state"), *command])
                self.assertEqual(code, 0, output.getvalue())
                self.assertIn('"audit_valid": true', output.getvalue())

    def test_cli_result_only_emits_one_decodable_json_object(self):
        import io
        from contextlib import redirect_stdout
        from aeon_worker.cli import main
        from aeon_worker.demo import SMOKE_BRIEF
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(["--task-root", str(root / "state"), "--adapter", "aeon_worker.demo:create_adapter",
                             "task", "start", "--result-only", "--brief", SMOKE_BRIEF, "--workspace", str(root / "work")])
            self.assertEqual(code, 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result["status"], "completed")
            self.assertTrue(result["audit_valid"])

    def test_cache_expiration_and_missing_asset_force_inspection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = WorkspaceTools(root / "work", root / "evidence", ActionGrant())
            tools.write_file("index.html", '<html lang="en"><head><title>T</title><meta name="viewport"><script src="app.js"></script></head><body>T</body></html>')
            tools.write_file("app.js", "console.log('ready')")
            with patch.object(tools, "inspect_site", return_value={"issues": [], "screenshots": []}) as inspect:
                cache = InspectionCache(ttl_seconds=0)
                for _ in range(2):
                    verify_artifacts(tools, ["index.html"], "website", [], inspection_cache=cache)
                self.assertEqual(inspect.call_count, 2)
                cache = InspectionCache()
                verify_artifacts(tools, ["index.html"], "website", [], inspection_cache=cache)
                (root / "work" / "app.js").unlink()
                findings, _ = verify_artifacts(tools, ["index.html"], "website", [], inspection_cache=cache)
                self.assertEqual(inspect.call_count, 4)
                self.assertTrue(any("Broken local link" in item.issue for item in findings))
            tools.close()

    def test_sdk_adapter_failures_leave_resumable_checkpoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            worker = AEONWorker(adapter=CallbackAdapter(lambda request: (_ for _ in ()).throw(RuntimeError())), task_root=Path(temporary) / "state")
            result = worker.run("Produce a file", Path(temporary) / "work")
            self.assertEqual(result["status"], "interrupted")
            self.assertEqual(worker.status(result["task_id"])["phase"], "plan")
            resumed = worker.resume(result["task_id"])
            self.assertEqual(resumed["status"], "interrupted")
            self.assertTrue(resumed["audit_valid"])


if __name__ == "__main__":
    unittest.main()
