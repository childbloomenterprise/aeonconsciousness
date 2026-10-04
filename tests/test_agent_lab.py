import os
import tempfile
import unittest
from pathlib import Path

from agent_lab.catalog import load_catalog
from agent_lab.runner import (
    AdapterSpec,
    ExecutionResult,
    load_adapter_specs,
    parse_adapter_output,
    sanitize_environment,
    validate_adapter_result,
)


class AgentCatalogTests(unittest.TestCase):
    def test_catalog_has_broad_unique_official_source_inventory(self) -> None:
        catalog = load_catalog()
        identifiers = [entry["id"] for entry in catalog]

        self.assertGreaterEqual(len(catalog), 30)
        self.assertEqual(len(identifiers), len(set(identifiers)))
        for entry in catalog:
            self.assertTrue(entry["source"].startswith("https://github.com/"))
            self.assertTrue(entry["architecture"])
            self.assertIn(entry["status"], {"cataloged", "adapter-tested", "adapter-failed"})

    def test_adapter_manifest_is_pinned_and_scripts_exist(self) -> None:
        specs = load_adapter_specs()
        self.assertGreaterEqual(len(specs), 8)
        for spec in specs:
            self.assertTrue(spec.packages)
            self.assertTrue(all("==" in package for package in spec.packages))
            self.assertTrue(spec.script.is_file())


class AgentLabBoundaryTests(unittest.TestCase):
    def test_adapter_spec_rejects_unpinned_or_unsafe_package(self) -> None:
        with self.assertRaisesRegex(ValueError, "pinned"):
            AdapterSpec("bad", ("langgraph",), Path("bad.py"), 30)
        with self.assertRaisesRegex(ValueError, "package"):
            AdapterSpec("bad", ("pkg==1; whoami",), Path("bad.py"), 30)

    def test_environment_removes_credentials(self) -> None:
        original = {
            "PATH": os.environ.get("PATH", ""),
            "TEMP": tempfile.gettempdir(),
            "ANTHROPIC_API_KEY": "secret",
            "CI_JOB_TOKEN": "secret",
            "DATABASE_PASSWORD": "secret",
            "SAFE_SETTING": "visible",
        }

        sanitized = sanitize_environment(original)

        self.assertIn("PATH", sanitized)
        self.assertEqual("visible", sanitized["SAFE_SETTING"])
        self.assertNotIn("ANTHROPIC_API_KEY", sanitized)
        self.assertNotIn("CI_JOB_TOKEN", sanitized)
        self.assertNotIn("DATABASE_PASSWORD", sanitized)

    def test_output_parser_reads_last_json_object_and_limits_size(self) -> None:
        result = ExecutionResult(
            returncode=0,
            stdout='framework banner\n{"framework":"demo","success":true,"actions":["OpenObject"]}\n',
            stderr="",
            duration_seconds=0.1,
        )
        parsed = parse_adapter_output(result)
        self.assertEqual("demo", parsed["framework"])
        decorated = ExecutionResult(
            0,
            '|  {"framework":"demo","success":true,"actions":[]}\n+---+',
            "",
            0.1,
        )
        self.assertEqual("demo", parse_adapter_output(decorated)["framework"])
        with self.assertRaisesRegex(ValueError, "too large"):
            parse_adapter_output(ExecutionResult(0, "x" * 1_000_001, "", 0.1))

    def test_result_outside_aeon_action_envelope_fails(self) -> None:
        task = {"allowed_actions": ["OpenObject", "Done"]}
        result = {"framework": "demo", "success": True, "actions": ["DeleteObject"]}

        verdict = validate_adapter_result("demo", task, result)

        self.assertFalse(verdict["accepted"])
        self.assertIn("DeleteObject", verdict["unauthorized_actions"])

    def test_valid_framework_result_is_accepted(self) -> None:
        task = {"allowed_actions": ["OpenObject", "Done"]}
        result = {"framework": "demo", "success": True, "actions": ["OpenObject"]}

        verdict = validate_adapter_result("demo", task, result)

        self.assertTrue(verdict["accepted"])
        self.assertEqual([], verdict["unauthorized_actions"])


if __name__ == "__main__":
    unittest.main()
