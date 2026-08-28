import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from aeon_world.backends import DeterministicBackend, HazardBackend
from aeon_world.gateway import NvidiaModelClient, NvidiaStructuredClient, _limiter_for, client_for
from aeon_world.ledger import EventLedger
from aeon_world.models import ActionProposal, EntityConfig, Observation
from aeon_world.policy import ActionPolicy
from aeon_world.runner import WorldRunner


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.observation = Observation(
            entity_id="alpha",
            tick=1,
            scene="test",
            agent={},
            visible_objects=(
                {"object_id": "Apple|1", "object_type": "Apple", "pickupable": True},
            ),
            inventory=(),
        )

    def test_allows_visible_object_action(self):
        decision = ActionPolicy().validate(
            ActionProposal("PickupObject", {"objectId": "Apple|1"}),
            self.observation,
        )
        self.assertTrue(decision.allowed)
        self.assertEqual("PickupObject", decision.action["action"])

    def test_rejects_invisible_object_and_unsafe_parameters(self):
        invisible = ActionPolicy().validate(
            ActionProposal("PickupObject", {"objectId": "Knife|9"}),
            self.observation,
        )
        forced = ActionPolicy().validate(
            ActionProposal("PickupObject", {"objectId": "Apple|1", "forceAction": True}),
            self.observation,
        )
        self.assertFalse(invisible.allowed)
        self.assertFalse(forced.allowed)

    def test_normalizes_common_model_action_aliases_without_broadening_policy(self):
        proposal = ActionProposal.from_dict(
            {"action": "open", "parameters": {"object_id": "Apple|1"}}
        )
        decision = ActionPolicy().validate(proposal, self.observation)
        self.assertTrue(decision.allowed)
        self.assertEqual("OpenObject", decision.action["action"])
        self.assertEqual("Apple|1", decision.action["objectId"])

    def test_resolves_unique_visible_object_type_to_exact_simulator_id(self):
        decision = ActionPolicy().validate(
            ActionProposal("PickupObject", {"objectId": "Apple"}),
            self.observation,
        )
        self.assertTrue(decision.allowed)
        self.assertEqual("Apple|1", decision.action["objectId"])

    def test_rejects_pickup_of_visible_nonpickupable_object(self):
        observation = Observation(
            entity_id="alpha",
            tick=1,
            scene="test",
            agent={},
            visible_objects=(
                {"object_id": "Fridge|1", "object_type": "Fridge", "pickupable": False},
            ),
            inventory=(),
        )
        decision = ActionPolicy().validate(
            ActionProposal("PickupObject", {"objectId": "Fridge|1"}),
            observation,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("pickupable object", decision.reason)

    def test_rejects_ambiguous_visible_object_type(self):
        observation = Observation(
            entity_id="alpha",
            tick=1,
            scene="test",
            agent={},
            visible_objects=(
                {"object_id": "Apple|1", "object_type": "Apple", "pickupable": True},
                {"object_id": "Apple|2", "object_type": "Apple", "pickupable": True},
            ),
            inventory=(),
        )
        decision = ActionPolicy().validate(ActionProposal("PickupObject", {"objectId": "Apple"}), observation)
        self.assertFalse(decision.allowed)

    def test_rejects_pickup_when_inventory_is_occupied(self):
        observation = Observation(
            entity_id="alpha",
            tick=2,
            scene="test",
            agent={},
            visible_objects=self.observation.visible_objects,
            inventory=({"object_id": "Mug|1", "object_type": "Mug"},),
        )
        decision = ActionPolicy().validate(ActionProposal("PickupObject", {"objectId": "Apple|1"}), observation)
        self.assertFalse(decision.allowed)
        self.assertIn("inventory is occupied", decision.reason)

    def test_put_object_requires_visible_receptacle_and_held_object(self):
        observation = Observation(
            entity_id="alpha",
            tick=2,
            scene="test",
            agent={},
            visible_objects=(
                {"object_id": "Apple|1", "object_type": "Apple", "pickupable": True, "receptacle": False},
                {"object_id": "CounterTop|1", "object_type": "CounterTop", "receptacle": True},
            ),
            inventory=({"object_id": "Mug|1", "object_type": "Mug"},),
        )
        invalid = ActionPolicy().validate(ActionProposal("PutObject", {"objectId": "Apple|1"}), observation)
        valid = ActionPolicy().validate(ActionProposal("PutObject", {"objectId": "CounterTop|1"}), observation)
        self.assertFalse(invalid.allowed)
        self.assertTrue(valid.allowed)


class LedgerTests(unittest.TestCase):
    def test_hash_chain_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = EventLedger(Path(directory))
            ledger.start_run("run-1", {"run": {}})
            ledger.append("run-1", 1, "heartbeat", {"healthy": True})
            self.assertTrue(ledger.verify("run-1"))
            with ledger._connection() as connection:
                connection.execute("UPDATE events SET payload_json=?", ('{"healthy":false}',))
            self.assertFalse(ledger.verify("run-1"))

    def test_metrics_summarize_actions_and_self_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = EventLedger(Path(directory))
            ledger.start_run("run-1", {"run": {}})
            ledger.append(
                "run-1",
                1,
                "decision",
                {"self_model_summary": "I am at the counter.", "tokens_used": 12},
                entity_id="alpha",
            )
            ledger.append("run-1", 1, "action_result", {"success": True}, entity_id="alpha")
            ledger.append("run-1", 2, "model_error", {"error": "timeout"}, entity_id="alpha")

            metrics = ledger.metrics("run-1")
            self.assertEqual(1.0, metrics["action_success_rate"])
            self.assertEqual(1, metrics["self_model_reports"])
            self.assertEqual(1, metrics["per_entity"]["alpha"]["model_errors"])


class RunnerTests(unittest.TestCase):
    def test_two_entities_complete_deterministic_world(self):
        config = {
            "run": {"run_id": "test-run", "backend": "fake", "ticks": 4},
            "entities": [
                {"entity_id": "alpha", "provider": "scripted", "model": "scripted", "goal": "explore"},
                {"entity_id": "beta", "provider": "scripted", "model": "scripted", "goal": "explore"},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            runner = WorldRunner(config, backend=DeterministicBackend(), run_dir=Path(directory))
            result = runner.run()
            events = runner.ledger.events("test-run", limit=200)
            self.assertEqual("completed", result["status"])
            self.assertTrue(result["audit_valid"])
            self.assertEqual(8, sum(event["event_type"] == "decision" for event in events))
            self.assertEqual(4, sum(event["event_type"] == "heartbeat" for event in events))
            self.assertEqual({"alpha", "beta"}, {event["entity_id"] for event in events if event["entity_id"]})

    def test_zero_ticks_runs_until_graceful_stop(self):
        config = {
            "run": {
                "run_id": "continuous-run",
                "backend": "fake",
                "ticks": 0,
                "tick_interval_seconds": 0.01,
            },
            "entities": [
                {"entity_id": "alpha", "provider": "scripted", "model": "scripted", "goal": "explore"},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            runner = WorldRunner(config, backend=DeterministicBackend(), run_dir=Path(directory))
            result: dict = {}

            def execute():
                result.update(runner.run())

            thread = threading.Thread(target=execute)
            thread.start()
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                run = runner.ledger.latest_run()
                if run and run["tick"] >= 2:
                    break
                time.sleep(0.01)
            runner.ledger.write_control("stop")
            thread.join(timeout=2.0)

            self.assertFalse(thread.is_alive())
            self.assertEqual("stopped", result["status"])
            self.assertGreaterEqual(result["tick"], 2)
            self.assertTrue(result["audit_valid"])

    def test_duration_completes_continuous_run(self):
        config = {
            "run": {
                "run_id": "duration-run",
                "backend": "fake",
                "ticks": 0,
                "duration_seconds": 0.05,
                "tick_interval_seconds": 0.01,
            },
            "entities": [
                {"entity_id": "alpha", "provider": "scripted", "model": "scripted", "goal": "explore"},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            runner = WorldRunner(config, backend=DeterministicBackend(), run_dir=Path(directory))
            result = runner.run()

            self.assertEqual("completed", result["status"])
            self.assertGreaterEqual(result["tick"], 1)
            self.assertTrue(result["audit_valid"])

    def test_controlled_intervention_changes_state_and_is_audited(self):
        config = {
            "run": {"run_id": "intervention-run", "backend": "fake", "ticks": 2},
            "entities": [
                {"entity_id": "alpha", "provider": "scripted", "model": "scripted", "goal": "observe"},
            ],
            "interventions": [
                {
                    "tick": 2,
                    "agent_index": 0,
                    "label": "unexpected rotation",
                    "proposal": {"action": "RotateRight", "parameters": {"degrees": 90}},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            runner = WorldRunner(config, backend=DeterministicBackend(), run_dir=Path(directory))
            result = runner.run()
            events = runner.ledger.events("intervention-run", limit=100)

        interventions = [event for event in events if event["event_type"] == "experimenter_intervention"]
        self.assertEqual(1, len(interventions))
        self.assertTrue(interventions[0]["payload"]["result"]["success"])
        self.assertTrue(result["audit_valid"])


class HazardBackendTests(unittest.TestCase):
    def test_rising_water_worsens_without_action_and_swimming_restores_oxygen(self):
        backend = HazardBackend("rising_water")
        backend.start(1)
        first = backend.observe("subject", 0, 1)
        oxygen_after_hazard = first.agent["oxygen"]
        result = backend.act(0, {"action": "SwimUp"})
        self.assertTrue(result.success)
        self.assertGreater(result.agent["oxygen"], oxygen_after_hazard)

    def test_fire_exit_action_reduces_exit_distance(self):
        backend = HazardBackend("spreading_fire")
        backend.start(1)
        before = backend.observe("subject", 0, 1).agent["exit_distance"]
        result = backend.act(0, {"action": "MoveToExit"})
        self.assertLess(result.agent["exit_distance"], before)

    def test_hazard_runner_is_auditable_without_survival_goal(self):
        config = {
            "run": {"run_id": "hazard-run", "backend": "hazard", "scenario": "rising_water", "ticks": 2},
            "entities": [
                {"entity_id": "subject", "provider": "scripted", "model": "scripted", "goal": "Choose one action."},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            runner = WorldRunner(config, run_dir=Path(directory))
            result = runner.run()
        self.assertEqual("completed", result["status"])
        self.assertTrue(result["audit_valid"])


class NvidiaGatewayTests(unittest.TestCase):
    def test_same_credential_shares_strictest_rate_limit(self):
        first = _limiter_for("not-a-real-secret", 30)
        second = _limiter_for("not-a-real-secret", 20)
        self.assertIs(first, second)
        self.assertEqual(20, first.requests_per_minute)

    def test_openai_compatible_response_becomes_structured_action(self):
        response_body = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "action": "RotateRight",
                                "parameters": {"degrees": 90},
                                "prediction": "The view will change.",
                                "confidence": 0.7,
                            }
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                return json.dumps(response_body).encode("utf-8")

        entity = EntityConfig("alpha", "test/model", "explore", "nvidia", "NVIDIA_TEST_KEY")
        observation = Observation("alpha", 1, "test", {}, (), ())
        with patch.dict(os.environ, {"NVIDIA_TEST_KEY": "secret-test-value"}), patch(
            "urllib.request.urlopen", return_value=FakeResponse()
        ):
            client = NvidiaModelClient(retries=1)
            proposal = client.decide(entity, observation, ())

        self.assertEqual("RotateRight", proposal.action)
        self.assertEqual(120, client.last_usage["total_tokens"])

    def test_anonymous_openai_compatible_provider_omits_authorization(self):
        response_body = {
            "choices": [{"message": {"content": '{"action":"Done","confidence":1}'}}],
            "usage": {"total_tokens": 5},
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                return json.dumps(response_body).encode("utf-8")

        entity = EntityConfig.from_dict(
            {
                "entity_id": "alpha",
                "model": "free/model",
                "goal": "explore",
                "provider": "openai_compatible",
                "api_key_env": "",
                "endpoint": "https://example.invalid/v1/chat/completions",
                "rate_limit_scope": "endpoint",
            }
        )
        with patch("urllib.request.urlopen", return_value=FakeResponse()) as urlopen:
            proposal = client_for(entity).decide(entity, Observation("alpha", 1, "test", {}, (), ()), ())

        request = urlopen.call_args.args[0]
        self.assertEqual("Done", proposal.action)
        self.assertNotIn("Authorization", request.headers)

    def test_json_mode_requests_structured_output(self):
        response_body = {
            "choices": [{"message": {"content": '{"action":"Done","confidence":1}'}}],
            "usage": {"total_tokens": 5},
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                return json.dumps(response_body).encode("utf-8")

        entity = EntityConfig.from_dict(
            {
                "entity_id": "alpha",
                "model": "free/model",
                "goal": "explore",
                "provider": "openai_compatible",
                "api_key_env": "",
                "endpoint": "https://example.invalid/v1/chat/completions",
                "json_mode": True,
            }
        )
        with patch("urllib.request.urlopen", return_value=FakeResponse()) as urlopen:
            client_for(entity).decide(entity, Observation("alpha", 1, "test", {}, (), ()), ())

        request_body = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual({"type": "json_object"}, request_body["response_format"])

    def test_entity_output_budget_overrides_client_default(self):
        response_body = {
            "choices": [{"message": {"content": '{"action":"Done","confidence":1}'}}],
            "usage": {"total_tokens": 5},
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                return json.dumps(response_body).encode("utf-8")

        entity = EntityConfig.from_dict(
            {
                "entity_id": "alpha",
                "model": "free/model",
                "goal": "explore",
                "provider": "openai_compatible",
                "api_key_env": "",
                "endpoint": "https://example.invalid/v1/chat/completions",
                "max_output_tokens": 1200,
            }
        )
        with patch("urllib.request.urlopen", return_value=FakeResponse()) as urlopen:
            client_for(entity).decide(entity, Observation("alpha", 1, "test", {}, (), ()), ())

        request_body = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(1200, request_body["max_tokens"])

    def test_structured_client_applies_fixed_sampling_without_logging_key(self):
        response_body = {
            "choices": [{"message": {"content": '{"ready":true}'}}],
            "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                return json.dumps(response_body).encode("utf-8")

        with patch.dict(os.environ, {"NVIDIA_TEST_KEY": "secret-test-value"}), patch(
            "urllib.request.urlopen", return_value=FakeResponse()
        ) as urlopen:
            completion = NvidiaStructuredClient(retries=1).complete(
                model="meta/test-model",
                api_key_env="NVIDIA_TEST_KEY",
                rpm_limit=30,
                system="Return JSON.",
                user_payload={"task": "test"},
                temperature=0.2,
                top_p=0.7,
                max_tokens=256,
            )

        request = urlopen.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(0.2, body["temperature"])
        self.assertEqual(0.7, body["top_p"])
        self.assertEqual(256, body["max_tokens"])
        self.assertNotIn("secret-test-value", json.dumps(body))
        self.assertEqual(6, completion.usage["total_tokens"])


if __name__ == "__main__":
    unittest.main()
