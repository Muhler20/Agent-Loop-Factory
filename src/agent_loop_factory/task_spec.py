from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class TaskSpec:
    task_title: str
    task_body: str
    task_file_path: str | None = None
    allowed_files: list[str] = field(default_factory=list)
    forbidden_files: list[str] = field(default_factory=list)


def load_task_spec(path: Path) -> TaskSpec:
    if not path.exists():
        raise ValueError(f"task file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"task file is not a file: {path}")
    return task_spec_from_body(path.read_text(), str(path))


def inline_task_spec(task: str) -> TaskSpec:
    return task_spec_from_body(f"# {task}\n\n{task}\n")


def task_spec_from_body(body: str, task_file_path: str | None = None) -> TaskSpec:
    if not body.strip():
        source = f": {task_file_path}" if task_file_path else ""
        raise ValueError(f"task spec is empty{source}")
    return TaskSpec(
        task_title=_title(body),
        task_body=body,
        task_file_path=task_file_path,
        allowed_files=_section_paths(body, "Allowed files") if task_file_path else [],
        forbidden_files=_section_paths(body, "Forbidden files") if task_file_path else [],
    )


def _title(body: str) -> str:
    first_line = None
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        first_line = first_line or stripped
        heading = re.match(r"^#{1,6}\s+(.+?)\s*#*$", stripped)
        if heading:
            return heading.group(1).strip()
    return first_line or ""


def _section_paths(body: str, section_name: str) -> list[str]:
    paths = []
    in_section = False
    for line in body.splitlines():
        stripped = line.strip()
        heading = re.match(r"^#{1,6}\s+(.+?)\s*#*$", stripped)
        if heading:
            in_section = heading.group(1).strip().casefold() == section_name.casefold()
            continue
        if not in_section or not stripped:
            continue
        bullet = re.match(r"^[-*]\s+(.+?)\s*$", stripped)
        if bullet:
            paths.append(_clean_path(bullet.group(1)))
    return paths


def _clean_path(path: str) -> str:
    path = path.strip()
    if len(path) >= 2 and path.startswith("`") and path.endswith("`"):
        path = path[1:-1].strip()
    return path.replace("\\", "/")
