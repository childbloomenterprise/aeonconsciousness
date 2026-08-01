from typing import Any

from pydantic import BaseModel, Field


class InputRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)


class ExperimentRequest(BaseModel):
    hypothesis: str
    configuration: str = "FULL_AEON"
    seed: int = 42
    ablations: list[str] = Field(default_factory=list)
    interventions: dict[str, Any] = Field(default_factory=dict)


class VIModeRequest(BaseModel):
    prompt: str
