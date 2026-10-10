import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aeon_worker.models import ActionGrant
from aeon_worker.tools import WorkspaceTools
from aeon_worker.runner import _decision_history
from aeon_worker.models import WorkOrder


class LocalBrowserCasesTests(unittest.TestCase):
    def test_layout_inspection_tracks_rewrites_on_reused_page_at_both_viewports(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tools = WorkspaceTools(root / 'workspace', root / 'evidence', ActionGrant())
            head = ('<!doctype html><html lang="en"><head>'
                    '<meta name="viewport" content="width=device-width,initial-scale=1">'
                    '<title>Layout rewrite check</title></head><body>')
            try:
                # Alternate contents at one URI, reuse Chromium/page, and force
                # each desktop/mobile navigation to observe the current bytes.
                for iteration, overflow in enumerate((True, False, True, False)):
                    marker = f'current-artifact-{iteration}'
                    css = 'width:2000px' if overflow else 'max-width:100%;box-sizing:border-box'
                    tools.write_file('index.html', head + f'<main style="{css}">{marker}</main></body></html>')
                    inspected = tools.inspect_site('index.html')
                    geometry = tools._page.evaluate('''() => ({
                        text: document.body.innerText, viewport: innerWidth,
                        scroll: document.documentElement.scrollWidth,
                        main: document.querySelector('main').getBoundingClientRect().width
                    })''')
                    with self.subTest(iteration=iteration, overflow=overflow):
                        self.assertEqual(inspected['issues'],
                                         ['desktop: horizontal overflow', 'mobile: horizontal overflow'] if overflow else [],
                                         {'inspection': inspected, 'geometry': geometry})
                        self.assertIn(marker, geometry['text'])
                        self.assertEqual(geometry['viewport'], 390)
                        self.assertEqual(geometry['scroll'] > geometry['viewport'] + 2, overflow)
                        self.assertEqual(len(inspected['screenshots']), 2)
                        self.assertTrue(all(Path(path).is_file() for path in inspected['screenshots']))
            finally:
                tools.close()

    def test_malformed_fills_rejected_before_browser_actions_with_recovery_example(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tools = WorkspaceTools(root / 'workspace', root / 'evidence', ActionGrant())
            try:
                for invalid in ([None], ['#bill', '100'], [{'selector': '#bill', 'value': None}], None):
                    with self.subTest(fills=invalid), patch.object(tools, '_ensure_browser') as launch:
                        with self.assertRaisesRegex(ValueError, 'fills needs 1..12 selector/value objects') as caught:
                            tools.browser('test_local', url='index.html', cases=[{
                                'fills': invalid, 'selector': '#bill', 'value': '100',
                                'click': '#calculate', 'expected': '115',
                            }])
                        self.assertIn('"selector":"#bill","value":"100"', str(caught.exception))
                        self.assertIn('separate fill actions', str(caught.exception))
                        launch.assert_not_called()
            finally:
                tools.close()

    def test_real_browser_batch_checks_multiple_inputs_and_zero_tip(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tools = WorkspaceTools(root / 'workspace', root / 'evidence', ActionGrant())
            tools.write_file('index.html', '''<html><body><input id="bill"><input id="tip">
<button id="calculate" onclick="document.getElementById('out').textContent=(Number(document.getElementById('bill').value)*(1+Number(document.getElementById('tip').value)/100)).toFixed(2)">Calculate</button><output id="out"></output></body></html>''')
            try:
                cases = [
                    {'fills': [{'selector': '#bill', 'value': '100'}, {'selector': '#tip', 'value': '15'}], 'click': '#calculate', 'expected': '115.00'},
                    {'fills': [{'selector': '#bill', 'value': '40'}, {'selector': '#tip', 'value': '0'}], 'click': '#calculate', 'expected': '40.00'},
                ]
                result = tools.browser('test_local', url='index.html', cases=cases)
                self.assertTrue(result['passed'])
                self.assertEqual([check['fills'] for check in result['checks']], [case['fills'] for case in cases])
                self.assertTrue(all(check['passed'] for check in result['checks']))
                self.assertFalse(tools._write_guard_active)
            finally:
                tools.close()

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
