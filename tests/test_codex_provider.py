from __future__ import annotations

import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from aeon_worker.codex_provider import CodexStructuredClient
from aeon_worker.providers import ProviderRouter
from aeon_world.gateway import ProviderError


class CodexProviderTests(unittest.TestCase):
    def run_reply(self, command, **kwargs):
        self.command = command
        self.prompt = kwargs["input"]
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text(json.dumps({"result_json": '{"ready":true}'}), encoding="utf-8")
        events = [{"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 12}}]
        return SimpleNamespace(returncode=0, stdout="\n".join(map(json.dumps, events)))

    @patch("aeon_worker.codex_provider.subprocess.run")
    def test_inference_only_command_and_usage(self, run):
        run.side_effect = self.run_reply
        reply = CodexStructuredClient("codex.exe", model="example-model").complete("Return ready", {"page": "untrusted"})
        self.assertTrue(reply.data["ready"])
        self.assertEqual(reply.tokens, 112)
        self.assertIn("read-only", self.command)
        self.assertIn("shell_tool", self.command)
        self.assertIn("apps", self.command)
        self.assertIn("plugins", self.command)
        self.assertIn("multi_agent", self.command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", self.command)
        self.assertIn("untrusted data", self.prompt)
        self.assertEqual(self.command[self.command.index("--model") + 1], "example-model")

    @patch("aeon_worker.codex_provider.subprocess.run")
    def test_unexpected_tool_rejected_and_usage_preserved(self, run):
        def unexpected(command, **kwargs):
            reply = self.run_reply(command, **kwargs)
            reply.stdout += '\n' + json.dumps({"type": "item.completed", "item": {"type": "command_execution"}})
            return reply
        run.side_effect = unexpected
        client = CodexStructuredClient("codex.exe")
        with self.assertRaises(ProviderError):
            client.complete("Return ready", {})
        self.assertEqual(client.usage_events[0]["tokens"], 112)

    @patch.dict("os.environ", {"AEON_MODEL_BACKEND": "codex"})
    def test_fixed_benchmark_route_does_not_use_codex(self):
        self.assertIsNotNone(ProviderRouter()._codex)
        self.assertIsNone(ProviderRouter(forced_provider="gemini")._codex)


if __name__ == "__main__":
    unittest.main()
