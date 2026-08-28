from __future__ import annotations

import threading
import uuid
from pathlib import Path

from .audit import AuditLog
from .memory import MemoryStore
from .models import ArtifactKind, Candidate, CandidateStatus, Evaluation
from .skills import SkillRegistry
from .storage import atomic_write_json, file_lock, iso_now, read_json


class SelfImprovementEngine:
    """Candidate → evaluation → approval → promotion → rollback pipeline."""

    def __init__(
        self,
        project_root: Path,
        *,
        require_approval: bool = True,
        minimum_score: float = 0.60,
        minimum_improvement: float = 0.05,
    ):
        self.project_root = Path(project_root)
        self.root = self.project_root / ".codebee" / "improvement"
        self.root.mkdir(parents=True, exist_ok=True)
        self.require_approval = require_approval
        self.minimum_score = minimum_score
        self.minimum_improvement = minimum_improvement
        self.memory = MemoryStore(self.root)
        self.skills = SkillRegistry(self.root)
        self.audit = AuditLog(self.root / "audit.jsonl")
        self.candidates_path = self.root / "candidates.json"
        self.candidates_lock_path = self.root / "candidates.lock"
        self._lock = threading.RLock()

    def _load(self) -> dict[str, Candidate]:
        return {
            item_id: Candidate.from_dict(value)
            for item_id, value in read_json(self.candidates_path, {}).items()
        }

    def _save(self, candidates: dict[str, Candidate]) -> None:
        atomic_write_json(self.candidates_path, {key: value.to_dict() for key, value in candidates.items()})

    def _propose(
        self,
        kind: ArtifactKind,
        payload: dict,
        *,
        rationale: str,
        provenance: str,
        actor: str,
    ) -> Candidate:
        if not rationale.strip() or not provenance.strip():
            raise ValueError("Candidates require rationale and provenance.")
        candidate = Candidate(uuid.uuid4().hex, kind, payload, rationale.strip(), provenance.strip())
        with self._lock:
            with file_lock(self.candidates_lock_path):
                candidates = self._load()
                candidates[candidate.id] = candidate
                self._save(candidates)
            self.audit.append("candidate.proposed", actor=actor, details={"id": candidate.id, "kind": kind.value})
        return candidate

    def propose_memory(
        self,
        *,
        namespace: str,
        content: str,
        rationale: str,
        provenance: str,
        actor: str = "agent",
    ) -> Candidate:
        return self._propose(
            ArtifactKind.MEMORY,
            {"namespace": namespace, "content": content},
            rationale=rationale,
            provenance=provenance,
            actor=actor,
        )

    def propose_skill(
        self,
        *,
        name: str,
        description: str,
        instructions: str,
        rationale: str,
        provenance: str,
        related_skills: list[str] | None = None,
        actor: str = "agent",
    ) -> Candidate:
        return self._propose(
            ArtifactKind.SKILL,
            {
                "name": name,
                "description": description,
                "instructions": instructions,
                "related_skills": related_skills or [],
            },
            rationale=rationale,
            provenance=provenance,
            actor=actor,
        )

    def get_candidate(self, candidate_id: str) -> Candidate:
        try:
            return self._load()[candidate_id]
        except KeyError as error:
            raise KeyError(f"Unknown candidate '{candidate_id}'.") from error

    def record_evaluation(self, candidate_id: str, evaluation: Evaluation, *, actor: str = "evaluator") -> Candidate:
        with self._lock:
            with file_lock(self.candidates_lock_path):
                candidates = self._load()
                candidate = candidates[candidate_id]
                if candidate.status not in {CandidateStatus.PROPOSED, CandidateStatus.EVALUATED}:
                    raise ValueError(f"Cannot evaluate candidate in state '{candidate.status.value}'.")
                candidate.evaluation = evaluation
                candidate.status = CandidateStatus.EVALUATED
                candidate.updated_at = iso_now()
                self._save(candidates)
            self.audit.append(
                "candidate.evaluated",
                actor=actor,
                details={
                    "id": candidate_id,
                    "baseline": evaluation.baseline_score,
                    "candidate": evaluation.candidate_score,
                    "tests_passed": evaluation.tests_passed,
                    "security_passed": evaluation.security_passed,
                },
            )
            return candidate

    def approve(self, candidate_id: str, *, actor: str) -> Candidate:
        with self._lock:
            with file_lock(self.candidates_lock_path):
                candidates = self._load()
                candidate = candidates[candidate_id]
                if candidate.status != CandidateStatus.EVALUATED or candidate.evaluation is None:
                    raise ValueError("Candidate must be evaluated before approval.")
                if not candidate.evaluation.qualifies(
                    minimum_score=self.minimum_score,
                    minimum_improvement=self.minimum_improvement,
                ):
                    raise ValueError("Candidate does not meet evaluation or security thresholds.")
                candidate.status = CandidateStatus.APPROVED
                candidate.approved_by = actor
                candidate.updated_at = iso_now()
                self._save(candidates)
            self.audit.append("candidate.approved", actor=actor, details={"id": candidate_id})
            return candidate

    def promote(self, candidate_id: str, *, actor: str = "agent") -> Candidate:
        with self._lock:
            with file_lock(self.candidates_lock_path):
                candidates = self._load()
                candidate = candidates[candidate_id]
                retrying = candidate.status == CandidateStatus.PROMOTING
                allowed = candidate.status == CandidateStatus.APPROVED or retrying
                if not self.require_approval and candidate.status == CandidateStatus.EVALUATED and candidate.evaluation:
                    allowed = candidate.evaluation.qualifies(
                        minimum_score=self.minimum_score,
                        minimum_improvement=self.minimum_improvement,
                    )
                if not allowed:
                    raise PermissionError("Candidate requires a passing evaluation and configured approval before promotion.")

                if not retrying:
                    if candidate.kind == ArtifactKind.SKILL:
                        previous = self.skills.read(candidate.payload["name"])
                        candidate.previous_version = previous.version if previous else None
                    candidate.status = CandidateStatus.PROMOTING
                    candidate.updated_at = iso_now()
                    self._save(candidates)
                    self.audit.append(
                        "candidate.promotion_started",
                        actor=actor,
                        details={"id": candidate_id, "previous_version": candidate.previous_version},
                    )

                artifact_provenance = f"candidate:{candidate.id}|{candidate.provenance}"

                if candidate.kind == ArtifactKind.MEMORY:
                    entry = self.memory.add(
                        candidate.payload["namespace"],
                        candidate.payload["content"],
                        provenance=artifact_provenance,
                    )
                    candidate.artifact_ref = entry.id
                else:
                    skill, _ = self.skills.promote(
                        candidate.payload["name"],
                        candidate.payload["description"],
                        candidate.payload["instructions"],
                        provenance=artifact_provenance,
                        related_skills=candidate.payload.get("related_skills", []),
                    )
                    candidate.artifact_ref = skill.name

                candidate.status = CandidateStatus.PROMOTED
                candidate.updated_at = iso_now()
                self._save(candidates)
            self.audit.append(
                "candidate.promoted",
                actor=actor,
                details={"id": candidate_id, "artifact_ref": candidate.artifact_ref},
            )
            return candidate

    def rollback(self, candidate_id: str, *, actor: str) -> Candidate:
        with self._lock:
            with file_lock(self.candidates_lock_path):
                candidates = self._load()
                candidate = candidates[candidate_id]
                if candidate.status != CandidateStatus.PROMOTED or not candidate.artifact_ref:
                    raise ValueError("Only promoted candidates can be rolled back.")
                if candidate.kind == ArtifactKind.MEMORY:
                    self.memory.archive(candidate.artifact_ref)
                elif candidate.previous_version is None:
                    self.skills.archive(candidate.artifact_ref)
                else:
                    self.skills.restore(
                        candidate.artifact_ref,
                        candidate.previous_version,
                        provenance=f"rollback:{candidate.id}",
                    )
                candidate.status = CandidateStatus.ROLLED_BACK
                candidate.updated_at = iso_now()
                self._save(candidates)
            self.audit.append("candidate.rolled_back", actor=actor, details={"id": candidate_id})
            return candidate
