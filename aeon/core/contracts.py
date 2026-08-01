from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class EpistemicClass(StrEnum):
    IMPLEMENTED = "implemented_capability"
    OBSERVATION = "observation"
    MEMORY = "memory"
    INFERENCE = "inference"
    PREDICTION = "prediction"
    HYPOTHESIS = "hypothesis"
    SPECULATIVE = "speculative"
    UNVERIFIED = "unverified"
    CONTRADICTED = "contradicted"
    UNKNOWN = "unknown"


class ControlSignal(StrEnum):
    CONTINUE = "CONTINUE"
    RETRIEVE = "RETRIEVE"
    VERIFY = "VERIFY"
    CHANGE_STRATEGY = "CHANGE_STRATEGY"
    REDUCE_CONFIDENCE = "REDUCE_CONFIDENCE"
    ABSTAIN = "ABSTAIN"
    REQUEST_CLARIFICATION = "REQUEST_CLARIFICATION"
    ENTER_VI_MODE = "ENTER_VI_MODE"


class Candidate(BaseModel):
    candidate_id: str = Field(default_factory=lambda: new_id("cand"))
    cycle_id: str
    content: str
    candidate_type: str
    origin_module: str = "manas"
    created_at: datetime = Field(default_factory=utc_now)
    novelty: float = 0.5
    relevance: float = 0.5
    uncertainty: float = 0.5
    contradiction_strength: float = 0.0
    identity_relevance: float = 0.0
    expected_consequence: float = 0.2
    homeostatic_urgency: float = 0.0
    redundancy: float = 0.0
    estimated_noise: float = 0.1
    provenance: list[str] = Field(default_factory=list)
    salience: float = 0.0
    score_breakdown: dict[str, float] = Field(default_factory=dict)


class MemoryRecord(BaseModel):
    memory_id: str = Field(default_factory=lambda: new_id("mem"))
    memory_type: str
    content: str
    created_at: datetime = Field(default_factory=utc_now)
    revised_at: datetime = Field(default_factory=utc_now)
    source: str
    provenance: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    causal_parents: list[str] = Field(default_factory=list)
    contradiction_links: list[str] = Field(default_factory=list)
    privacy_classification: str = "internal"
    retention_policy: str = "persistent"
    revision_history: list[dict[str, Any]] = Field(default_factory=list)
    identity_relevance: float = 0.0
    embedding_reference: str | None = None


class Belief(BaseModel):
    belief_id: str = Field(default_factory=lambda: new_id("belief"))
    proposition: str
    classification: EpistemicClass
    confidence: float
    evidence: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    falsification_conditions: list[str] = Field(default_factory=list)
    origin: str
    revision_history: list[dict[str, Any]] = Field(default_factory=list)


class CognitiveEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: new_id("evt"))
    cycle_id: str
    timestamp: datetime = Field(default_factory=utc_now)
    actor: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    input_refs: list[str] = Field(default_factory=list)
    output_refs: list[str] = Field(default_factory=list)
    workspace_state_ref: str | None = None
    memory_refs: list[str] = Field(default_factory=list)
    belief_refs: list[str] = Field(default_factory=list)
    action_refs: list[str] = Field(default_factory=list)
    confidence: float | None = None
    provenance: list[str] = Field(default_factory=list)
    schema_version: str = "1.0"
    previous_event_hash: str = "GENESIS"
    event_hash: str = ""
    signature: str = ""


class SelfModel(BaseModel):
    name: str = "AEON"
    origin: str = "Founder-originated research architecture"
    continuity_id: str = Field(default_factory=lambda: new_id("continuity"))
    created_at: datetime = Field(default_factory=utc_now)
    version: str = "alpha-0.1"
    restart_history: list[datetime] = Field(default_factory=list)
    model_migration_history: list[dict[str, Any]] = Field(default_factory=list)
    major_identity_events: list[dict[str, Any]] = Field(default_factory=list)
    lineage: list[str] = Field(default_factory=lambda: ["founder", "AEON Alpha"])
    boundaries: dict[str, Any] = Field(default_factory=dict)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    internal_state: dict[str, Any] = Field(default_factory=dict)
    active_beliefs: list[str] = Field(default_factory=list)
    active_goals: list[str] = Field(default_factory=list)
    unresolved_contradictions: list[str] = Field(default_factory=list)
    current_focus: str = "idle"


class MetacognitiveReport(BaseModel):
    predicted_success: float
    task_difficulty: float
    uncertainty_type: str
    evidence_sufficiency: float
    contradictions: list[str] = Field(default_factory=list)
    strategy: str
    control_signal: ControlSignal = ControlSignal.CONTINUE
    confidence: float
    falsification_conditions: list[str] = Field(default_factory=list)


class CycleResult(BaseModel):
    cycle_id: str
    input_text: str
    response: str
    candidates: list[Candidate]
    workspace: list[Candidate]
    memories: list[MemoryRecord]
    metacognition: MetacognitiveReport
    belief_proposal: Belief | None = None
    ownership: dict[str, Any]
    provider_metadata: dict[str, Any]
    iterations: int
    created_at: datetime = Field(default_factory=utc_now)
