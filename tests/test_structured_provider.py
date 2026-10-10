import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aeon_worker.benchmark import run_direct
from aeon_worker.models import ActionGrant, TaskSpec, TOOL_NAMES
from aeon_worker.providers import ProviderRouter, StructuredContentError
from aeon_worker.runner import TaskRunner, TaskStore, TOOLS_DESCRIPTION
from aeon_worker.tools import WorkspaceTools


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
        variants = schema['properties']['args']['anyOf']
        args_properties = {name: definition for variant in variants for name, definition in variant['properties'].items()}
        supported_args = {name for tool in TOOLS_DESCRIPTION.values() for name in tool} - {'test_local_example'}
        self.assertEqual(set(args_properties), supported_args)
        self.assertEqual(args_properties['amount']['type'], 'number')
        self.assertEqual(args_properties['operation']['type'], 'string')
        self.assertEqual(args_properties['url']['type'], 'string')
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

    def test_native_action_request_preserves_nested_browser_fills_and_site_sections(self):
        actions = [
            {'tool': 'browser', 'args': {'operation': 'test_local', 'url': 'index.html', 'cases': [
                {'fills': [{'selector': '#bill', 'value': '100'}, {'selector': '#tip', 'value': '15'}],
                 'click': '#calculate', 'expected': '115'}]}, 'decision_summary': 'Check two inputs.'},
            {'tool': 'create_site', 'args': {'name': 'Local project', 'sections': [
                {'heading': 'About', 'body': 'Owner-provided description.'}]}, 'decision_summary': 'Create a site.'},
        ]
        requests = []
        def respond(request, **kwargs):
            requests.append(json.loads(request.data))
            action = actions[len(requests) - 1]
            return io.BytesIO(json.dumps({'candidates': [{'content': {'parts': [{'text': json.dumps(action)}]}}]}).encode())
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}), patch('aeon_worker.providers.urllib.request.urlopen', side_effect=respond):
            router = ProviderRouter(forced_provider='gemini', gemini_backup_model=None)
            for expected in actions:
                self.assertEqual(router.complete('Choose a tool.', {'available_tools': {}}).data, expected)
        for request in requests:
            variants = request['generationConfig']['responseJsonSchema']['properties']['args']['anyOf']
            args_schema = next(variant for variant in variants if variant['properties'].get('operation', {}).get('enum') == ['test_local'])
            self.assertEqual(set(args_schema['required']), {'operation', 'url', 'cases'})
            cases = args_schema['properties']['cases']
            self.assertEqual((cases['type'], cases['minItems'], cases['maxItems']), ('array', 1, 12))
            case = cases['items']
            self.assertEqual(case['type'], 'object')
            self.assertEqual(set(case['required']), {'click', 'expected'})
            fills = case['properties']['fills']
            self.assertEqual((fills['type'], fills['minItems']), ('array', 1))
            # Live Gemini rejects 12 cases x 12 fills; runtime still enforces 12.
            self.assertNotIn('maxItems', fills)
            self.assertIn('twelve', fills['description'])
            self.assertEqual(fills['items']['type'], 'object')
            self.assertEqual(set(fills['items']['required']), {'selector', 'value'})
            self.assertEqual(fills['items']['properties']['value']['type'], 'string')
            sections = next(variant for variant in variants if 'sections' in variant['properties'])['properties']['sections']
            self.assertEqual(sections['type'], 'array')
            self.assertEqual(sections['items']['type'], 'object')
            self.assertEqual(set(sections['items']['required']), {'heading', 'body'})

    def test_browser_fill_limit_is_enforced_before_execution_without_provider_maximum(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tools = WorkspaceTools(root / 'workspace', root / 'evidence', ActionGrant())
            try:
                for count in (0, 13):
                    with self.subTest(count=count), patch.object(tools, '_ensure_browser') as launch:
                        with self.assertRaisesRegex(ValueError, 'fills needs 1..12 selector/value objects'):
                            tools.browser('test_local', url='index.html', cases=[{
                                'click': '#calculate', 'expected': '115',
                                'fills': [{'selector': '#bill', 'value': '100'}] * count,
                            }])
                        launch.assert_not_called()
            finally:
                tools.close()


if __name__ == '__main__':
    unittest.main()
