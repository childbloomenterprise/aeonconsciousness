"""Controlled, Hermes-derived self-improvement primitives for Codebee."""

from .engine import SelfImprovementEngine
from .models import ArtifactKind, Candidate, CandidateStatus, Evaluation

__all__ = [
    "ArtifactKind",
    "Candidate",
    "CandidateStatus",
    "Evaluation",
    "SelfImprovementEngine",
]

__version__ = "0.1.0"
