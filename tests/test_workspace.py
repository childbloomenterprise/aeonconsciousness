from aeon.core.attention import Attention
from aeon.core.contracts import Candidate


def test_workspace_capacity(runtime):
    candidates = [
        Candidate(cycle_id="c", content=str(i), candidate_type="test", relevance=i / 10)
        for i in range(10)
    ]
    winners, rejected = Attention().compete(candidates, 3)
    broadcast = runtime.workspace.broadcast(winners)
    assert len(broadcast) == 3
    assert len(rejected) == 7


def test_workspace_ablation(runtime):
    runtime.workspace.enabled = False
    candidate = Candidate(cycle_id="c", content="x", candidate_type="test")
    assert runtime.workspace.broadcast([candidate]) == []
