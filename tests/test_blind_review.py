from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aeon_worker.blind_review import review_blind_manifest, _validated_rating
from aeon_worker.providers import ModelReply
from aeon_worker.tools import WorkspaceTools


class BlindReviewTests(unittest.TestCase):
    def test_missing_artifact_fails_without_model_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / 'empty123'
            artifact.mkdir()
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps([{'label':'empty123', 'brief':'Deliver a report.', 'artifact_directory':str(artifact)}]), encoding='utf-8')
            output = root / 'ratings.json'
            review_blind_manifest(manifest, output, provider_factory=lambda: self.fail('Missing artifact must not call a model'))
            self.assertFalse(json.loads(output.read_text())['empty123']['success'])
            checkpoint = json.loads(output.with_suffix('.review-checkpoint.json').read_text())
            self.assertEqual(checkpoint['reviews']['0:empty123']['reviewer']['kind'], 'deterministic_missing_artifact_rule')

    def test_reviews_public_artifacts_only_and_resumes_without_regrading(self):
        calls = []

        class Reviewer:
            def complete(self, system, payload, **kwargs):
                calls.append(payload)
                return ModelReply({"score": .8, "success": True, "factual_accuracy": .9, "useful_initiative": .7, "artifact_quality": .8, "findings": [], "evidence_limits": []}, "test", "judge", 10)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "opaque123"
            artifact.mkdir()
            (artifact / "answer.md").write_text("Answer supported by https://example.com/source", encoding="utf-8")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps([{"label": "opaque123", "brief": "Explain a fact.", "artifact_directory": str(artifact)}]), encoding="utf-8")
            (root / "private-review-map.json").write_text("INVALID JSON: MUST NEVER READ", encoding="utf-8")
            output = root / "ratings.json"
            with patch.object(WorkspaceTools, "read_url", return_value={"url": "https://example.com/source", "content": "Independent source fact."}):
                result = review_blind_manifest(manifest, output, provider_factory=Reviewer)
                review_blind_manifest(manifest, output, provider_factory=lambda: self.fail("Cached review called model"))
            self.assertEqual(len(calls), 2)
            self.assertEqual(result["reviewer_kind"], "automated_model")
            self.assertTrue(json.loads(output.read_text())["opaque123"]["success"])
            self.assertNotIn("arm", calls[0])
            self.assertEqual(calls[0]["evidence"][0]["excerpt"], "Independent source fact.")

    def test_scores_reject_non_boolean_success_and_nonfinite_values(self):
        valid = {"score": .8, "success": True, "factual_accuracy": .9, "useful_initiative": .7, "artifact_quality": .8}
        for change in ({"success": "true"}, {"score": float("nan")}, {"factual_accuracy": 1.1}):
            with self.assertRaises(ValueError):
                _validated_rating(valid | change)


if __name__ == "__main__":
    unittest.main()
