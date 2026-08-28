from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .storage import iso_now


class ArtifactKind(str, Enum):
    MEMORY = "memory"
    SKILL = "skill"


class CandidateStatus(str, Enum):
    PROPOSED = "proposed"
    EVALUATED = "evaluated"
    APPROVED = "approved"
    PROMOTING = "promoting"
    REJECTED = "rejected"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"


@dataclass(slots=True)
class Evaluation:
    baseline_score: float
    candidate_score: float
    tests_passed: bool
    security_passed: bool
    evidence: list[str] = field(default_factory=list)
    evaluated_at: str = field(default_factory=iso_now)

    def __post_init__(self) -> None:
        if not 0.0 <= self.baseline_score <= 1.0:
            raise ValueError("baseline_score must be between 0 and 1.")
        if not 0.0 <= self.candidate_score <= 1.0:
            raise ValueError("candidate_score must be between 0 and 1.")

    @property
    def improvement(self) -> float:
        return self.candidate_score - self.baseline_score

    def qualifies(self, *, minimum_score: float, minimum_improvement: float) -> bool:
        return (
            self.tests_passed
            and self.security_passed
            and self.candidate_score >= minimum_score
            and self.improvement >= minimum_improvement
        )

    @classmethod
    def passing(cls, score: float, evidence: list[str]) -> "Evaluation":
        baseline = max(0.0, score - 0.1)
        return cls(baseline, score, True, True, evidence)


@dataclass(slots=True)
class Candidate:
    id: str
    kind: ArtifactKind
    payload: dict[str, Any]
    rationale: str
    provenance: str
    status: CandidateStatus = CandidateStatus.PROPOSED
    created_at: str = field(default_factory=iso_now)
    updated_at: str = field(default_factory=iso_now)
    evaluation: Evaluation | None = None
    approved_by: str | None = None
    artifact_ref: str | None = None
    previous_version: int | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["kind"] = self.kind.value
        value["status"] = self.status.value
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Candidate":
        copy = dict(value)
        copy["kind"] = ArtifactKind(copy["kind"])
        copy["status"] = CandidateStatus(copy["status"])
        if copy.get("evaluation"):
            copy["evaluation"] = Evaluation(**copy["evaluation"])
        return cls(**copy)
