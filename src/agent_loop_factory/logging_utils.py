from __future__ import annotations

from pathlib import Path


def append_log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(path.read_text() + message if path.exists() else message)
