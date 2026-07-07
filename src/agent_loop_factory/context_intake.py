from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


MAX_CONTEXT_BYTES = 50_000


@dataclass(frozen=True)
class ContextData:
    issue_file_path: str | None = None
    issue_body: str | None = None
    issue_size_bytes: int | None = None
    ci_log_file_path: str | None = None
    ci_log_body: str | None = None
    ci_log_size_bytes: int | None = None


def load_context(issue_file: Path | None = None, ci_log_file: Path | None = None) -> ContextData:
    issue_path, issue_body, issue_size = _load_optional(issue_file, "issue file")
    ci_path, ci_body, ci_size = _load_optional(ci_log_file, "CI log file")
    return ContextData(issue_path, issue_body, issue_size, ci_path, ci_body, ci_size)


def _load_optional(path: Path | None, label: str) -> tuple[str | None, str | None, int | None]:
    if path is None:
        return None, None, None
    path = path.expanduser()
    if not path.exists():
        raise ValueError(f"{label} does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"{label} is not a file: {path}")
    size = path.stat().st_size
    if size == 0:
        raise ValueError(f"{label} is empty: {path}")
    if size > MAX_CONTEXT_BYTES:
        raise ValueError(f"{label} is too large: {path} ({size} bytes > {MAX_CONTEXT_BYTES} bytes)")
    try:
        body = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} is not valid UTF-8: {path}") from exc
    return str(path), body, size
