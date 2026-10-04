import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aeon_worker.benchmark import run_direct
from aeon_worker.models import TaskSpec, TOOL_NAMES
from aeon_worker.providers import ProviderRouter, StructuredContentError
from aeon_worker.runner import TaskRunner, TaskStore


class StructuredProviderTests(unittest.TestCase):
    def test_native_action_schema_limits_tool_names(self):
        requests = []
        def respond(request, **kwargs):
            requests.append(json.loads(request.data))
            return io.BytesIO(json.dumps({'candidates':[{'content':{'parts':[{'text':'{"tool":"finish","args":{},"decision_summary":"Complete"}'}]}}]}).encode())
        with patch.dict('os.environ', {'GEMINI_API_KEY':'test-key'}), patch('aeon_worker.providers.urllib.request.urlopen', side_effect=respond):
            reply = ProviderRouter(forced_provider='gemini', gemini_backup_model=None).complete('Choose a tool.', {'available_tools':{}})
        schema = requests[0]['generationConfig']['responseJsonSchema']
        self.assertEqual(schema['properties']['tool']['enum'], list(TOOL_NAMES))
        self.assertEqual(reply.data['tool'], 'finish')

    def test_structured_failure_is_not_reported_as_provider_outage(self):
        class Failure:
            def complete(self, *args, **kwargs):
                raise StructuredContentError('Invalid JSON after retries.')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            aeon = TaskRunner(TaskStore(root/'tasks'), Failure()).start(TaskSpec(brief='Produce a file.', workspace=str(root/'workspace')))
            direct = run_direct({'id':'case1', 'brief':'Produce a file.', 'task_type':'general'}, root/'direct', Failure())
            for result in [aeon, direct]:
                self.assertEqual(result['reason'], 'invalid_model_response')
                self.assertEqual(result['status'], 'interrupted')


if __name__ == '__main__':
    unittest.main()
