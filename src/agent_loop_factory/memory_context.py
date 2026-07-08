from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .memory_registry import SECRET_MARKERS

MAX_MEMORY_FILE_BYTES = 25 * 1024
MAX_TOTAL_MEMORY_BYTES = 50 * 1024


@dataclass(frozen=True)
class MemoryFile:
    path: str
    content: str
    size_bytes: int


@dataclass(frozen=True)
class MemoryContext:
    files: list[MemoryFile]
    total_bytes: int

    @property
    def included(self) -> bool:
        return bool(self.files)

    @property
    def paths(self) -> list[str]:
        return [file.path for file in self.files]


def load_memory_context(repo_root: Path, paths: list[Path] | None) -> MemoryContext | None:
    if not paths:
        return None

    repo_root = repo_root.resolve()
    memory_dir = (repo_root / "memory").resolve()
    deprecated_dir = (memory_dir / "deprecated").resolve()
    seen: set[Path] = set()
    files: list[MemoryFile] = []
    total = 0

    for raw_path in paths:
        path = (repo_root / raw_path).resolve() if not raw_path.is_absolute() else raw_path.resolve()
        if path in seen:
            raise ValueError(f"duplicate memory file: {_display_path(repo_root, path)}")
        seen.add(path)
        if not path.exists():
            raise ValueError(f"memory file does not exist: {raw_path}")
        if not path.is_file():
            raise ValueError(f"memory path is not a file: {_display_path(repo_root, path)}")
        if not _inside(path, memory_dir):
            raise ValueError(f"memory file must be inside memory/: {_display_path(repo_root, path)}")
        if _inside(path, deprecated_dir):
            raise ValueError(f"memory file is deprecated: {_display_path(repo_root, path)}")
        if path.suffix != ".md":
            raise ValueError(f"memory file must use .md extension: {_display_path(repo_root, path)}")

        size = path.stat().st_size
        if size > MAX_MEMORY_FILE_BYTES:
            raise ValueError(f"memory file too large: {_display_path(repo_root, path)} ({size} bytes)")
        total += size
        if total > MAX_TOTAL_MEMORY_BYTES:
            raise ValueError(f"total memory context too large: {total} bytes")

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"memory file is not valid UTF-8: {_display_path(repo_root, path)}") from exc
        for marker in SECRET_MARKERS:
            if marker in content:
                raise ValueError(f"secret-like marker in {_display_path(repo_root, path)}: {marker}")
        files.append(MemoryFile(_display_path(repo_root, path), content, size))

    return MemoryContext(files, total)


def write_memory_context(run_dir: Path, run_id: str, memory: MemoryContext | None) -> dict[str, object] | None:
    if not memory or not memory.included:
        return None
    data = {
        "included": True,
        "files": memory.paths,
        "total_bytes": memory.total_bytes,
        "validation_ok": True,
        "automatic_selection": False,
        "automatic_retrieval": False,
        "no_files_modified": True,
    }
    (run_dir / "memory_context.json").write_text(json.dumps(data, indent=2) + "\n")
    (run_dir / "memory_context.md").write_text(build_memory_context_markdown(memory))
    return {
        **data,
        "memory_context_path": f".agent/runs/{run_id}/memory_context.md",
        "memory_context_json_path": f".agent/runs/{run_id}/memory_context.json",
    }


def build_memory_context_markdown(memory: MemoryContext) -> str:
    files = "\n".join(f"* {path}" for path in memory.paths)
    contents = "\n\n".join(f"### {file.path}\n\n{file.content}" for file in memory.files)
    return f"""# Memory Context

## Status

* included: true
* automatic_selection: false
* automatic_retrieval: false
* no_files_modified: true

## Included Files

{files}

## Contents

{contents}

## Notes

* Memory files were explicitly selected by the human.
* The loop did not search, rank, or auto-select memory.
* Memory files were not modified.
"""


def _inside(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def _display_path(repo_root: Path, path: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return str(path)
