import pytest


def test_experiments_are_seeded_and_hashed(runtime):
    record = runtime.experiments.create("Workspace matters", seed=7, ablations=["workspace"])
    assert record["seed"] == 7
    assert len(record["integrity_hash"]) == 64


def test_unknown_ablation_rejected(runtime):
    with pytest.raises(ValueError):
        runtime.experiments.create("Invalid", ablations=["magic"])


def test_vi_mode_quarantines_hypothesis(runtime):
    record = runtime.vi_mode.run("Explore identity continuity", [])
    assert record["quarantine_status"] == "QUARANTINED"
    assert record["canonical_belief_update"] is False
