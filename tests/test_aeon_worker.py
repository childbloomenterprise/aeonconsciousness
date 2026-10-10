from __future__ import annotations

import json
import io
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout

from aeon_worker.models import ActionGrant, TaskSpec, deadline_minutes_from_brief
from aeon_worker.providers import ModelReply, ProviderRouter
from aeon_worker.runner import TaskRunner, TaskStore, _neutralize_identity_claims
from aeon_worker.tools import WorkspaceTools, _DuckDuckGoResults
from aeon_worker.verification import cited_urls, verify_artifacts
from aeon_world.gateway import ProviderError
from aeon_worker.benchmark import analyze_benchmark, load_cases, make_review_pack, run_benchmark, run_direct
from aeon_worker.cli import main as cli_main


PLAN = {
    "outcome": "Produce a useful answer",
    "task_type": "research",
    "audience": "owner",
    "deliverables": ["answer.md"],
    "hard_requirements": ["Cite sources"],
    "flexible_tactics": [],
    "assumptions": [],
    "subgoals": ["Inspect source", "Write answer", "Verify"],
    "options": ["Short report", "Detailed report"],
    "chosen_approach": "Short sourced report",
    "success_checks": ["Citations and artifact"],
}


def action(tool: str, **args):
    return {"tool": tool, "args": args, "decision_summary": f"Use {tool} to advance the task."}


class ScriptedProvider:
    def __init__(self, *responses):
        self.responses = list(responses)

    def complete(self, system, payload):
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return ModelReply(response, "test", "scripted", 10)


class ScriptedImageProvider(ScriptedProvider):
    def __init__(self, *responses):
        super().__init__(*responses)
        self.reviewed_images = 0
        self.image_payloads = []

    def complete(self, system, payload):
        reply = super().complete(system, payload)
        return ModelReply(reply.data, "gemini", "scripted", reply.tokens)

    def complete_images(self, system, payload, image_paths):
        self.reviewed_images += len(image_paths)
        self.image_payloads.append(payload)
        self.asserted_paths = [Path(path).is_file() for path in image_paths]
        return ModelReply({"issues": []}, "gemini", "scripted", 10)


class WeightedProvider(ScriptedProvider):
    def complete(self, system, payload):
        reply = super().complete(system, payload)
        return ModelReply(reply.data, reply.provider, reply.model, 60)


