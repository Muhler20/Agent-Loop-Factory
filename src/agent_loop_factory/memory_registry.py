from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MAX_MEMORY_FILE_BYTES = 100 * 1024
REQUIRED_PATHS = (
    "INDEX.md",
    "MEMORY_TEMPLATE.md",
    "failure-patterns",
    "prompt-guidance",
    "reviewer-guidance",
    "deprecated",
)
SECRET_MARKERS = (
    "BEGIN PRIVATE KEY",
    "AWS_SECRET_ACCESS_KEY",
    "OPENAI_API_KEY",
    "GITHUB_TOKEN",
    "password=",
    "secret=",
)


@dataclass(frozen=True)
class MemoryRegistryResult:
    ok: bool
    errors: list[str]


def validate_memory_registry(repo_root: Path, max_file_bytes: int = MAX_MEMORY_FILE_BYTES) -> MemoryRegistryResult:
    memory_dir = repo_root / "memory"
    errors: list[str] = []

    for relative in REQUIRED_PATHS:
        path = memory_dir / relative
        if relative.endswith(".md"):
            if not path.is_file():
                errors.append(f"missing file: memory/{relative}")
        elif not path.is_dir():
            errors.append(f"missing directory: memory/{relative}")

    if memory_dir.is_dir():
        for path in memory_dir.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(repo_root)
            size = path.stat().st_size
            if size > max_file_bytes:
                errors.append(f"file too large: {relative} ({size} bytes)")
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for marker in SECRET_MARKERS:
                if marker in text:
                    errors.append(f"secret-like marker in {relative}: {marker}")

    return MemoryRegistryResult(ok=not errors, errors=errors)
