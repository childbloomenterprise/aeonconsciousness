from __future__ import annotations
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from aeon_enterprise.execute import execute
from aeon_enterprise.worker import (
    Client,
    SameOriginRedirect,
    docker_command,
    execution_environment,
    public_result,
)
from aeon_worker.demo import create_adapter, SMOKE_BRIEF


class EnterpriseWorkerTests(unittest.TestCase):
    def test_requires_https_and_origin_only(self):
        for url in (
            "http://example.com",
            "https://user:pass@example.com",
            "https://example.com/path",
            "https://example.com?x=y",
        ):
            with self.assertRaises(ValueError):
                Client({"base_url": url, "worker_token": "x" * 64})
        Client(
            {"base_url": "http://127.0.0.1:8787", "worker_token": "x" * 64},
            allow_local=True,
        )

    def test_never_redirects_credentials_to_other_origin(self):
        with self.assertRaises(PermissionError):
            SameOriginRedirect("https://owner.test").redirect_request(
                None, None, 302, "", {}, "https://attacker.test"
            )

    def test_no_control_plane_secret_in_execution_environment(self):
        with patch.dict(
            os.environ,
            {
                "AEON_ADMIN_KEY": "admin",
                "AEON_WORKER_TOKEN": "worker",
                "AEON_SITE_SERVICE_KEY": "sites",
                "GEMINI_API_KEY": "model",
            },
        ):
            env = execution_environment()
        self.assertNotIn("AEON_ADMIN_KEY", env)
        self.assertNotIn("AEON_WORKER_TOKEN", env)
        self.assertNotIn("AEON_SITE_SERVICE_KEY", env)
        self.assertEqual(env["GEMINI_API_KEY"], "model")

    def test_docker_enforces_container_resource_boundary(self):
        command = docker_command(
            Path("/tmp/job"), "aeon-enterprise-worker:0.4.0", "aeon-job-abcd-1234"
        )
        self.assertIn("--read-only", command)
        self.assertIn("--cap-drop", command)
        self.assertIn("--memory", command)
        self.assertNotIn("/var/run/docker.sock", " ".join(command))
        self.assertNotIn("--privileged", command)

    def test_public_result_omits_local_runtime_paths(self):
        result = public_result(
            {
                "status": "completed",
                "workspace": "C:/private",
                "run_dir": "C:/private/state",
                "artifacts": ["C:/private/guide.md"],
            },
            Path("."),
        )
        self.assertNotIn("run_dir", result)
        self.assertEqual(result["artifacts"], ["guide.md"])

    def test_actual_worker_executes_and_returns_saved_result_without_reexecution(self):
        job = {
            "id": "job_" + "a" * 32,
            "brief": SMOKE_BRIEF,
            "grant": {},
            "deadline_minutes": 3,
            "max_tokens": 50000,
            "max_steps": 8,
            "max_revisions": 1,
        }
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            first = execute(job, root, adapter=create_adapter())
            second = execute(job, root, adapter=create_adapter())
            self.assertEqual(first["status"], "completed")
            self.assertEqual(first["model_tokens"], second["model_tokens"])
            self.assertTrue((root / "runtime-result.json").is_file())

    def test_invalid_remote_job_id_rejected(self):
        with self.assertRaises(ValueError):
            execute({"id": "../../escape"}, Path("."))


if __name__ == "__main__":
    unittest.main()
