from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from .storage import atomic_write_json, atomic_write_text, file_lock, iso_now, read_json


@dataclass(slots=True)
class Skill:
    name: str
    description: str
    instructions: str
    version: int
    provenance: str
    created_at: str
    updated_at: str
    last_used_at: str
    pinned: bool = False
    state: str = "active"
    related_skills: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: dict) -> "Skill":
        return cls(**value)


class SkillRegistry:
    VALID_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

    def __init__(self, root: Path):
        self.root = Path(root)
        self.skills_dir = self.root / "skills"
        self.history_dir = self.root / "skill-history"
        self.index_path = self.root / "skills.json"
        self.lock_path = self.root / "skills.lock"

    def _load(self) -> dict[str, Skill]:
        return {
            name: Skill.from_dict(value)
            for name, value in read_json(self.index_path, {}).items()
        }

    def _save(self, skills: dict[str, Skill]) -> None:
        atomic_write_json(self.index_path, {name: asdict(skill) for name, skill in skills.items()})

    @classmethod
    def _validate(cls, name: str, description: str, instructions: str) -> None:
        if not cls.VALID_NAME.fullmatch(name):
            raise ValueError("Skill name must be lowercase and contain only letters, digits, '.', '_' or '-'.")
        if not description.strip() or len(description) > 1024:
            raise ValueError("Skill description must contain 1-1024 characters.")
        if not instructions.strip() or len(instructions) > 100_000:
            raise ValueError("Skill instructions must contain 1-100000 characters.")

    @staticmethod
    def _markdown(skill: Skill) -> str:
        related = ", ".join(skill.related_skills)
        return (
            "---\n"
            f"name: {skill.name}\n"
            f"description: {skill.description}\n"
            f"version: {skill.version}\n"
            f"provenance: {skill.provenance}\n"
            f"related_skills: [{related}]\n"
            "---\n\n"
            f"{skill.instructions.strip()}\n"
        )

    def read(self, name: str) -> Skill | None:
        skill = self._load().get(name)
        return skill if skill and skill.state == "active" else None

    def list(self, *, include_archived: bool = False) -> list[Skill]:
        values = self._load().values()
        return [skill for skill in values if include_archived or skill.state == "active"]

    def promote(
        self,
        name: str,
        description: str,
        instructions: str,
        *,
        provenance: str,
        related_skills: list[str] | None = None,
    ) -> tuple[Skill, Skill | None]:
        self._validate(name, description, instructions)
        with file_lock(self.lock_path):
            skills = self._load()
            previous = skills.get(name)
            normalized_related = list(related_skills or [])
            if (
                previous
                and previous.state == "active"
                and previous.description == description.strip()
                and previous.instructions == instructions.strip()
                and previous.provenance == provenance
                and previous.related_skills == normalized_related
            ):
                return previous, None
            if previous:
                history = self.history_dir / name / f"v{previous.version}.json"
                atomic_write_json(history, asdict(previous))
            now = iso_now()
            skill = Skill(
                name=name,
                description=description.strip(),
                instructions=instructions.strip(),
                version=(previous.version + 1) if previous else 1,
                provenance=provenance,
                created_at=previous.created_at if previous else now,
                updated_at=now,
                last_used_at=previous.last_used_at if previous else now,
                pinned=previous.pinned if previous else False,
                related_skills=normalized_related,
            )
            skills[name] = skill
            self._save(skills)
            atomic_write_text(self.skills_dir / name / "SKILL.md", self._markdown(skill))
            return skill, previous

    def restore(self, name: str, version: int, *, provenance: str) -> Skill:
        data = read_json(self.history_dir / name / f"v{version}.json", None)
        if data is None:
            raise KeyError(f"No archived version {version} for skill '{name}'.")
        old = Skill.from_dict(data)
        restored, _ = self.promote(
            old.name,
            old.description,
            old.instructions,
            provenance=provenance,
            related_skills=old.related_skills,
        )
        return restored

    def archive(self, name: str) -> Skill:
        with file_lock(self.lock_path):
            skills = self._load()
            skill = skills.get(name)
            if skill is None:
                raise KeyError(name)
            if skill.pinned:
                raise PermissionError(f"Pinned skill '{name}' cannot be archived.")
            atomic_write_json(self.history_dir / name / f"v{skill.version}.json", asdict(skill))
            skill.state = "archived"
            skill.updated_at = iso_now()
            self._save(skills)
            return skill

    def set_last_used(self, name: str, when: datetime) -> None:
        with file_lock(self.lock_path):
            skills = self._load()
            if name not in skills:
                raise KeyError(name)
            skills[name].last_used_at = when.isoformat()
            self._save(skills)
