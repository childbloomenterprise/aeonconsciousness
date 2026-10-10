from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading
import unittest
import urllib.request
import uuid
from unittest.mock import patch

from aeon_enterprise.local_service import enroll, load_providers, local_origin, local_root, main
from aeon_enterprise.execute import execute
from aeon_enterprise.worker import Client, deliver
from aeon_worker.demo import create_adapter, SMOKE_BRIEF
from aeon_worker.sdk import CallbackAdapter


class LocalEnterpriseServiceTests(unittest.TestCase):
    def test_only_explicit_loopback_origins_allowed(self):
        self.assertEqual(local_origin("http://127.0.0.1:8787/"), "http://127.0.0.1:8787")
        for value in ("https://localhost:8787", "http://example.com:8787", "http://127.0.0.1", "http://localhost:8787/path", "http://user:password@localhost:8787", "http://localhost:8787?token=foo"):
            with self.assertRaises(ValueError):
                local_origin(value)

    def test_local_state_cannot_mutate_hosted_installation(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"LOCALAPPDATA": folder}):
            hosted = Path(folder) / "AEON" / "enterprise-private"
            for root in (hosted, hosted / "jobs"):
                with self.assertRaises(ValueError):
                    local_root(root)
            local_root(Path(folder) / "AEON" / "localhost-private" / "worker")

    def test_only_model_credentials_loaded_without_copying(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            file = Path(folder) / "providers.json"
            file.write_text(json.dumps({"GEMINI_API_KEY": "model", "AEON_ADMIN_KEY": "forbidden"}))
            before = file.read_bytes()
            self.assertTrue(load_providers(file))
            self.assertEqual(os.environ["GEMINI_API_KEY"], "model")
            self.assertNotIn("AEON_ADMIN_KEY", os.environ)
            self.assertEqual(file.read_bytes(), before)

    def test_enrollment_reuses_valid_identity_after_restart(self):
        origin = "http://127.0.0.1:8787"
        config = {"base_url": origin, "worker_token": "w" * 64, "worker_id": "worker_abc", "mode": "trusted-local", "site_token": ""}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch("aeon_enterprise.local_service.call", side_effect=[{"mode": "local", "persistence": True}, {}, {"workers": []}, {"connection": config}]):
                self.assertEqual(enroll(origin, root), config)
            before = (root / "worker-connection.json").read_bytes()
            with patch("aeon_enterprise.local_service.call", side_effect=[{"mode": "local", "persistence": True}, {}, {"workers": [{"id": "worker_abc", "revoked": 0}]}]) as api:
                self.assertEqual(enroll(origin, root), config)
                self.assertEqual(api.call_count, 3)
            self.assertEqual((root / "worker-connection.json").read_bytes(), before)

    def test_runtime_and_connection_scope_checked_before_enrollment(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch("aeon_enterprise.local_service.call", return_value={"mode": "production", "persistence": True}):
                with self.assertRaises(ValueError):
                    enroll("http://127.0.0.1:8787", root)
            (root / "worker-connection.json").write_text(json.dumps({"base_url": "https://hosted.example", "worker_token": "w" * 64, "mode": "trusted-local"}))
            with patch("aeon_enterprise.local_service.call", side_effect=[{"mode": "local", "persistence": True}, {}, {"workers": []}]):
                with self.assertRaises(ValueError):
                    enroll("http://127.0.0.1:8787", root)

    def test_launcher_forwards_explicit_local_authority(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            with patch("aeon_enterprise.local_service.load_providers", return_value=True), patch("pathlib.Path.is_file", return_value=True), patch("aeon_enterprise.local_service.enroll"), patch("aeon_enterprise.local_service.worker_main", return_value=0) as worker:
                self.assertEqual(main(["--state-root", str(root), "--once"]), 0)
            worker.assert_called_once_with(["--connection", str(root / "worker-connection.json"), "--state-root", str(root / "jobs"), "--trusted-local", "--allow-local", "--once"])

    def test_replayed_resume_does_not_extend_authorized_budget_twice(self):
        job = {
            "id": "job_" + "d" * 32, "brief": SMOKE_BRIEF, "grant": {},
            "max_tokens": 20000, "max_steps": 8, "max_revisions": 1,
            "deadline_minutes": 3, "attempts": 1,
        }

        def unavailable(request):
            raise RuntimeError("Synthetic provider failure")

        demo = create_adapter()

        def fail_after_artifact(request):
            if "available_tools" in request.payload and request.payload["artifacts"]:
                return unavailable(request)
            return demo.callback(request)

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(execute(job, root, adapter=CallbackAdapter(fail_after_artifact))["status"], "interrupted")
            resumed = {**job, "max_tokens": 21000, "max_steps": 10, "max_revisions": 2,
                       "deadline_minutes": 4, "attempts": 2,
                       "resume_options": {"additional_model_tokens": 1000, "additional_steps": 2,
                                          "additional_minutes": 1, "additional_revisions": 1}}
            self.assertEqual(execute(resumed, root, adapter=CallbackAdapter(unavailable))["status"], "interrupted")
            checkpoint = root / "state" / ("task-" + job["id"][4:]) / "checkpoint.json"
            first = json.loads(checkpoint.read_text())
            self.assertEqual(first["spec"]["max_model_tokens"], resumed["max_tokens"])
            self.assertEqual(execute(resumed, root, adapter=CallbackAdapter(unavailable))["status"], "interrupted")
            replayed = json.loads(checkpoint.read_text())
            self.assertEqual(replayed["spec"], first["spec"])
            self.assertEqual(replayed["deadline_at"], first["deadline_at"])
            again = {**resumed, "max_tokens": 22000, "max_steps": 12, "max_revisions": 3,
                     "deadline_minutes": 5, "attempts": 3}
            self.assertEqual(execute(again, root, adapter=CallbackAdapter(unavailable))["status"], "interrupted")
            extended = json.loads(checkpoint.read_text())
            self.assertEqual(extended["spec"]["max_model_tokens"], 22000)
            self.assertEqual(extended["spec"]["max_steps"], 12)
            self.assertEqual(extended["spec"]["max_revisions"], 3)
            self.assertEqual(extended["spec"]["deadline_minutes"], 5)

    def test_provider_failure_before_planning_resumes_with_new_authorized_limits(self):
        job = {
            "id": "job_" + "e" * 32, "brief": SMOKE_BRIEF, "grant": {},
            "max_tokens": 20000, "max_steps": 8, "max_revisions": 1,
            "deadline_minutes": 3, "attempts": 1,
        }

        def unavailable(request):
            raise RuntimeError("Synthetic provider failure before work order")

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            interrupted = execute(job, root, adapter=CallbackAdapter(unavailable))
            self.assertEqual(interrupted["status"], "interrupted")
            self.assertEqual(interrupted["reason"], "provider_unavailable")
            resumed = {**job, "deadline_minutes": 4, "attempts": 2,
                       "resume_options": {"additional_minutes": 1}}
            result = execute(resumed, root, adapter=create_adapter())
            self.assertEqual(result["status"], "completed", result)
            self.assertTrue(result["audit_valid"])

    def test_abrupt_process_death_running_checkpoint_accepts_explicit_recovery(self):
        class AbruptProcessDeath(BaseException):
            pass

        demo = create_adapter()

        def die_after_saved_artifact(request):
            if "available_tools" in request.payload and request.payload["artifacts"]:
                raise AbruptProcessDeath()
            return demo.callback(request)

        job = {"id": "job_" + "f" * 32, "brief": SMOKE_BRIEF, "grant": {},
               "max_tokens": 20000, "max_steps": 8, "max_revisions": 1,
               "deadline_minutes": 3, "attempts": 1}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises(AbruptProcessDeath):
                execute(job, root, adapter=CallbackAdapter(die_after_saved_artifact))
            checkpoint = root / "state" / ("task-" + job["id"][4:]) / "checkpoint.json"
            self.assertEqual(json.loads(checkpoint.read_text())["status"], "running")
            recovered = {**job, "deadline_minutes": 4, "attempts": 2,
                         "resume_options": {"additional_minutes": 1}}
            result = execute(recovered, root, adapter=create_adapter())
            self.assertEqual(result["status"], "completed", result)
            self.assertTrue(result["audit_valid"])

    def test_terminal_checkpoint_survives_crash_before_result_file_write(self):
        class AbruptProcessDeath(BaseException):
            pass

        from codebee_improve.storage import atomic_write_json

        def die_before_result_write(path, payload):
            if path.name == "result.json" and payload.get("status") == "completed":
                raise AbruptProcessDeath()
            atomic_write_json(path, payload)

        demo = create_adapter()

        def fail_after_artifact(request):
            if "available_tools" in request.payload and request.payload["artifacts"]:
                raise RuntimeError("Synthetic interrupted result retained before completion")
            return demo.callback(request)

        job = {"id": "job_" + "c" * 32, "brief": SMOKE_BRIEF, "grant": {},
               "max_tokens": 20000, "max_steps": 8, "max_revisions": 1,
               "deadline_minutes": 3, "attempts": 1}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            interrupted = execute(job, root, adapter=CallbackAdapter(fail_after_artifact))
            self.assertEqual(interrupted["status"], "interrupted")
            with patch("aeon_worker.runner.atomic_write_json", side_effect=die_before_result_write):
                with self.assertRaises(AbruptProcessDeath):
                    execute(job, root, adapter=create_adapter())
            checkpoint = root / "state" / ("task-" + job["id"][4:]) / "checkpoint.json"
            self.assertEqual(json.loads(checkpoint.read_text())["status"], "completed")
            self.assertEqual(json.loads(checkpoint.with_name("result.json").read_text())["status"], "interrupted")
            result = execute(job, root, adapter=CallbackAdapter(
                lambda request: self.fail("Durable terminal result must not invoke provider")))
            self.assertEqual(result["status"], "completed", result)
            self.assertTrue(result["audit_valid"])


class IsolatedLocalLifecycleTests(unittest.TestCase):
    """Real HTTP bridge and checkpoint recovery; never connect to a user queue."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aeon-recovery-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = Path(__file__).resolve().parents[1]
        self.node = shutil.which("node")
        if not self.node or not (self.repo / "enterprise/node_modules/hono").exists():
            self.skipTest("Node 24+ and enterprise dependencies required for isolated HTTP bridge")
        self.process = None
        self.addCleanup(self.stop_server)
        self.start_server()

    def start_server(self, port=0):
        script = """
import { api } from API_URL;
import { createLocalServer } from SERVER_URL;
const worker = { fetch(request, env) {
  const url = new URL(request.url);
  return api.fetch(new Request(new URL(url.pathname.slice(4) + url.search, url.origin), request), env);
}};
const { server } = createLocalServer(worker, {stateDir: process.argv[1]});
server.listen(Number(process.argv[2]), '127.0.0.1', () => {
  console.log(JSON.stringify({origin: `http://127.0.0.1:${server.address().port}`}));
});
""".replace("API_URL", json.dumps((self.repo / "enterprise/worker/api.js").as_uri())).replace(
            "SERVER_URL", json.dumps((self.repo / "enterprise/scripts/local-server.mjs").as_uri()))
        self.process = subprocess.Popen(
            [self.node, "--input-type=module", "-e", script, str(self.root / "server"), str(port)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        startup = queue.Queue()
        threading.Thread(target=lambda: startup.put(self.process.stdout.readline()), daemon=True).start()
        try:
            line = startup.get(timeout=15)
        except queue.Empty:
            self.fail("Isolated HTTP fixture did not start within 15 seconds")
        self.assertTrue(line, "Isolated Node fixture failed during startup")
        self.origin = json.loads(line)["origin"]

    def stop_server(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
            self.process.stdout.close()
            self.process = None

    def call(self, path, data=None):
        request = urllib.request.Request(
            self.origin + "/api" + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Origin": self.origin, "Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response)

    def test_provider_failure_checkpoint_recovery_delivery_and_server_restart(self):
        self.call("/session")
        job = self.call("/orgs/org_primary/jobs", {
            "title": "Isolated recovery fixture", "brief": SMOKE_BRIEF,
            "max_tokens": 50000, "max_steps": 8,
        })["job"]
        config = enroll(self.origin, self.root / "connection")
        client = Client(config, allow_local=True)
        claim = client.request("/api/worker/claim", data={})
        self.assertEqual(claim["job"]["id"], job["id"])
        demo = create_adapter()

        def fail_after_artifact(request):
            if "available_tools" in request.payload and request.payload["artifacts"]:
                raise RuntimeError("Synthetic provider unavailable")
            return demo.callback(request)

        work = self.root / "worker" / job["id"]
        interrupted = execute(claim["job"], work, adapter=CallbackAdapter(fail_after_artifact))
        self.assertEqual(interrupted["status"], "interrupted")
        self.assertEqual(interrupted["reason"], "provider_unavailable")
        self.assertTrue(interrupted["artifacts"])
        artifact = Path(interrupted["artifacts"][0])
        before = artifact.read_bytes()
        deliver(client, claim["job"], claim["lease_token"], work, interrupted)
        self.assertEqual(self.call(f"/orgs/org_primary/jobs/{job['id']}")["job"]["status"], "interrupted")
        port = int(self.origin.rsplit(":", 1)[1])
        self.stop_server()
        self.start_server(port)
        self.assertEqual(enroll(self.origin, self.root / "connection"), config)
        self.call(f"/orgs/org_primary/jobs/{job['id']}/resume", {"additional_minutes": 1})
        resumed_claim = client.request("/api/worker/claim", data={})
        recovered = execute(resumed_claim["job"], work, adapter=create_adapter())
        self.assertEqual(recovered["status"], "completed", recovered)
        self.assertEqual(artifact.read_bytes(), before)
        deliver(client, resumed_claim["job"], resumed_claim["lease_token"], work, recovered)
        # Terminal checkpoint replay must not invoke a provider again.
        saved = execute(resumed_claim["job"], work, adapter=CallbackAdapter(
            lambda request: self.fail("Terminal checkpoint must not call provider")))
        self.assertEqual(saved["status"], "completed")
        self.assertEqual(saved["model_tokens"], recovered["model_tokens"])
        self.stop_server()
        self.start_server(port)
        final = self.call(f"/orgs/org_primary/jobs/{job['id']}")
        self.assertEqual(final["job"]["status"], "completed")
        self.assertGreaterEqual(len(final["artifacts"]), 3)
        for record in final["artifacts"]:
            with urllib.request.urlopen(self.origin + "/api/orgs/org_primary/artifacts/" + record["id"], timeout=10) as response:
                self.assertEqual(hashlib.sha256(response.read()).hexdigest(), record["sha256"])
                self.assertIn("attachment", response.headers["Content-Disposition"])


if __name__ == "__main__":
    unittest.main()
