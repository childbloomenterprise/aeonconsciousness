from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .engine import SelfImprovementEngine
from .storage import parse_time


@dataclass(frozen=True, slots=True)
class CuratorAction:
    action: str
    target: str
    reason: str


@dataclass(slots=True)
class CuratorReport:
    generated_at: str
    dry_run: bool
    actions: list[CuratorAction] = field(default_factory=list)


class Curator:
    """Conservative curator: review first; mutation requires explicit approval."""

    def __init__(self, engine: SelfImprovementEngine):
        self.engine = engine

    def review(self, *, stale_after_days: int = 90, dry_run: bool = True) -> CuratorReport:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=stale_after_days)
        actions: list[CuratorAction] = []

        for skill in self.engine.skills.list():
            last_used = parse_time(skill.last_used_at)
            if last_used and last_used < cutoff and not skill.pinned:
                actions.append(CuratorAction("archive_skill", skill.name, f"unused for {stale_after_days}+ days"))

        seen: dict[tuple[str, str], str] = {}
        for entry in self.engine.memory.list():
            key = (entry.namespace, " ".join(entry.content.lower().split()))
            if key in seen:
                actions.append(CuratorAction("archive_memory", entry.id, f"duplicate of {seen[key]}"))
            else:
                seen[key] = entry.id

        report = CuratorReport(now.isoformat(), dry_run, actions)
        self.engine.audit.append(
            "curator.reviewed",
            actor="curator",
            details={"dry_run": dry_run, "actions": len(actions)},
        )
        return report

    def apply(self, report: CuratorReport, *, actor: str, approved: bool = False) -> None:
        if not approved:
            raise PermissionError("Curator mutations require explicit approval.")
        for action in report.actions:
            if action.action == "archive_skill":
                self.engine.skills.archive(action.target)
            elif action.action == "archive_memory":
                self.engine.memory.archive(action.target)
            self.engine.audit.append(
                "curator.applied",
                actor=actor,
                details={"action": action.action, "target": action.target, "reason": action.reason},
            )
