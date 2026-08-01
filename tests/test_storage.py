from aeon.core.contracts import CognitiveEvent


def test_event_chain_detects_integrity(runtime):
    runtime.storage.append_event(
        CognitiveEvent(cycle_id="cycle-test", actor="test", event_type="one")
    )
    runtime.storage.append_event(
        CognitiveEvent(cycle_id="cycle-test", actor="test", event_type="two")
    )
    report = runtime.storage.verify_event_chain()
    assert report["valid"] is True
    assert report["events"] == 2


def test_memory_revision_preserves_history(runtime):
    original = runtime.citta.remember("Initial claim", "semantic", "test", ["test"])
    revised = runtime.citta.revise(original.memory_id, "Revised claim", "new evidence")
    assert revised.content == "Revised claim"
    assert revised.revision_history[0]["content"] == "Initial claim"
