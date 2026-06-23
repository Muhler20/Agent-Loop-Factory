from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


_SLUG_RE = re.compile(r"[a-z0-9_-]+")


@dataclass(frozen=True)
class Skill:
    skill_name: str
    skill_body: str
    skill_file_path: str


def load_skill(repo_root: Path, skill_name: str) -> Skill:
    if not _SLUG_RE.fullmatch(skill_name):
        raise ValueError("skill name must use only lowercase letters, numbers, hyphens, and underscores")

    skill_file = repo_root / "skills" / skill_name / "SKILL.md"
    if not skill_file.exists():
        raise ValueError(f"skill file does not exist: {skill_file}")

    body = skill_file.read_text()
    if not body.strip():
        raise ValueError(f"skill file is empty: {skill_file}")

    return Skill(skill_name=skill_name, skill_body=body, skill_file_path=str(skill_file))
