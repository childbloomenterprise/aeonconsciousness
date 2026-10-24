import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from aeon_develop.agent import AeonConfig, Task
from aeon_develop.experiment import PREDICTIONS, evaluate, preregister, run_condition
from aeon_develop.inquiry import EXPERIMENTS, HYPOTHESES, TIMING, expected_info_gain
from aeon_develop.plasticity import BoundedParam, Trace
from aeon_develop.session import Session
from aeon_develop.story import GuidedStory


def developed(seed=0, **cfg):
    s = Session(seed, AeonConfig(seed=seed, **cfg))
    s.add(Task("fetch"))
    s.run_queue()
    return s


class BodyDiscoveryTests(unittest.TestCase):
    def test_discovers_own_body_and_object_channels_from_shuffled_labels(self):
        for seed in (0, 1, 2):
            s = developed(seed)
            truth = s.world.truth_channel_map()
            sm = s.agent.sm
            self.assertEqual(set(sm.hand_channels), {truth["hand_x"], truth["hand_y"]})
            self.assertEqual(set(sm.object_channels), {truth["obj_x"], truth["obj_y"]})
            same_order = (sm.hand_channels[0] == truth["hand_x"]) == (sm.object_channels[0] == truth["obj_x"])
            self.assertTrue(same_order, "object coordinates must align with hand coordinates")
            self.assertEqual(sm.channels[truth["touch"]].role, "contact-interface")
            self.assertEqual(sm.channels[truth["light"]].role, "external-unrelated")
            self.assertAlmostEqual(sm.reach, 0.6, delta=0.15)


class SecretDelayTests(unittest.TestCase):
    def test_delay_is_diagnosed_by_experiment_and_reused_for_catching(self):
        s = developed(0)
        s.add(Task("fetch", before=lambda w: w.set_delay(3)), Task("fetch"), s.catch_task(), s.catch_task())
        s.run_queue()
        agent = s.agent
        self.assertEqual(agent.sm.delay, 3)
        timing = [i for i in agent.inquiries if i.conclusion == TIMING]
        self.assertTrue(timing)
        self.assertIn("probe_pulse", [st.kind for st in timing[0].steps])
        catches = [t for t in agent.task_log if t.kind == "catch"]
        self.assertTrue(all(t.thought == "imagine" for t in catches))
        self.assertGreaterEqual(sum(t.success and t.misses == 0 for t in catches), 1)

    def test_frozen_self_model_notices_but_cannot_revise(self):
        s = developed(0, freeze_self_model=True)
        s.add(Task("fetch", before=lambda w: w.set_delay(3)), Task("fetch"))
        s.run_queue()
        self.assertEqual(s.agent.sm.delay, 0)
        self.assertTrue(any(not r.accepted and r.param == "delay" for r in s.agent.sm.revisions))


class VisionAndToolTests(unittest.TestCase):
    def test_vision_bias_is_measured_by_touch_and_corrected(self):
        s = developed(0)
        s.add(*[Task("fetch") for _ in range(3)])
        s.queue[0].before = lambda w: w.set_vision_bias(1.3, 0.4)
        s.run_queue()
        sm, truth = s.agent.sm, s.world.truth_channel_map()
        off = dict(zip(sm.object_channels, sm.vision_offset))
        self.assertAlmostEqual(off[truth["obj_x"]], 1.3, delta=0.25)
        self.assertAlmostEqual(off[truth["obj_y"]], 0.4, delta=0.25)
        self.assertTrue(s.agent.task_log[-1].success)

    def test_new_tool_signal_is_incorporated_and_extends_reach(self):
        s = developed(0)
        s.add(Task("fetch", before=lambda w: w.attach_tool()), s.far_task(), s.far_task())
        s.run_queue()
        sm = s.agent.sm
        self.assertIn("s6", sm.tool_channels)
        self.assertGreater(sm.reach, 1.2)
        self.assertTrue(any(t.success for t in s.agent.task_log if t.kind == "far"))


class MechanismTests(unittest.TestCase):
    def test_bounded_param_respects_bounds_step_and_is_traced(self):
        trace = Trace()
        p = BoundedParam("x", 0.5, 0.0, 1.0, 0.1, trace)
        p.nudge(5.0, 1.0, "rule", "cause")
        self.assertAlmostEqual(p.value, 0.6)
        self.assertEqual(trace.events[-1].param, "x")
        p.frozen = True
        p.nudge(0.0, 1.0, "rule", "cause")
        self.assertAlmostEqual(p.value, 0.6)

    def test_probe_pulse_is_most_informative_between_motor_hypotheses(self):
        posterior = {h: 0.0 for h in HYPOTHESES}
        posterior.update({"action_failed": 0.5, "action_timing_changed": 0.5})
        gains = {e: expected_info_gain(posterior, e) for e in EXPERIMENTS}
        self.assertEqual(max(gains, key=gains.get), "probe_pulse")

    def test_situation_graph_links_perception_memory_and_doubt(self):
        s = developed(0)
        agent = s.agent
        agent.sm.channel(agent.sm.object_channels[0]).unreliable_events = 1
        agent.current_task = Task("fetch")
        agent.memory.place("cube", (0.5, 0.5), agent.n, "me")
        g = agent.situation()
        self.assertTrue(g.has_edge("self", "moved", "object:cube"))
        self.assertTrue(g.has_edge("prediction:object:cube", "contradicted_by"))
        self.assertTrue(g.edges_from("object:cube", "uncertain_because"))
        self.assertIn("I moved", g.narrate()[0])


class ExperimentTests(unittest.TestCase):
    def test_preregistration_is_hashed_and_predictions_are_evaluated(self):
        with TemporaryDirectory() as tmp:
            body = preregister(Path(tmp) / "p.json", [0])
            self.assertEqual(len(body["sha256"]), 64)
            self.assertEqual(json.loads((Path(tmp) / "p.json").read_text())["predictions"], PREDICTIONS)
        intact = run_condition("intact", 0)["metrics"]
        frozen = run_condition("frozen_self_model", 0)["metrics"]
        summary = {name: intact for name in ("intact", "attention_disconnected", "foreign_predictions", "memory_loss", "reduced_compute", "simple_adaptive_controller")}
        summary["frozen_self_model"] = frozen
        results = {p["id"]: p for p in evaluate(summary)}
        self.assertTrue(results["P2"]["held"])


class GuidedStoryTests(unittest.TestCase):
    def test_guided_demo_runs_every_scene_to_completion(self):
        s = Session(0, AeonConfig(seed=0), live=True)
        story = GuidedStory(s)
        while not story.done and s.agent.n < 8000:
            s.step()
            story.tick()
        self.assertTrue(story.done)
        self.assertTrue(all(r.endswith("True") for r in story.results), story.results)
        far = [t for t in s.agent.task_log if t.kind == "far"]
        self.assertTrue(far[0].declined and far[-1].success)


if __name__ == "__main__":
    unittest.main()
