from __future__ import annotations

import uuid
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


TOOL_NAMES = frozenset({
    "search_web", "read_url", "list_files", "read_file", "write_file", "replace_text",
    "run_check", "inspect_site", "browser", "create_site", "finish",
})


def deadline_minutes_from_brief(brief: str) -> int | None:
    match = re.search(r"\b(?:within|in|deadline\s*:?)\s*(\d{1,4})\s*(minutes?|mins?|hours?|hrs?)\b", brief, re.IGNORECASE)
    if not match:
        return None
    amount = int(match.group(1)) * (60 if match.group(2).lower().startswith(("hour", "hr")) else 1)
    return amount if 1 <= amount <= 24 * 60 else None


@dataclass(frozen=True, slots=True)
class ActionGrant:
    """Explicit authority for effects outside public reading and the task workspace."""

    browser_write_domains: tuple[str, ...] = ()
    external_actions: tuple[str, ...] = ()
    recipients: tuple[str, ...] = ()
    max_spend: float = 0.0
    currency: str = "USD"

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "ActionGrant":
        value = value or {}
        allowed = {"publish", "message", "spend", "delete", "browser_write"}
        actions = tuple(sorted({str(item).strip().lower() for item in value.get("external_actions", [])}))
        if not set(actions) <= allowed:
            raise ValueError("Unknown external action in grant.")
        domains = tuple(sorted({str(item).strip().lower() for item in value.get("browser_write_domains", [])}))
        if any(not domain or "/" in domain or ":" in domain for domain in domains):
            raise ValueError("Grant domains must be hostnames.")
        ceiling = float(value.get("max_spend", 0))
        if ceiling < 0:
            raise ValueError("max_spend must be non-negative.")
        return cls(
            browser_write_domains=domains,
            external_actions=actions,
            recipients=tuple(str(item).strip() for item in value.get("recipients", [])),
            max_spend=ceiling,
            currency=str(value.get("currency", "USD")).upper(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TaskSpec:
    brief: str
    workspace: str
    task_id: str = field(default_factory=lambda: "task-" + uuid.uuid4().hex[:12])
    deadline_minutes: int = 90
    max_model_tokens: int = 50_000
    max_steps: int = 32
    max_revisions: int = 3
    grant: ActionGrant = field(default_factory=ActionGrant)

    def __post_init__(self) -> None:
        if not self.brief.strip():
            raise ValueError("Task brief cannot be empty.")
        if not self.task_id.startswith("task-") or not self.task_id[5:].replace("-", "").isalnum():
            raise ValueError("Invalid task id.")
        if not 1 <= self.deadline_minutes <= 24 * 60:
            raise ValueError("deadline_minutes must be 1..1440.")
        if not 100 <= self.max_model_tokens <= 1_000_000:
            raise ValueError("max_model_tokens must be 100..1000000.")
        if not 1 <= self.max_steps <= 200 or not 0 <= self.max_revisions <= 20:
            raise ValueError("Invalid step or revision limit.")
        object.__setattr__(self, "workspace", str(Path(self.workspace).resolve()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TaskSpec":
        data = dict(value)
        data["grant"] = ActionGrant.from_dict(data.get("grant"))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class Subgoal:
    id: str
    outcome: str
    success_check: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WorkOrder:
    outcome: str
    task_type: str
    audience: str
    deliverables: tuple[str, ...]
    hard_requirements: tuple[str, ...]
    flexible_tactics: tuple[str, ...]
    assumptions: tuple[str, ...]
    subgoals: tuple[Subgoal, ...]
    options: tuple[str, ...]
    chosen_approach: str
    success_checks: tuple[str, ...]
    deadline_minutes: int

    @classmethod
    def from_model(cls, value: dict[str, Any], brief: str, deadline_minutes: int = 90) -> "WorkOrder":
        def items(key: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
            raw = value.get(key, default)
            if not isinstance(raw, (list, tuple)):
                return default
            return tuple(str(item).strip()[:400] for item in raw if str(item).strip())[:12]

        task_type = str(value.get("task_type", "general")).strip().lower()
        if task_type not in {"research", "website", "code", "browser_file", "general"}:
            task_type = "general"
        if task_type in {"research", "browser_file"} and re.search(r"\bno (?:web )?research\b", brief, re.IGNORECASE):
            task_type = "general"
        allowed_suffixes = {".html", ".css", ".js", ".mjs", ".md", ".txt", ".csv", ".json", ".py", ".ts", ".tsx", ".jsx"}
        deliverables: list[str] = []
        for item in items("deliverables"):
            # Models sometimes append explanatory prose to a filename. It is
            # useful in the plan, but cannot be matched to an output artifact.
            name = re.sub(r"\s+\([^()]*\)\s*$", "", item).strip()
            if Path(name).suffix.lower() in allowed_suffixes and name not in deliverables:
                deliverables.append(name)
        if task_type == "research" and len(deliverables) > 1 and not re.search(
            r"\b(?:source (?:note|list|file)|references? (?:list|file)|bibliography)\b", brief, re.IGNORECASE
        ):
            main = next((name for name in deliverables if Path(name).suffix.lower() == ".md"), None)
            if main:
                deliverables = [name for name in deliverables if name == main or not re.search(r"(?:source|reference|citation)", Path(name).stem, re.IGNORECASE)]
        if len(deliverables) > 1:
            requested_check_file = bool(re.search(r"\b(?:verification|test|validation) (?:report|plan|cases?)\b", brief, re.IGNORECASE))
            deliverables = [name for name in deliverables if not re.search(r"(?:verification|test|validation)[_-]?(?:report|plan|cases?)", Path(name).stem, re.IGNORECASE) or requested_check_file or Path(name).name.casefold() in brief.casefold()]
        if task_type in {"website", "code"} and "index.html" in deliverables and not any(
            Path(name).suffix.lower() in {".py", ".ts", ".tsx", ".jsx", ".mjs"} for name in deliverables
        ) and not re.search(
            r"\b(?:separate files|separate (?:css|javascript|js)|(?:styles?\.css|script\.js|readme\.md))\b", brief, re.IGNORECASE
        ):
            # A broad page or browser utility needs one portable deliverable. Extra files
            # remain available as tactics, but are not invented acceptance gates.
            deliverables = ["index.html", *[name for name in deliverables if Path(name).suffix.lower() in {".json", ".csv"} or Path(name).suffix.lower() in {".md", ".txt"} and re.search(r"\b(?:source note|uncertainty note|usage guide|readme)\b", brief, re.IGNORECASE)]]
        if not deliverables:
            if task_type == "website" or task_type == "code" and re.search(r"\b(?:web|site|page|html|browser|calculator|converter)\b", brief, re.IGNORECASE):
                deliverables = ["index.html"]
            elif task_type == "code":
                deliverables = ["answer.py"]
            else:
                deliverables = ["answer.md"]
        raw_subgoals = value.get("subgoals", [])
        if not isinstance(raw_subgoals, (list, tuple)):
            raw_subgoals = []
        subgoals = []
        for index, raw in enumerate(raw_subgoals[:12], start=1):
            if isinstance(raw, dict):
                outcome = str(raw.get("outcome") or raw.get("description") or "").strip()[:400]
                check = str(raw.get("success_check") or raw.get("check") or outcome).strip()[:400]
            else:
                outcome = str(raw).strip()[:400]
                check = outcome
            if outcome:
                subgoals.append(Subgoal(f"S{index}", outcome, check))
        if not subgoals:
            subgoals = [
                Subgoal("S1", "Find relevant evidence", "Relevant evidence inspected"),
                Subgoal("S2", "Produce the requested deliverable", "Deliverable exists"),
                Subgoal("S3", "Verify the result", "Acceptance checks pass"),
            ]
        return cls(
            outcome=str(value.get("outcome") or brief).strip()[:1000],
            task_type=task_type,
            audience=str(value.get("audience") or "the task owner").strip()[:300],
            deliverables=tuple(deliverables),
            hard_requirements=items("hard_requirements"),
            flexible_tactics=items("flexible_tactics"),
            assumptions=items("assumptions"),
            subgoals=tuple(subgoals),
            options=items("options"),
            chosen_approach=str(value.get("chosen_approach") or "Research, create, and verify").strip()[:500],
            success_checks=items("success_checks") or ("Artifact exists and matches the brief",),
            deadline_minutes=deadline_minutes,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ToolAction:
    name: str
    args: dict[str, Any]
    decision_summary: str
    prediction: str = ""
    initiative: str = ""

    @classmethod
    def from_model(cls, value: dict[str, Any]) -> "ToolAction":
        name = str(value.get("tool", "")).strip()
        if name not in TOOL_NAMES:
            raise ValueError("Model selected an unknown tool.")
        args = value.get("args", {})
        if not isinstance(args, dict):
            raise ValueError("Tool arguments must be an object.")
        return cls(
            name=name, args=args,
            decision_summary=str(value.get("decision_summary", ""))[:400],
            prediction=str(value.get("prediction", ""))[:300],
            initiative=str(value.get("initiative", ""))[:300],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    url: str
    excerpt: str
    retrieved_at: str
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class VerificationFinding:
    severity: str
    artifact: str
    issue: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Artifact:
    path: str
    kind: str
    verified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
