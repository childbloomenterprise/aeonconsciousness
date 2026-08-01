import pytest


@pytest.mark.asyncio
async def test_witness_detects_false_memory_claim(runtime):
    result = await runtime.process("Run source fidelity check")
    report = runtime.sakshin.witness(result.cycle_id, {"memory_refs": ["mem-never-retrieved"]})
    assert report["status"] == "POSSIBLE_CONFABULATION"


@pytest.mark.asyncio
async def test_model_observer_records_actual_provider(runtime):
    await runtime.process("Observe provider interaction")
    traces = runtime.storage.list_records("model_observer")
    assert traces[-1]["provider"] == "mock"
    assert traces[-1]["hidden_state_access"] is False
