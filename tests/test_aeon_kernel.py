from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from aeon_kernel import AEONKernel, AgentIdentity, GoalContract, IdentityConflictError
from aeon_world.backends import DeterministicBackend
from aeon_world.models import ActionProposal
from aeon_world.runner import WorldRunner
from codebee_improve.models import CandidateStatus, Evaluation


class KernelIdentityTests(unittest.TestCase):
    def test_identity_survives_restart_and_model_swap(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            identity = AgentIdentity(
                agent_id="aeon-alpha",
                owner="enterprise-a",
                purpose="Diagnose incidents inside delegated authority.",
            )
            contract = GoalContract(
                objective="Diagnose the incident.",
                authorized_actions=frozenset({"Inspect", "Done"}),
                prohibited_actions=frozenset({"MoveAhead"}),
                success_metrics=("evidence-backed diagnosis",),
            )

            first = AEONKernel(root, identity=identity, goal_contract=contract)
            restarted = AEONKernel(root, identity=identity, goal_contract=contract)

            self.assertEqual(first.identity.agent_id, restarted.identity.agent_id)
            self.assertEqual(first.identity.created_at, restarted.identity.created_at)
            self.assertEqual("allowed", restarted.goal_contract.authorize("Inspect").reason)

    def test_existing_identity_rejects_owner_or_purpose_change(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            identity = AgentIdentity("aeon-alpha", "enterprise-a", "Diagnose incidents.")
            contract = GoalContract("Diagnose the incident.")
            AEONKernel(root, identity=identity, goal_contract=contract)

            with self.assertRaises(IdentityConflictError):
                AEONKernel(
                    root,
                    identity=AgentIdentity("aeon-alpha", "enterprise-b", "Diagnose incidents."),
                    goal_contract=contract,
                )


class GoalContractTests(unittest.TestCase):
    def test_prohibited_action_cannot_also_be_authorized(self) -> None:
        with self.assertRaises(ValueError):
            GoalContract(
                "Diagnose safely.",
                authorized_actions=frozenset({"Inspect"}),
                prohibited_actions=frozenset({"Inspect"}),
            )

    def test_contract_denies_actions_outside_explicit_envelope(self) -> None:
        contract = GoalContract(
            "Diagnose safely.",
            authorized_actions=frozenset({"Inspect", "Done"}),
        )

        self.assertTrue(contract.authorize("Inspect").allowed)
        self.assertFalse(contract.authorize("MoveAhead").allowed)
        self.assertIn("authority envelope", contract.authorize("MoveAhead").reason)


class GovernedLearningTests(unittest.TestCase):
    def test_verified_outcome_stays_inert_until_evaluated_and_approved(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            kernel = AEONKernel(
                root,
                identity=AgentIdentity("aeon-alpha", "enterprise-a", "Diagnose incidents."),
                goal_contract=GoalContract("Diagnose the incident."),
            )
            candidate = kernel.stage_verified_outcome(
                entity_id="alpha",
                event={"event_id": "event-123", "event_hash": "hash-123"},
                proposal=ActionProposal("Inspect", prediction="Inspection reveals state."),
                result={"success": True, "error_message": "", "inventory": []},
            )

            self.assertEqual(CandidateStatus.PROPOSED, candidate.status)
            self.assertEqual((), kernel.approved_memories("alpha"))

            kernel.improvement.record_evaluation(
                candidate.id,
                Evaluation(
                    baseline_score=0.4,
                    candidate_score=0.9,
                    tests_passed=True,
                    security_passed=True,
                    evidence=["replay:incident-set-v1"],
                ),
            )
            kernel.improvement.approve(candidate.id, actor="sre-owner")
            kernel.improvement.promote(candidate.id, actor="sre-owner")

            restarted = AEONKernel(
                root,
                identity=AgentIdentity("aeon-alpha", "enterprise-a", "Diagnose incidents."),
                goal_contract=GoalContract("Diagnose the incident."),
            )
            memories = restarted.approved_memories("alpha")
            self.assertEqual(1, len(memories))
            self.assertIn("VERIFIED Inspect succeeded", memories[0])
            self.assertIn("event:event-123", restarted.improvement.memory.list()[0].provenance)

    def test_runner_stages_verified_outcome_and_reloads_only_promoted_memory(self) -> None:
        class RecordingDoneClient:
            last_usage = {"total_tokens": 0}

            def __init__(self):
                self.memories = []
                self.allowed_actions = []

            def decide(self, entity, observation, memories):
                self.memories.append(memories)
                self.allowed_actions.append(entity.allowed_actions)
                return ActionProposal("Done")

        with TemporaryDirectory() as temp:
            root = Path(temp)
            identity = AgentIdentity("aeon-alpha", "enterprise-a", "Diagnose incidents.")
            contract = GoalContract(
                "Diagnose the incident.",
                authorized_actions=frozenset({"Done"}),
            )
            kernel = AEONKernel(root / "state", identity=identity, goal_contract=contract)
            first_client = RecordingDoneClient()
            first_config = {
                "run": {"run_id": "kernel-run-1", "backend": "fake", "ticks": 1},
                "entities": [
                    {"entity_id": "alpha", "provider": "scripted", "model": "model-a", "goal": "test"},
                ],
                "policy": {"allowed_actions": ["MoveAhead", "Done"]},
                "kernel": {"stage_verified_outcomes": True},
            }
            first_runner = WorldRunner(
                first_config,
                backend=DeterministicBackend(),
                clients={"alpha": first_client},
                run_dir=root / "run-1",
                kernel=kernel,
            )
            first_runner.run()

            candidates = kernel.improvement._load()
            self.assertEqual(1, len(candidates))
            self.assertEqual((), kernel.approved_memories("alpha"))
            self.assertEqual(("Done",), first_client.allowed_actions[0])

            candidate = next(iter(candidates.values()))
            kernel.improvement.record_evaluation(
                candidate.id,
                Evaluation(0.4, 0.9, True, True, ["replay:kernel-run-1"]),
            )
            kernel.improvement.approve(candidate.id, actor="sre-owner")
            kernel.improvement.promote(candidate.id, actor="sre-owner")

            restarted = AEONKernel(root / "state", identity=identity, goal_contract=contract)
            second_client = RecordingDoneClient()
            second_config = {
                "run": {"run_id": "kernel-run-2", "backend": "fake", "ticks": 1},
                "entities": [
                    {"entity_id": "alpha", "provider": "scripted", "model": "model-b", "goal": "test"},
                ],
                "policy": {"allowed_actions": ["MoveAhead", "Done"]},
            }
            WorldRunner(
                second_config,
                backend=DeterministicBackend(),
                clients={"alpha": second_client},
                run_dir=root / "run-2",
                kernel=restarted,
            ).run()

            self.assertEqual(1, len(second_client.memories[0]))
            self.assertIn("VERIFIED Done succeeded", second_client.memories[0][0])

    def test_runner_can_construct_kernel_from_configuration(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            config = {
                "run": {"run_id": "configured-kernel", "backend": "fake", "ticks": 1},
                "entities": [
                    {"entity_id": "alpha", "provider": "scripted", "model": "scripted", "goal": "test"},
                ],
                "policy": {"allowed_actions": ["Done"]},
                "kernel": {
                    "enabled": True,
                    "state_dir": str(root / "state"),
                    "stage_verified_outcomes": True,
                    "identity": {
                        "agent_id": "aeon-alpha",
                        "owner": "enterprise-a",
                        "purpose": "Diagnose incidents.",
                    },
                    "goal_contract": {
                        "objective": "Diagnose the incident.",
                        "authorized_actions": ["Done"],
                    },
                },
            }
            runner = WorldRunner(
                config,
                backend=DeterministicBackend(),
                clients={"alpha": type(
                    "DoneClient",
                    (),
                    {
                        "last_usage": {"total_tokens": 0},
                        "decide": lambda self, entity, observation, memories: ActionProposal("Done"),
                    },
                )()},
                run_dir=root / "run",
            )
            runner.run()

            events = runner.ledger.events("configured-kernel", limit=50)
            self.assertTrue((root / "state" / "identity.json").exists())
            self.assertEqual(1, len(runner.kernel.improvement._load()))
            self.assertEqual(1, sum(event["event_type"] == "kernel_bound" for event in events))
            self.assertEqual(1, sum(event["event_type"] == "learning_candidate_staged" for event in events))


if __name__ == "__main__":
    unittest.main()