class WorkerTests(unittest.TestCase):
    def test_no_research_brief_overrides_misclassified_research_plan_and_old_sources(self):
        for old_sources in (False, True):
            with self.subTest(old_sources=old_sources), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                provider = ScriptedProvider(PLAN,
                    action('write_file', path='answer.md', content='# Facts vs Inferences\nOnly provided email facts; unknown cause.'),
                    {'issues': []})
                runner = TaskRunner(TaskStore(root / 'tasks'), provider)
                original_plan = runner._plan
                def plan(spec, state, ledger):
                    original_plan(spec, state, ledger)
                    if old_sources:
                        state['sources'] = [{'url': 'https://example.com', 'excerpt': 'Unrelated old source'}]
                with patch.object(runner, '_plan', side_effect=plan):
                    result = runner.start(TaskSpec('Ground everything in the provided email. No web browsing. No citations.', str(root / 'workspace')))
                self.assertEqual(result['status'], 'completed', result)
                self.assertEqual(result['unresolved_gaps'], [])
                self.assertTrue((root / 'workspace' / 'answer.md').is_file())

    def test_forbidden_public_read_never_reaches_network_and_local_write_recovers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(PLAN,
                action('read_url', url='https://example.com'),
                action('write_file', path='answer.md', content='Facts from supplied context; no external evidence.'),
                action('finish'), {'issues': []})
            with patch.object(WorkspaceTools, 'read_url') as network:
                result = TaskRunner(TaskStore(root / 'tasks'), provider).start(TaskSpec(
                    'Analyze supplied email. No research needed. No web browsing.', str(root / 'workspace')))
            network.assert_not_called()
            self.assertEqual(result['status'], 'completed', result)
            self.assertEqual(result['sources'], [])

    def test_real_research_still_requires_inspected_citations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(PLAN,
                action('write_file', path='answer.md', content='Unsupported source-free report.'),
                action('finish'), {'issues': []})
            result = TaskRunner(TaskStore(root / 'tasks'), provider).start(TaskSpec(
                'Research public sources and cite inspected evidence.', str(root / 'workspace'), max_revisions=0))
            self.assertNotEqual(result['status'], 'completed')
            self.assertFalse((root / 'workspace' / 'answer.md').exists())

    def test_explicit_local_assertion_brief_cannot_complete_without_execution_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(
                dict(PLAN, task_type='browser_file', deliverables=['source-summary.json'],
                     hard_requirements=['Run a real bounded local assertion check recording only observed checks']),
                action('read_url', url='https://example.com/about'),
                action('write_file', path='source-summary.json', content='{"claims":["one","two","three"]}'),
                {'issues': []},
            )
            with patch.object(WorkspaceTools, 'read_url', return_value={'url': 'https://example.com/about', 'content': 'one two three'}):
                result = TaskRunner(TaskStore(root / 'tasks'), provider).start(TaskSpec(
                    'Produce source-summary.json. Run a real bounded local assertion check.',
                    str(root / 'workspace'), max_revisions=0))
            self.assertEqual(result['status'], 'partial', result)
            self.assertEqual(result['command_checks'], [])
            self.assertTrue(any('local verification command' in gap for gap in result['unresolved_gaps']), result)

    def test_hard_requirement_local_assertions_repaired_with_real_current_script_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            received = []
            class CapturingProvider(ScriptedProvider):
                def complete(self, system, payload):
                    received.append(json.loads(json.dumps(payload)))
                    return super().complete(system, payload)
            provider = CapturingProvider(
                dict(PLAN, task_type='browser_file', deliverables=['source-summary.json'],
                     hard_requirements=['Run a real bounded local assertion check recording only observed checks']),
                action('read_url', url='https://example.com/about'),
                action('write_file', path='source-summary.json', content='{"claims":["one","two","three"]}'),
                action('write_file', path='verify.py', content="import json\nfrom pathlib import Path\nassert len(json.loads(Path('source-summary.json').read_text())['claims']) == 3\n"),
                action('run_check', check='python_script', path='verify.py'),
                action('finish'), {'issues': []},
            )
            with patch.object(WorkspaceTools, 'read_url', return_value={'url': 'https://example.com/about', 'content': 'one two three'}):
                result = TaskRunner(TaskStore(root / 'tasks'), provider).start(TaskSpec(
                    'Produce source-summary.json.', str(root / 'workspace')))
            self.assertEqual(result['status'], 'completed', result)
            self.assertTrue(any('local verification command' in item for item in received[3]['verification_feedback']))
            self.assertEqual(len(result['command_checks']), 1)
            self.assertEqual(result['command_checks'][0]['check'], 'python_script')
            self.assertEqual(result['command_checks'][0]['returncode'], 0)
            self.assertTrue(result['command_checks'][0]['passed'])

    def test_local_assertion_detection_preserves_explanations_and_plain_document_tasks(self):
        positive = (
            'Run a real bounded local assertion check.', 'Execute local assertions.',
            'Validate fields and run a local verification script.',
        )
        negative = (
            'Explain how to run a local assertion check.', 'Do not run local assertions; write a guide.',
            'Summarize an inspected source in a document.',
        )
        for brief in positive:
            with self.subTest(brief=brief):
                self.assertTrue(TaskSpec(brief, '.').require_local_check)
        for brief in negative:
            with self.subTest(brief=brief):
                self.assertFalse(TaskSpec(brief, '.').require_local_check)

    def test_failed_negative_browser_case_guides_targeted_repair_and_current_retest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            observed_error = 'Please enter a valid non-negative bill amount.'
            required_error = 'Please enter a valid non-negative amount'
            html = '''<!doctype html><html lang="en"><head><title>Tip calculator</title>
<meta name="viewport" content="width=device-width,initial-scale=1"></head><body>
<label for="amount">Bill amount</label><input id="amount"><label for="tip">Tip</label><input id="tip">
<button id="calculate">Calculate</button><output id="out"></output>
<script>document.getElementById('calculate').onclick=() => {
const bill=Number(document.getElementById('amount').value),tip=Number(document.getElementById('tip').value);
document.getElementById('out').textContent=bill<0 ? 'Please enter a valid non-negative bill amount.' : (bill*tip/100).toFixed(2);
};</script></body></html>'''
            cases = [
                {'fills': [{'selector': '#amount', 'value': '100'}, {'selector': '#tip', 'value': '15'}],
                 'click': '#calculate', 'expected': '15.00'},
                {'fills': [{'selector': '#amount', 'value': '0'}, {'selector': '#tip', 'value': '20'}],
                 'click': '#calculate', 'expected': '0.00'},
                {'fills': [{'selector': '#amount', 'value': '-1'}, {'selector': '#tip', 'value': '15'}],
                 'click': '#calculate', 'expected': required_error},
            ]
            received = []
            class CapturingProvider(ScriptedProvider):
                def complete(self, system, payload):
                    received.append(json.loads(json.dumps(payload)))
                    return super().complete(system, payload)
            provider = CapturingProvider(
                dict(PLAN, task_type='code', deliverables=['index.html']),
                action('write_file', path='index.html', content=html),
                action('browser', operation='test_local', url='index.html', cases=cases),
                action('replace_text', path='index.html', old=observed_error, new=required_error),
                action('browser', operation='test_local', url='index.html', cases=cases),
                {'issues': []},
            )
            runner = TaskRunner(TaskStore(root / 'tasks'), provider)
            result = runner.start(TaskSpec('Build an offline tip calculator. Test normal, zero and negative bill inputs. '
                                          f'Negative bills must display exactly: {required_error}',
                                          str(root / 'workspace')))
            self.assertEqual(result['status'], 'completed', result)
            # Input and actual output of the failed case must guide the next
            # action; passing sibling cases must not hide its failure.
            repair_decision = received[3]
            feedback = json.dumps(repair_decision['verification_feedback'])
            self.assertIn('#amount', feedback)
            self.assertIn('-1', feedback)
            self.assertIn(observed_error, feedback)
            self.assertIn(required_error, feedback)
            failed_check = repair_decision['recent_results'][-1]['result']['checks'][-1]
            self.assertFalse(failed_check['passed'])
            self.assertEqual(failed_check['fills'], cases[-1]['fills'])
            self.assertIn(observed_error, failed_check['observed_text'])
            retest_decision = received[4]
            edit = next(item for item in retest_decision['recent_results'] if item['tool'] == 'replace_text')
            self.assertIn(observed_error, json.dumps(edit['args'].get('old')))
            self.assertIn(required_error, json.dumps(edit['args'].get('new')))
            current_checks = result['local_interaction_checks'][-3:]
            self.assertEqual(len(current_checks), 3)
            self.assertTrue(all(check['passed'] for check in current_checks), current_checks)
            self.assertIn(required_error, current_checks[-1]['observed_text'])
            self.assertEqual(provider.responses, [])

    def test_targeted_edit_history_keeps_excerpts_without_resending_whole_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old = '"status":"before"'
            new = '"status":"corrected"'
            padding = 'source-content-not-needed-for-next-decision-' * 100
            body = '{' + old + ',"padding":' + json.dumps(padding) + '}'
            received = []
            class CapturingProvider(ScriptedProvider):
                def complete(self, system, payload):
                    received.append(json.loads(json.dumps(payload)))
                    return super().complete(system, payload)
            provider = CapturingProvider(
                dict(PLAN, task_type='general', deliverables=['answer.json']),
                action('write_file', path='answer.json', content=body),
                action('replace_text', path='answer.json', old=old, new=new),
                action('finish'), {'issues': []},
            )
            runner = TaskRunner(TaskStore(root / 'tasks'), provider)
            result = runner.start(TaskSpec('Produce a JSON artifact and make a focused status correction.', str(root / 'workspace')))
            self.assertEqual(result['status'], 'completed', result)
            context = received[3]['recent_results']
            edited = next(item for item in context if item['tool'] == 'replace_text')
            self.assertIn(old, str(edited['args'].get('old')))
            self.assertIn(new, str(edited['args'].get('new')))
            self.assertNotIn(padding, json.dumps(context))
            history = runner.store.load(result['task_id'])['history']
            audit_edit = next(item for item in history if item['tool'] == 'replace_text')
            self.assertIn(old, str(audit_edit['args'].get('old')))
            self.assertIn(new, str(audit_edit['args'].get('new')))
            self.assertEqual(json.loads((root / 'workspace' / 'answer.json').read_text(encoding='utf-8'))['status'], 'corrected')

    def test_benchmark_refuses_changed_source_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'run-metadata.json').write_text(json.dumps({'source_sha256': 'stale'}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'source changed'):
                run_benchmark([{'id': 'case-one', 'brief': 'Produce one artifact.', 'task_type': 'general'}], root, provider_factory=lambda: None)

    def test_plan_filename_annotations_and_optional_source_list_do_not_block_delivery(self):
        from aeon_worker.models import WorkOrder

        brief = 'Research official Python documentation and deliver a cited Markdown answer.'
        order = WorkOrder.from_model({
            'task_type': 'research',
            'deliverables': ['ExitStack_Guide.md (cited explanation)', 'Source_References.txt'],
        }, brief)
        self.assertEqual(order.deliverables, ('ExitStack_Guide.md',))
        requested = WorkOrder.from_model({
            'task_type': 'research',
            'deliverables': ['answer.md', 'Source_References.txt'],
        }, brief + ' Include a separate source list.')
        self.assertEqual(requested.deliverables, ('answer.md', 'Source_References.txt'))

    def test_plan_explanatory_filenames_keep_real_secondary_assets(self):
        from aeon_worker.models import WorkOrder

        order = WorkOrder.from_model({
            'task_type': 'code',
            'deliverables': ['index.html (interface)', 'style.css (responsive layout)', 'script.js (logic)', 'README.md (instructions)'],
        }, 'Build a local reading-time estimator using separate CSS and JavaScript files and README.md.')
        self.assertEqual(order.deliverables, ('index.html', 'style.css', 'script.js', 'README.md'))

    def test_browser_utility_plan_does_not_invent_secondary_asset_gates(self):
        from aeon_worker.models import WorkOrder

        plan = {'task_type': 'code', 'deliverables': ['index.html', 'style.css', 'script.js', 'README.md', 'test_plan.json']}
        order = WorkOrder.from_model(plan, 'Build an offline character counter with a text input.')
        self.assertEqual(order.deliverables, ('index.html',))
        native = WorkOrder.from_model(dict(plan, deliverables=['index.html', 'validate.py']), 'Build a calculator plus a Python validation helper.')
        self.assertEqual(native.deliverables, ('index.html', 'validate.py'))
        requested = WorkOrder.from_model(plan, 'Build a counter and include test_plan.json.')
        self.assertEqual(requested.deliverables, ('index.html', 'test_plan.json'))

    def test_visual_review_receives_actual_current_interactions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            html = '''<!doctype html><html lang="en"><head><title>Price</title>
<meta name="viewport" content="width=device-width,initial-scale=1"></head><body>
<label for="n">Price</label><input id="n"><button id="b" onclick="document.getElementById('out').textContent='Final price: '+Number(document.getElementById('n').value)">Calculate</button><output id="out"></output></body></html>'''
            provider = ScriptedImageProvider(
                dict(PLAN, task_type='code', deliverables=['index.html']),
                action('write_file', path='index.html', content=html),
                action('browser', operation='test_local', url='index.html', cases=[{'selector': '#n', 'value': '42', 'click': '#b', 'expected': 'Final price: 42'}]),
                {'issues': []},
            )
            runner = TaskRunner(TaskStore(root / 'tasks'), provider)
            spec = TaskSpec('Build an offline price calculator.', str(root / 'workspace'))
            result = runner.start(spec)
            self.assertEqual(result['status'], 'completed', result)
            payload = provider.image_payloads[-1]
            self.assertEqual(payload['screenshot_state'], 'initial_unfilled_page')
            self.assertIn('Final price: 42', payload['local_interaction_checks'][0]['observed_text'])
            state = runner.store.load(result['task_id'])
            tools = WorkspaceTools(root / 'workspace', root / 'evidence', ActionGrant())
            try:
                tools.write_file('index.html', html.replace("'Final price: '", "'New price: '"))
                provider.responses.append({'issues': []})
                from unittest.mock import MagicMock
                runner._review(spec, state, tools, MagicMock())
                self.assertEqual(provider.image_payloads[-1]['local_interaction_checks'], [])
            finally:
                tools.close()

    def test_broad_website_brief_keeps_one_portable_required_artifact(self):
        from aeon_worker.models import WorkOrder

        plan = {'task_type': 'website', 'deliverables': ['index.html', 'styles.css', 'script.js', 'verification_report.json']}
        one = WorkOrder.from_model(plan, 'Build a responsive puzzle club website with a local interest draft.')
        self.assertEqual(one.deliverables, ('index.html',))
        separate = WorkOrder.from_model(plan, 'Build a responsive puzzle club website with separate files styles.css and script.js.')
        self.assertEqual(separate.deliverables, ('index.html', 'styles.css', 'script.js'))

    def test_interactive_site_cannot_start_with_static_template(self):
        for kind, brief in [('website', 'Build a local-only interest form.'), ('code', 'Build an offline word-frequency counter.')]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                provider = ScriptedProvider(
                    dict(PLAN, task_type=kind, deliverables=['index.html', 'verification_report.json']),
                    action('create_site', name='Local Interest', role='Club'),
                )
                runner = TaskRunner(TaskStore(root / 'tasks'), provider)
                result = runner.start(TaskSpec(brief, str(root / 'workspace'), max_steps=1))
                self.assertEqual(result['work_order']['deliverables'], ['index.html'])
                self.assertFalse(result['artifacts'])
                history = runner.store.load(result['task_id'])['history']
                self.assertIn('static template', history[-1]['result']['error'])

    def test_passed_local_browser_case_triggers_review_without_extra_finish_call(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            html = '''<!doctype html><html lang="en"><head><title>Calculator</title>
<meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body><h1>Calculator</h1><input id="n"><button id="b" onclick="document.getElementById('out').textContent='Result: '+(Number(document.getElementById('n').value)*2)">Double</button><output id="out"></output></body></html>'''
            provider = ScriptedProvider(
                dict(PLAN, task_type='website', deliverables=['index.html']),
                action('write_file', path='index.html', content=html),
                action('browser', operation='test_local', url='index.html', cases=[{'selector': '#n', 'value': '21', 'click': '#b', 'expected': 'Result: 42'}]),
                {'issues': []},
            )
            result = TaskRunner(TaskStore(root / 'tasks'), provider).start(
                TaskSpec('Build a local doubling calculator.', str(root / 'workspace'))
            )
            self.assertEqual(result['status'], 'completed', result)
            self.assertEqual(result['reason'], 'verified_artifact')
            self.assertEqual(result['steps'], 2)

    def test_browser_utility_code_finishes_after_actual_case_and_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            html = '''<!doctype html><html lang="en"><head><title>Double</title>
<meta name="viewport" content="width=device-width,initial-scale=1"></head><body>
<label for="n">Number</label><input id="n"><button id="b" onclick="document.getElementById('out').textContent='Result: '+(Number(document.getElementById('n').value)*2)">Double</button><output id="out"></output></body></html>'''
            provider = ScriptedProvider(
                dict(PLAN, task_type='code', deliverables=['index.html']),
                action('write_file', path='index.html', content=html),
                action('browser', operation='test_local', url='index.html', cases=[{'selector': '#n', 'value': '21', 'click': '#b', 'expected': 'Result: 42'}]),
                {'issues': []},
            )
            result = TaskRunner(TaskStore(root / 'tasks'), provider).start(TaskSpec('Build an offline doubling calculator.', str(root / 'workspace')))
            self.assertEqual(result['status'], 'completed', result)
            self.assertEqual(result['reason'], 'verified_artifact')
            self.assertEqual(result['steps'], 2)
            self.assertIn('Result: 42', result['local_interaction_checks'][-1]['observed_text'])

    def test_browser_case_does_not_replace_native_code_command_check(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            html = '''<!doctype html><html lang="en"><head><title>Helper</title>
<meta name="viewport" content="width=device-width,initial-scale=1"></head><body>
<h1>Helper</h1><button id="b" onclick="document.getElementById('out').textContent='Ready'">Check</button><output id="out"></output></body></html>'''
            provider = ScriptedProvider(
                dict(PLAN, task_type='code', deliverables=['index.html', 'validate.py']),
                action('write_file', path='index.html', content=html),
                action('write_file', path='validate.py', content='print("validation helper")\n'),
                action('browser', operation='test_local', url='index.html', cases=[{'click': '#b', 'expected': 'Ready'}]),
            )
            result = TaskRunner(TaskStore(root / 'tasks'), provider).start(TaskSpec('Build a browser calculator plus a Python validation helper.', str(root / 'workspace'), max_steps=3))
            self.assertEqual(result['status'], 'partial', result)
            self.assertEqual(result['reason'], 'step_budget')

    def test_website_research_gate_respects_negation_but_retains_positive_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runner = TaskRunner(TaskStore(root / 'tasks'), ScriptedProvider())
            tools = WorkspaceTools(root / 'workspace', root / 'evidence', ActionGrant())
            state = {'task_id': 'task-research-gate', 'work_order': {'task_type': 'website'}, 'artifacts': [], 'sources': [], 'steps': 0}
            from unittest.mock import MagicMock
            try:
                with patch('aeon_worker.runner.verify_artifacts', return_value=([], [])):
                    offline = runner._verify(TaskSpec('Build calculator. No publishing or research needed.', str(root / 'workspace')), state, tools, MagicMock())
                    requested = runner._verify(TaskSpec('Research public sources. No research needed for CSS.', str(root / 'workspace')), state, tools, MagicMock())
                self.assertFalse(any('required public research' in str(item) for item in offline))
                self.assertTrue(any('required public research' in str(item) for item in requested))
            finally:
                tools.close()

    def test_owned_absolute_deliverable_is_normalized_before_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / 'workspace'
            provider = ScriptedProvider(
                dict(PLAN, task_type='general', deliverables=[str(workspace / 'answer.json')]),
                action('write_file', path='answer.json', content='{"answer":1}'),
                action('finish'), {'issues':[]},
            )
            result = TaskRunner(TaskStore(root / 'tasks'), provider).start(TaskSpec(brief='Create JSON.', workspace=str(workspace)))
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(result['work_order']['deliverables'], ['answer.json'])

    def test_router_receives_remaining_budget_and_overrun_never_completes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            class OverrunningRouter(ProviderRouter):
                def __init__(self):
                    self.limits = []

                def complete(self, system, payload, *, max_output_tokens=16_384):
                    self.limits.append(max_output_tokens)
                    return ModelReply(dict(PLAN), "gemini", "scripted", 21_000)

            provider = OverrunningRouter()
            result = TaskRunner(TaskStore(root / "tasks"), provider).start(
                TaskSpec("Produce a short report.", str(root / "workspace"), max_model_tokens=20_000)
            )
            self.assertLess(provider.limits[0], 20_000)
            self.assertNotEqual(result["status"], "completed")
            self.assertEqual(result["reason"], "model_token_budget")
            self.assertTrue(result["audit_valid"])

    def test_provider_fallback_reason_enters_task_audit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            class FallbackRouter(ProviderRouter):
                def __init__(self):
                    self.responses = [
                        dict(PLAN, task_type="general", deliverables=["answer.json"]),
                        action("write_file", path="answer.json", content='{"ok": true}'),
                        action("finish", summary="Done"),
                        {"issues": []},
                    ]

                def complete(self, system, payload, *, max_output_tokens=16_384):
                    return ModelReply(self.responses.pop(0), "gemini", "scripted", 10, fallback_from="nvidia", fallback_reason="nvidia_key_absent")

            result = TaskRunner(TaskStore(root / "tasks"), FallbackRouter()).start(
                TaskSpec("Produce a JSON answer.", str(root / "workspace"))
            )
            self.assertEqual(result["status"], "completed", result)
            self.assertEqual(result["provider_failovers"], [{"from": "nvidia", "to": "gemini", "reason": "nvidia_key_absent"}])
            self.assertTrue(result["audit_valid"])

    def test_brief_relative_deadline_parsing(self):
        self.assertEqual(deadline_minutes_from_brief("Finish within 45 minutes."), 45)
        self.assertEqual(deadline_minutes_from_brief("Complete in 2 hours."), 120)
        self.assertIsNone(deadline_minutes_from_brief("Finish when convenient."))

    def test_workspace_path_and_grant_boundaries(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            tools = WorkspaceTools(base / "workspace", base / "evidence", ActionGrant())
            with self.assertRaises(PermissionError):
                tools.write_file("../escape.md", "no")
            with self.assertRaises(PermissionError):
                tools.write_file("bad.exe", "no")
            with self.assertRaises(ValueError):
                ActionGrant.from_dict({"external_actions": ["unknown"]})
            self.assertFalse((base / "escape.md").exists())

    def test_replace_text_makes_unique_bounded_file_edit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = WorkspaceTools(root / "workspace", root / "evidence", ActionGrant())
            try:
                tools.write_file("note.md", "one two three")
                self.assertEqual(tools.replace_text("note.md", "two", "fixed")["replacements"], 1)
                self.assertEqual(tools.read_file("note.md")["content"], "one fixed three")
                with self.assertRaises(ValueError):
                    tools.replace_text("note.md", "e", "x")
                with self.assertRaises(PermissionError):
                    tools.replace_text("../outside.md", "one", "two")
            finally:
                tools.close()

    def test_read_url_finds_api_signature_split_across_html_nodes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = WorkspaceTools(root / "workspace", root / "evidence", ActionGrant())
            try:
                body = '<html><body><h2>class csv.<span>DictReader</span> (<i>f</i>)</h2><p>Maps rows to dictionaries.</p></body></html>'
                with patch("aeon_worker.tools._fetch", return_value=("https://example.com/docs", body)):
                    result = tools.read_url("https://example.com/docs", find="class csv.DictReader(")
                self.assertIn("Maps rows to dictionaries", result["content"])
            finally:
                tools.close()

    def test_research_task_writes_sourced_artifact_and_audit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(
                PLAN,
                action("read_url", url="https://example.com/fact"),
                action("write_file", path="answer.md", content="# Finding\n\nVerified example. [Source](https://example.com/fact)\n"),
                action("finish", summary="Done"),
                {"issues": []},
            )
            runner = TaskRunner(TaskStore(root / "tasks"), provider)
            spec = TaskSpec("Research the example and deliver a cited answer.", str(root / "workspace"))
            with patch.object(WorkspaceTools, "read_url", return_value={"url": "https://example.com/fact", "content": "Verified example"}):
                result = runner.start(spec)
            self.assertEqual(result["status"], "completed", result)
            self.assertTrue(result["audit_valid"])
            self.assertEqual(len(result["sources"]), 1)
            self.assertTrue(Path(result["artifacts"][0]).is_file())
            self.assertTrue(result["artifact_records"][0]["verified"])
            self.assertEqual(result["work_order"]["subgoals"][0]["id"], "S1")
            self.assertTrue(result["work_order"]["subgoals"][0]["success_check"])
            self.assertTrue(result["memory_candidate_id"])

    def test_cli_status_result_and_terminal_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(
                dict(PLAN, task_type="general", deliverables=["answer.json"]),
                action("write_file", path="answer.json", content='{"ok": true}'),
                action("finish", summary="Done"),
                {"issues": []},
            )
            task_root = root / "tasks"
            result = TaskRunner(TaskStore(task_root), provider).start(TaskSpec("Produce JSON.", str(root / "workspace")))
            for operation in ("status", "result", "resume"):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = cli_main(["--task-root", str(task_root), "task", operation, result["task_id"]])
                self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue())["status"], "completed")

    def test_doctor_probe_reports_provider_unavailable_without_secret(self):
        output = io.StringIO()
        with patch("aeon_worker.cli.ProviderRouter") as router, redirect_stdout(output):
            router.return_value.complete.side_effect = ProviderError("Gemini HTTP 429.")
            code = cli_main(["doctor", "--probe"])
        diagnostic = json.loads(output.getvalue())
        self.assertEqual(code, 1)
        self.assertFalse(diagnostic["probe"]["available"])
        self.assertIn("HTTP 429", diagnostic["probe"]["error"])

    def test_invalid_artifact_is_revised_before_completion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(
                dict(PLAN, task_type="general", deliverables=["data.json"]),
                action("write_file", path="data.json", content="{invalid"),
                action("finish", summary="First attempt"),
                action("write_file", path="data.json", content='{"valid": true}'),
                action("finish", summary="Fixed"),
                {"issues": []},
            )
            result = TaskRunner(TaskStore(root / "tasks"), provider).start(TaskSpec("Make valid JSON.", str(root / "workspace")))
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["revisions"], 1)
            self.assertEqual(json.loads(Path(result["artifacts"][0]).read_text()), {"valid": True})

    def test_finish_cannot_complete_when_independent_review_is_unavailable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(
                dict(PLAN, task_type="general", deliverables=["result.json"]),
                action("write_file", path="result.json", content='{"ok": true}'),
                action("finish", summary="Done"),
                ProviderError("Review unavailable"),
            )
            result = TaskRunner(TaskStore(root / "tasks"), provider).start(
                TaskSpec("Produce a checked JSON result.", str(root / "workspace"), max_revisions=0)
            )
            self.assertEqual(result["status"], "partial")
            self.assertTrue(any("Independent review unavailable" in issue for issue in result["unresolved_gaps"]))
            self.assertEqual(json.loads(Path(result["artifacts"][0]).read_text()), {"ok": True})

    def test_worker_can_repair_artifact_with_targeted_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(
                dict(PLAN, task_type="general", deliverables=["answer.json"]),
                action("write_file", path="answer.json", content='{"ok": fals}'),
                action("finish", summary="Check"),
                action("replace_text", path="answer.json", old="fals", new="true"),
                action("finish", summary="Repaired"),
                {"issues": []},
            )
            result = TaskRunner(TaskStore(root / "tasks"), provider).start(TaskSpec("Produce valid JSON.", str(root / "workspace")))
            self.assertEqual(result["status"], "completed", result)
            self.assertEqual(json.loads(Path(result["artifacts"][0]).read_text(encoding="utf-8")), {"ok": True})

    def test_promised_deliverable_missing_marks_result_partial(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(
                dict(PLAN, task_type="general", deliverables=["first.json", "second.json"]),
                action("write_file", path="first.json", content='{"ok": true}'),
                action("finish", summary="Done"),
            )
            result = TaskRunner(TaskStore(root / "tasks"), provider).start(
                TaskSpec("Produce two JSON files.", str(root / "workspace"), max_revisions=0)
            )
            self.assertEqual(result["status"], "partial")
            self.assertIn("Promised deliverable was not produced.", result["unresolved_gaps"])

    def test_interrupted_task_resumes_from_checkpoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(
                dict(PLAN, task_type="general", deliverables=["result.json"]),
                action("write_file", path="result.json", content='{"ok": true}'),
                KeyboardInterrupt(),
                action("finish", summary="Resumed"),
                {"issues": []},
            )
            store = TaskStore(root / "tasks")
            runner = TaskRunner(store, provider)
            spec = TaskSpec("Create a valid JSON file.", str(root / "workspace"))
            with self.assertRaises(KeyboardInterrupt):
                runner.start(spec)
            self.assertEqual(store.load(spec.task_id)["status"], "interrupted")
            result = runner.resume(spec.task_id)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["steps"], 2)

    def test_provider_interruption_keeps_task_resumable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(
                dict(PLAN, task_type="general", deliverables=["result.json"]),
                action("write_file", path="result.json", content='{"ok": true}'),
                ProviderError("temporarily unavailable"),
                action("finish", summary="Recovered"),
                {"issues": []},
            )
            runner = TaskRunner(TaskStore(root / "tasks"), provider)
            spec = TaskSpec("Produce a JSON file.", str(root / "workspace"))
            interrupted = runner.start(spec)
            self.assertEqual(interrupted["status"], "interrupted")
            self.assertTrue(Path(interrupted["artifacts"][0]).exists())
            completed = runner.resume(spec.task_id, additional_revisions=2)
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(runner.store.load(spec.task_id)["spec"]["max_revisions"], spec.max_revisions + 2)

    def test_budget_partial_can_resume_with_explicit_extension(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = WeightedProvider(
                dict(PLAN, task_type="general", deliverables=["result.json"]),
                action("write_file", path="result.json", content='{"ok": true}'),
                action("finish", summary="Done"),
                {"issues": []},
            )
            runner = TaskRunner(TaskStore(root / "tasks"), provider)
            spec = TaskSpec("Produce a JSON file.", str(root / "workspace"), max_model_tokens=100)
            partial = runner.start(spec)
            self.assertEqual(partial["status"], "partial")
            self.assertEqual(partial["reason"], "model_token_budget")
            completed = runner.resume(spec.task_id, additional_model_tokens=200)
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(completed["model_tokens"], 240)
            self.assertTrue(completed["audit_valid"])

    def test_research_verifier_rejects_uninspected_citation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = WorkspaceTools(root / "workspace", root / "evidence", ActionGrant())
            tools.write_file("answer.md", "See https://uninspected.example/page")
            findings, _ = verify_artifacts(
                tools, ["answer.md"], "research",
                [{"url": "https://inspected.example/page"}],
            )
            self.assertTrue(any("not inspected" in item.issue for item in findings))

    def test_citation_extraction_ignores_illustrative_urls_in_code(self):
        content = "[Python docs](https://docs.python.org/3/library/csv.html)\n```python\nurl='https://example.org/api'\n```"
        self.assertEqual(cited_urls(content), {"https://docs.python.org/3/library/csv.html"})

    def test_browser_navigation_counts_as_inspected_source_for_csv(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            page = "https://example.com/docs"
            provider = ScriptedProvider(
                dict(PLAN, task_type="browser_file", deliverables=["features.csv", "note.md"]),
                action("browser", operation="navigate", url=page),
                action("write_file", path="features.csv", content=f"feature,API,evidence_url\nContexts,new_context(),{page}\n"),
                action("write_file", path="note.md", content=f"Verified [docs]({page}).\n"),
                action("finish", summary="Done"),
                {"issues": []},
            )
            runner = TaskRunner(TaskStore(root / "tasks"), provider)
            with patch.object(WorkspaceTools, "browser", return_value={"url": page, "title": "Docs", "text": "new_context() creates a context."}):
                result = runner.start(TaskSpec("Read docs and produce a CSV plus note.", str(root / "workspace")))
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["sources"][0]["url"], page)
            self.assertTrue(result["audit_valid"])

    def test_browser_file_csv_rejects_uninspected_evidence_url(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = WorkspaceTools(root / "workspace", root / "evidence", ActionGrant())
            tools.write_file("features.csv", "feature,API,evidence_url\nScreenshot,page.screenshot(),https://uninspected.example/docs\n")
            findings, _ = verify_artifacts(tools, ["features.csv"], "browser_file", [{"url": "https://inspected.example/docs"}])
            self.assertTrue(any("not inspected" in item.issue for item in findings))

    def test_worker_requires_inspected_source_before_sourced_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            page = "https://example.com/docs"
            provider = ScriptedProvider(
                PLAN,
                action("write_file", path="answer.md", content=f"Claim [{page}]({page})"),
                action("read_url", url=page),
                action("write_file", path="answer.md", content=f"Claim [{page}]({page})"),
                {"issues": []},
            )
            runner = TaskRunner(TaskStore(root / "tasks"), provider)
            with patch.object(WorkspaceTools, "read_url", return_value={"url": page, "content": "Claim"}):
                result = runner.start(TaskSpec("Research and write a cited claim.", str(root / "workspace")))
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["steps"], 3)
            state = runner.store.load(result["task_id"])
            self.assertIn("No inspected source yet", state["history"][0]["result"]["error"])

    def test_worker_redirects_repeated_search_to_source_page(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            page = "https://example.com/docs"
            provider = ScriptedProvider(
                PLAN,
                action("search_web", query="first"),
                action("search_web", query="again"),
                action("read_url", url=page),
                action("write_file", path="answer.md", content=f"Verified [docs]({page})."),
                action("finish", summary="Done"),
                {"issues": []},
            )
            runner = TaskRunner(TaskStore(root / "tasks"), provider)
            with patch.object(WorkspaceTools, "search_web", return_value={"query": "first", "results": [{"url": page, "title": "Docs", "snippet": "Fact"}]}), patch.object(WorkspaceTools, "read_url", return_value={"url": page, "content": "Fact"}):
                result = runner.start(TaskSpec("Research docs and cite them.", str(root / "workspace")))
            self.assertEqual(result["status"], "completed")
            history = runner.store.load(result["task_id"])["history"]
            self.assertIn("Search already returned leads", history[1]["result"]["error"])
            self.assertEqual(history[1]["result"]["suggested_urls"], [page])

    def test_research_pacing_redirects_repeated_reads_to_draft(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            page = "https://example.com/docs"
            provider = WeightedProvider(
                PLAN,
                *[action("read_url", url=page) for _ in range(5)],
                action("write_file", path="answer.md", content=f"# Answer\n\nA fact. [Source]({page})"),
                {"issues": []},
            )
            runner = TaskRunner(TaskStore(root / "tasks"), provider)
            with patch.object(WorkspaceTools, "read_url", return_value={"url": page, "content": "A fact."}):
                result = runner.start(TaskSpec("Research and deliver a cited note.", str(root / "workspace"), max_model_tokens=500))
            self.assertEqual(result["status"], "completed", result)
            state = runner.store.load(result["task_id"])
            self.assertTrue(any("Evidence-gathering budget reached" in str(item.get("result", {}).get("error", "")) for item in state["history"]))

    def test_worker_rejects_uninspected_citation_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = "https://example.com/first"
            second = "https://example.com/second"
            provider = ScriptedProvider(
                PLAN,
                action("read_url", url=first),
                action("write_file", path="answer.md", content=f"[Wrong]({second})"),
                action("read_url", url=second),
                action("write_file", path="answer.md", content=f"[Right]({second}#detail)"),
                action("finish", summary="Done"),
                {"issues": []},
            )
            runner = TaskRunner(TaskStore(root / "tasks"), provider)
            with patch.object(WorkspaceTools, "read_url", side_effect=[{"url": first, "content": "First"}, {"url": second, "content": "Second"}]):
                result = runner.start(TaskSpec("Research a topic and cite inspected pages.", str(root / "workspace")))
            self.assertEqual(result["status"], "completed")
            self.assertIn("uninspected URLs", runner.store.load(result["task_id"])["history"][1]["result"]["error"])

    def test_read_url_can_focus_large_source_page(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = WorkspaceTools(root / "workspace", root / "evidence", ActionGrant())
            page = "<html><body>" + ("intro " * 10000) + "page.screenshot() captures a page" + " tail" * 10000 + "</body></html>"
            with patch("aeon_worker.tools._fetch", return_value=("https://example.com/docs", page)) as fetch:
                result = tools.read_url("https://example.com/docs", "page.screenshot()")
            self.assertIn("page.screenshot()", result["content"])
            self.assertIn("page.screenshot() captures a page", result["content"][:1200])
            self.assertLess(len(result["content"]), 13000)
            self.assertEqual(fetch.call_args.kwargs["max_bytes"], 2_000_000)

    def test_cited_fragment_retains_actual_section_in_source_excerpt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = WorkspaceTools(root / "workspace", root / "evidence", ActionGrant())
            url = "https://example.com/docs#api-target"
            page = '<html><body>' + ('Introduction ' * 5000) + '<h2 id="api-target">Target API</h2><p>Actual behavior: reverse cleanup order.</p></body></html>'
            with patch("aeon_worker.tools._fetch", return_value=(url, page)):
                result = tools.read_url(url)
            self.assertEqual(result["focus"], "#api-target")
            self.assertTrue(result["content"].startswith("Target API"))
            self.assertIn("Actual behavior: reverse cleanup order", result["content"][:1200])

    def test_public_search_parser_extracts_real_destination(self):
        parser = _DuckDuckGoResults()
        with patch("aeon_worker.tools.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
            parser.feed("<a class='result-link' href='https://duckduckgo.com/l/?uddg=https%3A%2F%2Fplaywright.dev%2Fpython%2Fdocs'>Docs</a><td class='result-snippet'>Official <b>browser</b> guide</td>")
        self.assertEqual(parser.results[0]["url"], "https://playwright.dev/python/docs")
        self.assertIn("browser", parser.results[0]["snippet"])

    def test_provider_falls_back_when_nvidia_key_absent(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test"}, clear=True):
            router = ProviderRouter()
            with patch.object(router, "_gemini", return_value=ModelReply({"ok": True}, "gemini", "test", 1)) as gemini:
                result = router.complete("system", {"task": "x"})
            self.assertEqual(result.provider, "gemini")
            self.assertEqual(result.fallback_from, "nvidia")
            self.assertEqual(result.fallback_reason, "nvidia_key_absent")
            gemini.assert_called_once()
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test"}, clear=True):
            with self.assertRaises(ProviderError):
                ProviderRouter(forced_provider="nvidia").complete("system", {"task": "x"})

    def test_invalid_gemini_reply_retains_reported_retry_usage(self):
        def envelope(text):
            return io.StringIO(json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}}], "usageMetadata": {"totalTokenCount": 12, "promptTokenCount": 8, "candidatesTokenCount": 4}}))

        router = ProviderRouter(forced_provider="gemini", gemini_backup_model=None)
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), patch("aeon_worker.providers.urllib.request.urlopen", side_effect=[envelope("broken JSON"), envelope('{"ready": true}')]), patch("aeon_worker.providers.time.sleep"):
            reply = router.complete("Return JSON.", {"ready": True})
        self.assertTrue(reply.data["ready"])
        self.assertEqual(sum(item["tokens"] for item in router.usage_events), 24)

    def test_both_arms_count_usage_on_provider_failure(self):
        class MeteredFailure(ProviderRouter):
            def complete(self, system, payload, **kwargs):
                self.usage_events = [{"provider": "gemini", "model": "test", "tokens": 12, "input_tokens": 8, "output_tokens": 4}]
                raise ProviderError("Invalid output")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            aeon = TaskRunner(TaskStore(root / "tasks"), MeteredFailure()).start(TaskSpec("Write a note.", str(root / "workspace")))
            direct = run_direct({"id": "usage", "brief": "Write a note.", "task_type": "general"}, root / "direct", MeteredFailure())
            for result in (aeon, direct):
                self.assertEqual(result["status"], "interrupted")
                self.assertEqual(result["model_tokens"], 12)
                self.assertEqual(result["input_tokens"], 8)
                self.assertEqual(result["output_tokens"], 4)

    def test_gemini_rate_limit_honors_retry_after(self):
        error = urllib.error.HTTPError("https://example.com", 429, "rate limited", {"Retry-After": "7"}, None)
        router = ProviderRouter(forced_provider="gemini")
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), patch("aeon_worker.providers.urllib.request.urlopen", side_effect=error), patch("aeon_worker.providers.time.sleep") as sleep:
            with self.assertRaises(ProviderError):
                router.complete("Return JSON.", {"x": 1})
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(sleep.call_args_list[0].args[0], 7)

    def test_gemini_uses_backup_model_after_primary_rate_limit(self):
        router = ProviderRouter(forced_provider="gemini")
        called_models = []

        def complete_model(system, payload, *, model, **kwargs):
            called_models.append(model)
            if model == "gemini-3.5-flash-lite":
                raise ProviderError("Gemini HTTP 429.")
            return ModelReply({"ready": True}, "gemini", model, 12)

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), patch.object(router, "_gemini", side_effect=complete_model):
            first = router.complete("Return JSON.", {"ready": True})
            second = router.complete("Return JSON.", {"ready": True})
        self.assertEqual(first.model, "gemini-3.1-flash-lite")
        self.assertEqual(first.route_events[0]["from"], "gemini:gemini-3.5-flash-lite")
        self.assertEqual(called_models, ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.1-flash-lite"])
        self.assertEqual(second.route_events, ())

    def test_static_site_gets_desktop_and_mobile_browser_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = WorkspaceTools(root / "workspace", root / "evidence", ActionGrant())
            try:
                tools.write_file(
                    "index.html",
                    '<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>AEON site</title></head><body><main><h1>Hello</h1></main></body></html>',
                )
                result = tools.inspect_site("index.html")
                self.assertEqual(result["issues"], [])
                self.assertEqual(len(result["screenshots"]), 2)
                self.assertTrue(all(Path(path).is_file() for path in result["screenshots"]))
            finally:
                tools.close()

    def test_create_site_is_runnable_and_avoids_unverified_biography(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = WorkspaceTools(root / "workspace", root / "evidence", ActionGrant())
            try:
                result = tools.create_site({
                    "name": "Mira Vale", "role": "Stage performer",
                    "tagline": "Stories in motion", "intro": "Explore a new stage presence.",
                    "audience": "For event planners", "palette": "rose",
                    "contact_email": "hello@example.com",
                })
                self.assertEqual(result["path"], "index.html")
                body = (root / "workspace" / "index.html").read_text(encoding="utf-8")
                self.assertIn("mailto:hello@example.com", body)
                self.assertNotIn("critically acclaimed", body)
                inspected = tools.inspect_site("index.html")
                self.assertEqual(inspected["issues"], [])
            finally:
                tools.close()

    def test_verified_site_completes_without_extra_model_steps(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(
                dict(PLAN, task_type="website", deliverables=["index.html"]),
                action("create_site", name="Mira Vale", role="Stage performer", tagline="Stories in motion", intro="Explore a new stage presence.", audience="Event planners", palette="rose"),
                {"issues": []},
            )
            result = TaskRunner(TaskStore(root / "tasks"), provider).start(
                TaskSpec("Build a stage performer website for Mira Vale.", str(root / "workspace"))
            )
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["reason"], "verified_artifact")
            self.assertEqual(result["steps"], 1)
            self.assertEqual(len(result["inspections"][0]["screenshots"]), 2)
            self.assertEqual(result["work_order"]["deliverables"], ["index.html"])
            self.assertEqual(provider.responses, [])

    def test_written_site_completes_after_browser_inspection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            html = '<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Local site</title></head><body><main><h1>Local site</h1></main></body></html>'
            provider = ScriptedProvider(
                dict(PLAN, task_type="website", deliverables=["index.html"]),
                action("write_file", path="index.html", content=html),
                action("inspect_site", path="index.html"),
                {"issues": []},
            )
            result = TaskRunner(TaskStore(root / "tasks"), provider).start(
                TaskSpec("Build and check a local site.", str(root / "workspace"))
            )
            self.assertEqual(result["status"], "completed", result)
            self.assertEqual(result["steps"], 2)
            self.assertEqual(result["reason"], "verified_artifact")
            self.assertEqual(len(result["inspections"][0]["screenshots"]), 2)
            self.assertEqual(provider.responses, [])

    def test_broken_layout_is_repaired_before_completion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            head = '<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Responsive</title></head><body>'
            bad = head + '<main style="width:2000px">Too wide</main></body></html>'
            good = head + '<main style="max-width:100%;box-sizing:border-box">Fits viewport</main></body></html>'
            provider = ScriptedProvider(
                dict(PLAN, task_type="website", deliverables=["index.html"]),
                action("write_file", path="index.html", content=bad),
                action("inspect_site", path="index.html"),
                action("write_file", path="index.html", content=good),
                {"issues": []},
            )
            runner = TaskRunner(TaskStore(root / "tasks"), provider)
            result = runner.start(TaskSpec("Build a responsive page.", str(root / "workspace")))
            self.assertEqual(result["status"], "completed", result)
            history = runner.store.load(result["task_id"])["history"]
            self.assertGreaterEqual(result["revisions"], 1, {"result": result, "history": history})
            inspected = [item for item in history if item.get("tool") == "inspect_site"]
            self.assertEqual(len(inspected), 1, {"result": result, "history": history})
            self.assertEqual(inspected[0]["result"].get("issues"),
                             ["desktop: horizontal overflow", "mobile: horizontal overflow"],
                             {"result": result, "history": history})
            self.assertTrue(result["inspections"], result)
            self.assertTrue(all(not item["issues"] for item in result["inspections"]), result)
            self.assertEqual(result["findings"], [])

    def test_failed_local_check_can_be_repaired(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(
                dict(PLAN, task_type="code", deliverables=["app.py"]),
                action("write_file", path="app.py", content="def broken(:\n    pass\n"),
                action("run_check", check="python_compile", path="app.py"),
                action("write_file", path="app.py", content="def working():\n    return 1\n"),
                action("run_check", check="python_compile", path="app.py"),
                {"issues": []},
            )
            runner = TaskRunner(TaskStore(root / "tasks"), provider)
            result = runner.start(TaskSpec("Write and check a Python function.", str(root / "workspace")))
            self.assertEqual(result["status"], "completed", result)
            state = runner.store.load(result["task_id"])
            checks = [item["result"]["returncode"] for item in state["history"] if item.get("tool") == "run_check"]
            self.assertEqual(checks, [1, 0])

    def test_gemini_route_reviews_site_screenshots(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ScriptedImageProvider(
                dict(PLAN, task_type="website", deliverables=["index.html"]),
                action("create_site", name="Mira Vale", role="Stage performer", intro="Explore the work.", palette="rose"),
                {"issues": []},
            )
            result = TaskRunner(TaskStore(root / "tasks"), provider).start(
                TaskSpec("Build a simple site for Mira Vale, stage performer.", str(root / "workspace"))
            )
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["visual_review"], "inspected")
            self.assertEqual(provider.reviewed_images, 2)
            self.assertEqual(provider.asserted_paths, [True, True])

    def test_site_revises_unsupported_biography_before_completion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(
                dict(PLAN, task_type="website", deliverables=["index.html"]),
                action("create_site", name="Mira Vale", role="Stage performer", intro="Specializing in touring performances.", palette="rose"),
                {"issues": []},
                action("create_site", name="Mira Vale", role="Stage performer", intro="Explore Mira's stage work and start a conversation.", palette="rose"),
                {"issues": []},
            )
            result = TaskRunner(TaskStore(root / "tasks"), provider).start(
                TaskSpec("Build a site for Mira Vale, a stage performer. Do not invent credentials.", str(root / "workspace"))
            )
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["revisions"], 1)
            self.assertNotIn("touring", Path(result["artifacts"][0]).read_text(encoding="utf-8"))

    def test_researched_website_waits_for_inspected_identity_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = "https://example.com/mira"
            provider = ScriptedProvider(
                dict(PLAN, task_type="website", deliverables=["index.html"]),
                action("create_site", name="Mira Vale", role="Stage performer", intro="Explore the work."),
                action("read_url", url=source),
                action("create_site", name="Mira Vale", role="Stage performer", intro="Explore the work."),
                {"issues": []},
            )
            runner = TaskRunner(TaskStore(root / "tasks"), provider)
            with patch.object(WorkspaceTools, "read_url", return_value={"url": source, "content": "Mira Vale — stage performer"}):
                result = runner.start(TaskSpec("Research public sources to verify Mira Vale's identity, then build a website.", str(root / "workspace")))
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["revisions"], 1)
            self.assertEqual(result["sources"][0]["url"], source)

    def test_identity_sensitive_site_requires_note_and_flags_unsupported_biography(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = "https://example.com/mira"
            html = '<!doctype html><html lang="en"><head><title>Mira</title><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><h1>Mira Vale</h1><p>Mira is a professional singer based in Kerala.</p></body></html>'
            provider = ScriptedProvider(
                dict(PLAN, task_type="website", deliverables=["index.html"]),
                action("read_url", url=source),
                action("write_file", path="index.html", content=html),
                action("finish", summary="Done"),
            )
            brief = "Research public sources first and verify identity for Mira Vale. Treat biographical details as unverified. Deliver a website and a source/uncertainty note."
            with patch.object(WorkspaceTools, "read_url", return_value={"url": source, "content": "Mira Vale profile page."}):
                result = TaskRunner(TaskStore(root / "tasks"), provider).start(
                    TaskSpec(brief, str(root / "workspace"), max_revisions=0)
                )
            self.assertEqual(result["status"], "partial")
            issues = [item["issue"] for item in result["findings"]]
            self.assertTrue(any("source/uncertainty note" in issue for issue in issues))
            self.assertTrue(any("singer" in issue for issue in issues))

    def test_site_creation_preserves_promised_secondary_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(
                dict(PLAN, task_type="website", deliverables=["index.html", "details.json"]),
                action("create_site", name="Fictional Project", role="Local demo"),
                {"issues": []},
            )
            result = TaskRunner(TaskStore(root / "tasks"), provider).start(
                TaskSpec("Build a site and a details JSON file.", str(root / "workspace"), max_revisions=0)
            )
            self.assertEqual(result["status"], "partial")
            self.assertIn("details.json", result["work_order"]["deliverables"])
            self.assertTrue(any(item["artifact"] == "details.json" for item in result["findings"]))

    def test_identity_repair_preserves_source_supported_location(self):
        original = "Mira is a stage performer based in Kyoto."
        supported = "mira is a stage performer based in kyoto."
        self.assertEqual(_neutralize_identity_claims(original, supported), original)
        repaired = _neutralize_identity_claims(original, "mira name only")
        self.assertIn("owner-supplied, unverified", repaired)
        self.assertNotIn("based in Kyoto", repaired)

    def test_exhausted_identity_site_gets_bounded_claim_repair_on_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = "https://example.com/mira"
            provider = ScriptedProvider(
                dict(PLAN, task_type="website", deliverables=["index.html"]),
                action("read_url", url=source),
                action("create_site", name="Mira Vale", role="Stage performer", intro="Welcome to the official page.", sections=[{"heading": "About", "body": "Mira is a stage performer based in Kutumbura."}]),
                {"issues": []},
            )
            runner = TaskRunner(TaskStore(root / "tasks"), provider)
            brief = "Research public sources first to verify identity for Mira Vale; build a local demo website."
            with patch.object(WorkspaceTools, "read_url", return_value={"url": source, "content": "Mira Vale channel name only."}):
                partial = runner.start(TaskSpec(brief, str(root / "workspace"), max_revisions=0))
            self.assertEqual(partial["status"], "partial")
            completed = runner.resume(partial["task_id"], additional_steps=1)
            self.assertEqual(completed["status"], "completed", completed)
            html = Path(completed["artifacts"][0]).read_text(encoding="utf-8")
            self.assertIn("owner-supplied, unverified", html)
            self.assertNotIn("official page", html.lower())
            self.assertNotIn("based in Kutumbura", html)
            self.assertEqual(completed["steps"], partial["steps"])

    def test_missing_source_note_takes_priority_over_repeated_site_edits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = "https://example.com/subject"
            html = '<!doctype html><html lang="en"><head><title>Site</title><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><h1>Site</h1></body></html>'
            provider = ScriptedProvider(
                dict(PLAN, task_type="website", deliverables=["index.html"]),
                action("read_url", url=source),
                action("write_file", path="index.html", content=html),
                action("write_file", path="index.html", content=html),
                action("write_file", path="index.html", content=html),
                action("write_file", path="sources.md", content=f"# Uncertainty\n\nOnly the name appears on [source]({source}); other details remain unverified."),
                action("inspect_site", path="index.html"),
                {"issues": []},
            )
            runner = TaskRunner(TaskStore(root / "tasks"), provider)
            with patch.object(WorkspaceTools, "read_url", return_value={"url": source, "content": "Subject page."}):
                result = runner.start(TaskSpec("Research and build a website with a source/uncertainty note.", str(root / "workspace")))
            self.assertEqual(result["status"], "completed", result)
            state = runner.store.load(result["task_id"])
            self.assertTrue(any("note is still missing" in str(item.get("result", {}).get("error", "")) for item in state["history"]))
            self.assertTrue(any(Path(path).name == "sources.md" for path in result["artifacts"]))

    def test_browser_write_without_domain_grant_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = WorkspaceTools(root / "workspace", root / "evidence", ActionGrant())
            tools._page = type("Page", (), {"url": "https://example.com/form"})()
            with self.assertRaises(PermissionError):
                tools.browser("click", selector="button")

    def test_denied_external_action_reports_blocked_draft(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(
                dict(PLAN, task_type="general", deliverables=["draft.md"]),
                action("write_file", path="draft.md", content="Draft ready for review."),
                action("browser", operation="click", selector="button.publish", effect="publish"),
                action("finish", summary="Draft ready; publishing blocked."),
                {"issues": []},
            )
            with patch.object(WorkspaceTools, "browser", side_effect=PermissionError("Publishing is not granted.")):
                result = TaskRunner(TaskStore(root / "tasks"), provider).start(
                    TaskSpec("Prepare and publish a draft.", str(root / "workspace"))
                )
            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["denied_actions"], 1)
            self.assertTrue(result["blocked_actions"])
            self.assertTrue(any("External action blocked" in gap for gap in result["unresolved_gaps"]))
            self.assertTrue(Path(result["artifacts"][0]).is_file())

    def test_browser_write_guard_blocks_cross_domain_requests(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = WorkspaceTools(root / "workspace", root / "evidence", ActionGrant(browser_write_domains=("example.com",), external_actions=("browser_write",)))
            tools._write_guard_active = True
            with patch("aeon_worker.tools._public_url", side_effect=lambda url: url):
                tools._guard_browser_request("https://example.com/submit")
                tools._guard_browser_request("https://sub.example.com/asset")
                with self.assertRaises(PermissionError):
                    tools._guard_browser_request("https://other.example.net/submit")

    def test_browser_preview_blocks_hidden_post_without_active_grant(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = WorkspaceTools(root / "workspace", root / "evidence", ActionGrant(browser_write_domains=("example.com",), external_actions=("browser_write",)))
            with patch("aeon_worker.tools._public_url", side_effect=lambda url: url):
                tools._guard_browser_request("https://example.com", method="GET")
                with self.assertRaises(PermissionError):
                    tools._guard_browser_request("https://example.com/submit", method="POST")
                tools._write_guard_active = True
                tools._guard_browser_request("https://example.com/submit", method="POST")
                with self.assertRaises(PermissionError):
                    tools._guard_browser_request("https://other.example.net/submit", method="POST")

    def test_local_browser_can_exercise_calculator_without_external_authority(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = WorkspaceTools(root / "workspace", root / "evidence", ActionGrant())
            tools.write_file("index.html", '<!doctype html><html><body><label for="number">Number</label><input id="number" type="number"><button id="calculate" onclick="document.getElementById(\'result\').textContent=Number(document.getElementById(\'number\').value)*2">Calculate</button><output id="result">0</output></body></html>')
            try:
                tools.browser("navigate_local", url="index.html")
                tools.browser("fill", selector="#number", value="21")
                result = tools.browser("click", selector="#calculate")
                self.assertIn("42", result["text"])
                self.assertFalse(tools._write_guard_active)
                with self.assertRaises(PermissionError):
                    tools.browser("click", selector="#calculate", effect="spend", amount=1)
                with self.assertRaises(PermissionError):
                    tools.browser("navigate_local", url="../outside.html")
            finally:
                tools.close()

    def test_worker_requires_current_interaction_evidence_before_completion(self):
        html = '<!doctype html><html lang="en"><head><title>Double</title><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><label for="number">Number</label><input id="number" type="number"><button id="calculate" onclick="document.getElementById(\'result\').textContent=Number(document.getElementById(\'number\').value)*2">Calculate</button><output id="result">0</output></body></html>'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ScriptedProvider(
                dict(PLAN, task_type="website", deliverables=["index.html"]),
                action("write_file", path="index.html", content=html),
                action("finish", summary="Done"),
                action("browser", operation="navigate_local", url="index.html"),
                action("browser", operation="fill", selector="#number", value="21"),
                action("browser", operation="click", selector="#calculate"),
                action("finish", summary="Verified double calculation"),
                {"issues": []},
            )
            result = TaskRunner(TaskStore(root / "tasks"), provider).start(TaskSpec("Build and verify a doubling calculator.", str(root / "workspace")))
            self.assertEqual(result["status"], "completed", result)
            self.assertEqual(result["revisions"], 1)
            self.assertIn("42", result["local_interaction_checks"][-1]["observed_text"])

            stale_provider = ScriptedProvider(
                dict(PLAN, task_type="website", deliverables=["index.html"]),
                action("write_file", path="index.html", content=html),
                action("browser", operation="navigate_local", url="index.html"),
                action("browser", operation="fill", selector="#number", value="21"),
                action("browser", operation="click", selector="#calculate"),
                action("write_file", path="index.html", content=html.replace("value)*2", "value)*3")),
                action("finish", summary="Done"),
            )
            stale = TaskRunner(TaskStore(root / "stale-tasks"), stale_provider).start(TaskSpec("Build a doubling calculator.", str(root / "stale-workspace"), max_revisions=0))
            self.assertEqual(stale["status"], "partial")
            self.assertTrue(any("no current browser interaction check" in item["issue"] for item in stale["findings"]))

    def test_granted_browser_action_executes_once_and_tracks_declared_spend(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            grant = ActionGrant(browser_write_domains=("example.com",), external_actions=("spend",), max_spend=5.0)
            tools = WorkspaceTools(root / "workspace", root / "evidence", grant)

            class Locator:
                first = None

                def count(self):
                    return 1

                def click(self, **kwargs):
                    self.clicked = True

                def inner_text(self, **kwargs):
                    return "Checkout ready"

            locator = Locator()
            locator.first = locator

            class Page:
                url = "https://example.com/checkout"

                def locator(self, selector):
                    return locator

                def title(self):
                    return "Checkout"

            tools._page = Page()
            with patch("aeon_worker.tools._public_url", side_effect=lambda url: url):
                with self.assertRaises(PermissionError):
                    tools.browser("click", selector="button.buy", effect="spend", amount=6.0)
                result = tools.browser("click", selector="button.buy", effect="spend", amount=3.0)
                self.assertEqual(result["url"], Page.url)
                self.assertTrue(locator.clicked)
                self.assertEqual(tools.spent, 3.0)
                self.assertTrue(tools._write_guard_active)

    def test_site_inspection_catches_undefined_form_handler(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = WorkspaceTools(root / "workspace", root / "evidence", ActionGrant())
            try:
                tools.write_file(
                    "index.html",
                    '<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Form</title></head><body><form onsubmit="missingHandler(event)"><button>Send</button></form></body></html>',
                )
                self.assertTrue(any("undefined" in item for item in tools.inspect_site("index.html")["issues"]))
            finally:
                tools.close()

    def test_site_inspection_accepts_inline_event_prevent_default(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = WorkspaceTools(root / "workspace", root / "evidence", ActionGrant())
            try:
                tools.write_file(
                    "index.html",
                    '<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Form</title></head><body><form onsubmit="event.preventDefault()"><button>Send</button><p>Demo only: your message is not sent.</p></form></body></html>',
                )
                self.assertFalse(any("undefined" in item for item in tools.inspect_site("index.html")["issues"]))
            finally:
                tools.close()

    def test_site_verifier_rejects_fake_form_delivery(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = WorkspaceTools(root / "workspace", root / "evidence", ActionGrant())
            try:
                tools.write_file("index.html", '<!doctype html><html lang="en"><head><title>Site</title><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><form><button>Send</button></form><script>const status = "Your message has been received";</script></body></html>')
                findings, _ = verify_artifacts(tools, ["index.html"], "website", [])
                self.assertTrue(any("no delivery backend" in item.issue for item in findings))
                tools.write_file("index.html", '<!doctype html><html lang="en"><head><title>Site</title><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><form><button>Send</button><p>Demo only: your message is not sent.</p></form></body></html>')
                safe_findings, _ = verify_artifacts(tools, ["index.html"], "website", [])
                self.assertFalse(any("no delivery backend" in item.issue for item in safe_findings))
            finally:
                tools.close()

    def test_review_does_not_mistake_excerpt_for_incomplete_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            html = '<!doctype html><html lang="en"><head><title>Site</title><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><main>' + ('<p>Detailed content.</p>' * 600) + '</main></body></html>'
            provider = ScriptedProvider(
                dict(PLAN, task_type="website", deliverables=["index.html"]),
                action("write_file", path="index.html", content=html),
                action("finish", summary="Done"),
                {"issues": ["Artifact truncated and cutting off mid-form inside contact section."]},
            )
            result = TaskRunner(TaskStore(root / "tasks"), provider).start(TaskSpec("Build a long local website.", str(root / "workspace")))
            self.assertEqual(result["status"], "completed", result)

    def test_benchmark_keeps_arms_blind_and_superiority_gate_closed_for_one_pair(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            providers = iter([
                ScriptedProvider(action("write_file", path="answer.json", content='{"answer": 1}'), action("finish", summary="Done")),
                ScriptedProvider(dict(PLAN, task_type="general", deliverables=["answer.json"]), action("write_file", path="answer.json", content='{"answer": 1}'), action("finish", summary="Done"), {"issues": []}),
            ])
            cases = [{"id": "case-one", "brief": "Produce a JSON answer.", "task_type": "general", "max_steps": 5}]
            summary = run_benchmark(cases, root / "bench", provider_factory=lambda: next(providers))
            self.assertEqual(summary["completed_direct"], 1)
            self.assertEqual(summary["completed_aeon"], 1)
            manifest = json.loads((root / "bench" / "blind-review-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest), 2)
            self.assertNotIn("arm", manifest[0])
            self.assertTrue((root / "bench" / "ratings-template.json").is_file())
            self.assertTrue((root / "bench" / "blind-review-instructions.md").is_file())
            ratings = {item["label"]: {"score": 0.8, "success": True, "factual_accuracy": 0.9, "useful_initiative": 0.7, "artifact_quality": 0.8} for item in manifest}
            ratings_path = root / "ratings.json"
            ratings_path.write_text(json.dumps(ratings), encoding="utf-8")
            report = analyze_benchmark(root / "bench", ratings_path)
            self.assertFalse(report["passed"])
            self.assertIn("sample_size", report["failed_gates"])
            self.assertIn("factual_accuracy", report["measured_metrics"]["aeon"])
            self.assertIsNone(report["measured_metrics"]["aeon"]["estimated_paid_list_cost_usd"])
            with patch.object(ProviderRouter, "complete", side_effect=AssertionError("Cached benchmark must not call model")):
                cached = run_benchmark(cases, root / "bench")
            self.assertEqual(cached["records"], 2)

    def test_partial_benchmark_resume_preflights_the_saved_exact_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            arm = root / "case-one" / "direct"
            arm.mkdir(parents=True)
            (arm / "result.json").write_text(json.dumps({"provider_route": [{"provider": "gemini", "model": "gemini-3.1-flash-lite"}]}), encoding="utf-8")
            with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), patch("aeon_worker.benchmark.ProviderRouter") as router:
                router.return_value.complete.side_effect = ProviderError("Unavailable")
                with self.assertRaises(RuntimeError):
                    run_benchmark([{"id": "case-one", "brief": "Write a note."}], root)
                self.assertEqual(router.call_args.kwargs["forced_provider"], "gemini")
                self.assertEqual(router.call_args.kwargs["gemini_model"], "gemini-3.1-flash-lite")
                self.assertIsNone(router.call_args.kwargs["gemini_backup_model"])

    def test_benchmark_retries_both_arms_after_provider_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            providers = iter([
                ScriptedProvider(ProviderError("temporarily unavailable")),
                ScriptedProvider(dict(PLAN, task_type="general", deliverables=["answer.json"]), action("write_file", path="answer.json", content='{"answer": 1}'), action("finish", summary="Done"), {"issues": []}),
                ScriptedProvider(action("write_file", path="answer.json", content='{"answer": 1}'), action("finish", summary="Done")),
                ScriptedProvider(dict(PLAN, task_type="general", deliverables=["answer.json"]), action("write_file", path="answer.json", content='{"answer": 1}'), action("finish", summary="Done"), {"issues": []}),
            ])
            cases = [{"id": "retry-case", "brief": "Produce a JSON answer.", "task_type": "general", "max_steps": 5}]
            first = run_benchmark(cases, root / "bench", provider_factory=lambda: next(providers))
            self.assertEqual(first["completed_direct"], 0)
            retried = run_benchmark(cases, root / "bench", provider_factory=lambda: next(providers), retry_interrupted=True)
            self.assertEqual(retried["completed_direct"], 1)
            self.assertEqual(retried["completed_aeon"], 1)
            self.assertTrue((root / "bench" / "retry-case" / "retry-1" / "previous-direct-result.json").is_file())

    def test_blind_pack_recovers_workspace_from_interrupted_checkpoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            case = root / "case-one"
            workspace = case / "aeon" / "workspace"
            workspace.mkdir(parents=True)
            artifact = workspace / "partial.md"
            artifact.write_text("Partial work", encoding="utf-8")
            run_dir = case / "aeon" / "tasks" / "task-abc"
            run_dir.mkdir(parents=True)
            (run_dir / "checkpoint.json").write_text(json.dumps({"spec": {"workspace": str(workspace)}}), encoding="utf-8")
            (case / "aeon" / "result.json").write_text(json.dumps({"status": "interrupted", "artifacts": [str(artifact)], "run_dir": str(run_dir)}), encoding="utf-8")
            direct = case / "direct"
            direct.mkdir()
            (direct / "result.json").write_text(json.dumps({"status": "failed", "artifacts": [], "workspace": str(direct / "workspace")}), encoding="utf-8")
            make_review_pack([{"id": "case-one", "brief": "Produce work."}], root)
            manifest = json.loads((root / "blind-review-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest), 2)
            self.assertEqual(sum((Path(item["artifact_directory"]) / "partial.md").is_file() for item in manifest), 1)

    def test_held_out_benchmark_has_thirty_balanced_cases(self):
        cases = load_cases(Path(__file__).resolve().parents[1] / "configs" / "aeon-worker-benchmark-30.json")
        self.assertEqual(len(cases), 30)
        self.assertEqual(sum(case["task_type"] == "research" for case in cases), 10)
        self.assertEqual(sum(case["task_type"] in {"website", "code"} for case in cases), 10)
        self.assertEqual(sum(case["task_type"] == "browser_file" for case in cases), 10)
        holdout = load_cases(Path(__file__).resolve().parents[1] / "configs" / "aeon-worker-benchmark-holdout-30-v2.json")
        self.assertEqual(len(holdout), 30)
        self.assertEqual(sum(case["task_type"] == "research" for case in holdout), 10)
        self.assertEqual(sum(case["task_type"] in {"website", "code"} for case in holdout), 10)
        self.assertEqual(sum(case["task_type"] == "browser_file" for case in holdout), 10)


if __name__ == "__main__":
    unittest.main()
