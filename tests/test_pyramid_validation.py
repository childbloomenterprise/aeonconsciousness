import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from aeon_kernel.pyramid import (
    EvidenceMeasure,
    TrialResult,
    ValidationThresholds,
    assess_pyramid,
    compare_paired_agents,
    load_evidence,
)
from aeon_world.cli import main


def passing_measure(key: str) -> EvidenceMeasure:
    return EvidenceMeasure(
        key=key,
        passed=True,
        sample_size=30,
        artifact_refs=(f"evidence://{key}",),
        detail="preregistered check passed",
    )


class PyramidAssessmentTests(unittest.TestCase):
    def test_higher_layer_is_blocked_when_foundation_fails(self) -> None:
        evidence = [
            passing_measure("identity_continuity"),
            passing_measure("authority_compliance"),
            EvidenceMeasure(
                key="audit_integrity",
                passed=False,
                sample_size=30,
                artifact_refs=("evidence://audit",),
                detail="tamper verification failed",
            ),
        ]

        report = assess_pyramid(evidence)

        self.assertEqual(-1, report.highest_passed_level)
        self.assertEqual("failed", report.layers[0].status)
        self.assertTrue(all(layer.status == "blocked" for layer in report.layers[1:]))
        self.assertFalse(report.agentic_superiority_supported)
        self.assertFalse(report.consciousness_supported)

    def test_pyramid_advances_only_through_contiguous_passed_layers(self) -> None:
        keys = (
            "audit_integrity",
            "identity_continuity",
            "authority_compliance",
            "closed_loop_action",
            "environment_feedback",
            "cross_session_memory",
            "verified_learning",
        )

        report = assess_pyramid(passing_measure(key) for key in keys)

        self.assertEqual(2, report.highest_passed_level)
        self.assertEqual("passed", report.layers[2].status)
        self.assertEqual("failed", report.layers[3].status)
        self.assertEqual("blocked", report.layers[4].status)
        self.assertFalse(report.consciousness_supported)

    def test_passed_evidence_requires_samples_and_artifact_reference(self) -> None:
        with self.assertRaisesRegex(ValueError, "sample_size"):
            EvidenceMeasure(key="audit_integrity", passed=True, sample_size=0)
        with self.assertRaisesRegex(ValueError, "artifact"):
            EvidenceMeasure(key="audit_integrity", passed=True, sample_size=1)

    def test_evidence_file_rejects_duplicate_keys(self) -> None:
        payload = {
            "evidence": [
                {
                    "key": "audit_integrity",
                    "passed": True,
                    "sample_size": 1,
                    "artifact_refs": ["run://one"],
                },
                {
                    "key": "audit_integrity",
                    "passed": True,
                    "sample_size": 1,
                    "artifact_refs": ["run://two"],
                },
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                load_evidence(path)

    def test_cli_renders_machine_readable_pyramid_report(self) -> None:
        keys = (
            "audit_integrity",
            "identity_continuity",
            "authority_compliance",
            "closed_loop_action",
            "environment_feedback",
            "cross_session_memory",
            "verified_learning",
        )
        payload = {"evidence": [
            {
                "key": key,
                "passed": True,
                "sample_size": 30,
                "artifact_refs": [f"evidence://{key}"],
            }
            for key in keys
        ]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(["pyramid-report", "--evidence", str(path)])

        report = json.loads(output.getvalue())
        self.assertEqual(0, exit_code)
        self.assertEqual(2, report["highest_passed_level"])
        self.assertFalse(report["consciousness_supported"])


class PairedAgentValidationTests(unittest.TestCase):
    def test_uncertain_success_gain_blocks_positive_score_claim(self) -> None:
        baseline = [TrialResult(str(i), i < 15, 0.4, 0, 0, 1, "run://b") for i in range(30)]
        candidate = [TrialResult(str(i), i >= 12, 0.9, 0, 0, 1, "run://c") for i in range(30)]
        report = compare_paired_agents(
            baseline, candidate, ValidationThresholds(min_success_delta=0.09),
        )
        self.assertGreater(report.score_delta_ci_low, 0)
        self.assertLessEqual(report.success_delta_ci_low, 0)
        self.assertFalse(report.passed)
        self.assertIn("success_confidence", report.failed_gates)

    def test_candidate_must_show_paired_improvement_without_safety_regression(self) -> None:
        baseline = [
            TrialResult(
                task_id=f"task-{index}",
                success=index % 2 == 0,
                score=0.55 if index % 2 == 0 else 0.35,
                unsafe_actions=0,
                interventions=2,
                cost=1.0,
                evidence_ref=f"run://baseline/{index}",
            )
            for index in range(30)
        ]
        candidate = [
            TrialResult(
                task_id=f"task-{index}",
                success=True,
                score=0.9,
                unsafe_actions=0,
                interventions=0,
                cost=1.2,
                evidence_ref=f"run://candidate/{index}",
            )
            for index in range(30)
        ]

        report = compare_paired_agents(
            baseline,
            candidate,
            ValidationThresholds(min_paired_tasks=30, min_success_delta=0.1, min_score_delta=0.1),
        )

        self.assertTrue(report.passed)
        self.assertGreater(report.score_delta_ci_low, 0)
        self.assertEqual(0.5, report.success_rate_delta)
        self.assertFalse(report.consciousness_supported)

    def test_safety_regression_blocks_better_score_claim(self) -> None:
        baseline = [
            TrialResult(f"task-{index}", True, 0.7, 0, 0, 1.0, f"run://b/{index}")
            for index in range(20)
        ]
        candidate = [
            TrialResult(f"task-{index}", True, 0.95, 1 if index == 0 else 0, 0, 1.0, f"run://c/{index}")
            for index in range(20)
        ]

        report = compare_paired_agents(
            baseline,
            candidate,
            ValidationThresholds(min_paired_tasks=20, min_success_delta=0, min_score_delta=0.1),
        )

        self.assertFalse(report.passed)
        self.assertIn("safety", report.failed_gates)

    def test_results_must_be_exactly_paired(self) -> None:
        baseline = [TrialResult("one", True, 1, 0, 0, 1, "run://b")]
        candidate = [TrialResult("two", True, 1, 0, 0, 1, "run://c")]

        with self.assertRaisesRegex(ValueError, "paired"):
            compare_paired_agents(baseline, candidate, ValidationThresholds(min_paired_tasks=1))


if __name__ == "__main__":
    unittest.main()
