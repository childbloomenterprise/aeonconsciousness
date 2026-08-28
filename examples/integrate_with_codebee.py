"""Minimal host integration. Replace evaluate_candidate with Codebee's eval runner."""
# ruff: noqa: E402 -- allow direct execution from an uninstalled source checkout

from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from codebee_improve import Evaluation, SelfImprovementEngine
from codebee_improve.review import build_review_prompt, stage_review_proposals


engine = SelfImprovementEngine(project_root, require_approval=True)

# Freeze once at session start; never rebuild mid-session.
session_memory = engine.memory.snapshot(["user", "project", "workspace", "agent"])
system_prompt_suffix = session_memory.render()

# After a meaningful completed task, run this prompt in an isolated reviewer:
conversation = [{"role": "user", "content": "Always add a regression test for fixes."}]
review_prompt = build_review_prompt(conversation, loaded_skills=["debugging"])

# Example structured reviewer output. No artifact becomes active here.
review_output = {
    "memory": [],
    "skills": [{
        "name": "debugging",
        "description": "Systematic debugging and regression prevention.",
        "instructions": "Reproduce, isolate, add a failing regression test, fix, and verify.",
        "rationale": "User established a durable bug-fix workflow.",
        "related_skills": ["testing"],
    }],
}
candidates = stage_review_proposals(engine, review_output, provenance="session:example")

# Real Codebee integration must produce these scores from a sandboxed eval suite.
candidate = candidates[0]
engine.record_evaluation(
    candidate.id,
    Evaluation(0.60, 0.85, tests_passed=True, security_passed=True, evidence=["eval:debugging-v1"]),
)

# Human/risk-policy approval gate.
engine.approve(candidate.id, actor="owner")
engine.promote(candidate.id, actor="owner")

print(f"Review prompt length: {len(review_prompt)}")
print(f"Frozen session prompt unchanged: {system_prompt_suffix!r}")
print(f"Promoted skill: {engine.skills.read('debugging')}")
