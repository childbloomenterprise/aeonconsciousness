from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from aeon_enterprise.service import configure, main


class EnterpriseServiceTests(unittest.TestCase):
    def write_connection(self, root: Path, **overrides) -> None:
        (root / "worker-connection.json").write_text(json.dumps({
            "base_url": "https://owner.example",
            "worker_token": "w" * 64,
            "mode": "trusted-local",
            **overrides,
        }), encoding="utf-8")

    def test_configuration_preserves_identity_and_loads_only_model_credentials(self):
        windows_env = {name: value for name, value in os.environ.items() if name.upper() in {"SYSTEMROOT", "WINDIR"}}
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, windows_env, clear=True):
            root = Path(folder)
            self.write_connection(root)
            original = (root / "worker-connection.json").read_bytes()
            (root / "providers.json").write_text(json.dumps({"GEMINI_API_KEY": "model", "AEON_ADMIN_KEY": "forbidden"}))
            (root / "browsers").mkdir()
            configure(root)
            self.assertEqual(os.environ["GEMINI_API_KEY"], "model")
            self.assertNotIn("AEON_ADMIN_KEY", os.environ)
            self.assertEqual(os.environ["PLAYWRIGHT_BROWSERS_PATH"], str(root / "browsers"))
            self.assertEqual((root / "worker-connection.json").read_bytes(), original)

    def test_invalid_connection_rejected_before_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for overrides in ({"base_url": "https://owner.example/unsafe"}, {"mode": "automatic"}):
                self.write_connection(root, **overrides)
                with self.assertRaises(ValueError):
                    configure(root)

    def test_malformed_provider_values_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.write_connection(root)
            for providers in ([], {"GEMINI_API_KEY": 123}, {"NVIDIA_API_KEY": " "}):
                (root / "providers.json").write_text(json.dumps(providers))
                with self.assertRaises(ValueError):
                    configure(root)

    def test_installed_launcher_passes_mode_and_state_without_mutating_process_arguments(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.write_connection(root)
            original = sys.argv[:]
            with patch("aeon_enterprise.service.worker_main", return_value=0) as worker:
                self.assertEqual(main(["--private-root", str(root), "--once"]), 0)
            self.assertEqual(sys.argv, original)
            worker.assert_called_once_with(["--connection", str(root / "worker-connection.json"), "--state-root", str(root / "jobs"), "--trusted-local", "--once"])

    @unittest.skipUnless(os.name == "nt", "Windows startup regression")
    def test_broken_python_stops_startup_before_background_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.write_connection(root)
            fake_python = root / "broken-python.cmd"
            fake_python.write_text("@exit /b 1\n")
            script = Path(__file__).resolve().parents[1] / "deployment" / "start-enterprise-worker.ps1"
            result = subprocess.run(["powershell.exe", "-NoProfile", "-File", str(script), "-Python", str(fake_python), "-PrivateRoot", str(root)], capture_output=True, text=True, timeout=20)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Worker installation check failed", result.stderr)
            self.assertFalse((root / "worker.log").exists())


if __name__ == "__main__":
    unittest.main()
