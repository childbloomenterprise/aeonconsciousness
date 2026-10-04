import tempfile
import unittest
from pathlib import Path

from aeon_worker.models import ActionGrant
from aeon_worker.tools import WorkspaceTools
from aeon_worker.runner import _decision_history
from aeon_worker.models import WorkOrder


class LocalBrowserCasesTests(unittest.TestCase):
    def test_compact_context_preserves_file_tail_and_full_audit(self):
        raw = 'a' * 7000 + '<button id="actual-control">Calculate</button>'
        history = [{'tool':'read_file', 'args':{'content':raw}, 'result':{'content':raw}}]
        compact = _decision_history(history)
        self.assertIn('actual-control', compact[0]['result']['content'])
        self.assertEqual(history[0]['result']['content'], raw)
        self.assertLess(len(str(compact)), len(str(history)))

    def test_explicit_offline_brief_does_not_require_web_sources(self):
        order = WorkOrder.from_model({'task_type':'browser_file'}, 'Create checklist.json. No research needed.')
        self.assertEqual(order.task_type, 'general')

    def test_real_browser_batch_reports_actual_pass_and_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tools = WorkspaceTools(root, root / 'evidence', ActionGrant())
            tools.write_file('index.html', '<html><body><input id="n"><button id="b" onclick="document.getElementById(\'out\').textContent=Number(document.getElementById(\'n\').value)*2">Calculate</button><output id="out"></output></body></html>')
            try:
                result = tools.browser('test_local', url='index.html', cases=[
                    {'selector': '#n', 'value': '21', 'click': '#b', 'expected': '42'},
                    {'selector': '#n', 'value': '5', 'click': '#b', 'expected': '999'},
                ])
                self.assertFalse(result['passed'])
                self.assertTrue(result['checks'][0]['passed'])
                self.assertFalse(result['checks'][1]['passed'])
                self.assertIn('10', result['checks'][1]['observed_text'])
                with self.assertRaises(ValueError):
                    tools.browser('test_local', url='https://example.com', effect='spend', cases=[])
                with self.assertRaises(ValueError):
                    tools.browser('test_local', url='index.html', cases=[{'selector':'#n'}])
            finally:
                tools.close()

    def test_local_batch_fills_all_required_form_fields_before_click(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tools = WorkspaceTools(root, root / 'evidence', ActionGrant())
            tools.write_file('index.html', '''<!doctype html><html><body>
<form id="f"><input id="name" required><input id="city" required>
<select id="topic"><option value="puzzle">Puzzles</option></select>
<button id="save">Save</button></form><output id="out"></output>
<script>document.getElementById('f').addEventListener('submit', e => {
e.preventDefault(); document.getElementById('out').textContent =
'Saved ' + document.getElementById('name').value + ' in ' + document.getElementById('city').value + ' for ' + document.getElementById('topic').value;
});</script></body></html>''')
            try:
                result = tools.browser('test_local', url='index.html', cases=[{
                    'fills': ['{"selector":"#name","value":"Mira"}', {'selector': '#city', 'value': 'Pune'}, {'selector': '#topic', 'value': 'Puzzles'}],
                    'click': '#save', 'expected': 'Saved Mira in Pune for puzzle',
                }])
                self.assertTrue(result['passed'])
                self.assertEqual(len(result['checks']), 1)
                with self.assertRaisesRegex(ValueError, 'Available options'):
                    tools.browser('fill', selector='#topic', value='Unknown')
            finally:
                tools.close()


if __name__ == '__main__':
    unittest.main()
