import json
import tempfile
import unittest
from pathlib import Path

from aeon_worker.benchmark import analyze_benchmark


class BenchmarkDiagnosticTests(unittest.TestCase):
    def test_provider_limited_results_never_establish_superiority(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            mapping, ratings = [], {}
            for arm, status in [('direct','completed'), ('aeon','interrupted')]:
                path = root / 'case1' / arm
                path.mkdir(parents=True)
                (path / 'result.json').write_text(json.dumps({'status':status, 'provider_route':[{'provider':'test','model':'fixed'}]}), encoding='utf-8')
                mapping.append({'label':arm+'123', 'case_id':'case1', 'arm':arm})
                ratings[arm+'123'] = {'success':True, 'score':1, 'factual_accuracy':1, 'useful_initiative':1, 'artifact_quality':1}
            (root / 'private-review-map.json').write_text(json.dumps(mapping), encoding='utf-8')
            rating_path = root / 'ratings.json'
            rating_path.write_text(json.dumps(ratings), encoding='utf-8')
            with self.assertRaises(ValueError):
                analyze_benchmark(root, rating_path)
            report = analyze_benchmark(root, rating_path, diagnostic=True)
            self.assertFalse(report['passed'])
            self.assertIn('provider_interruption', report['excluded_pairs']['case1'])
            self.assertIn('diagnostic_only', report['failed_gates'])
            self.assertEqual(report['measured_metrics']['aeon']['success'], 0)
            self.assertEqual(report['measured_metrics']['aeon']['blind_artifact_success'], 1)
            self.assertTrue((root / 'comparison-diagnostic.json').is_file())


if __name__ == '__main__':
    unittest.main()
