from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

MAX_MEMORY_FILE_BYTES = 100 * 1024
ACTIVE_MEMORY_DIRS = {
    "failure-patterns": "failure-pattern",
    "prompt-guidance": "prompt-guidance",
    "reviewer-guidance": "reviewer-guidance",
}
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
REQUIRED_METADATA = ("status", "category", "source_run_id", "created", "last_reviewed", "confidence")
REQUIRED_SECTIONS = ("## Lesson", "## Evidence", "## When To Apply", "## When Not To Apply", "## Suggested Enforcement")
VALID_STATUS = {"active", "deprecated", "superseded"}
VALID_CONFIDENCE = {"low", "medium", "high"}


@dataclass(frozen=True)
class MemoryRegistryResult:
    ok: bool
    errors: list[str]
    warnings: list[str]


def validate_memory_registry(repo_root: Path, max_file_bytes: int = MAX_MEMORY_FILE_BYTES) -> MemoryRegistryResult:
    memory_dir = repo_root / "memory"
    errors: list[str] = []
    warnings: list[str] = []
    active_titles: dict[str, list[Path]] = {}
    deprecated_titles: dict[str, list[Path]] = {}
    active_texts_by_title: dict[str, list[tuple[Path, str]]] = {}

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
            file_errors, file_warnings = validate_memory_file_hygiene(repo_root, path, text)
            errors.extend(file_errors)
            warnings.extend(file_warnings)
            title = first_h1(text)
            if title and is_active_memory_file(repo_root, path):
                active_titles.setdefault(title, []).append(path)
                active_texts_by_title.setdefault(title, []).append((path, text.lower()))
            elif title and is_deprecated_memory_file(repo_root, path):
                deprecated_titles.setdefault(title, []).append(path)

    for title, paths in active_titles.items():
        if len(paths) > 1:
            warnings.append(f"duplicate active memory title: {title} ({', '.join(_display(repo_root, path) for path in paths)})")
        if title in deprecated_titles:
            warnings.append(f"active memory title also exists in deprecated memory: {title}")
        texts = active_texts_by_title.get(title, [])
        if any("never" in text for _, text in texts) and any("always" in text for _, text in texts):
            warnings.append(f"possible always/never conflict for active memory title: {title}")

    return MemoryRegistryResult(ok=not errors, errors=errors, warnings=warnings)


def validate_memory_file_hygiene(repo_root: Path, path: Path, text: str | None = None) -> tuple[list[str], list[str]]:
    if not is_active_memory_file(repo_root, path):
        return [], []
    if text is None:
        text = path.read_text(encoding="utf-8", errors="ignore")
    relative = _display(repo_root, path)
    errors: list[str] = []
    warnings: list[str] = []
    metadata = parse_metadata(text)

    for field in REQUIRED_METADATA:
        if not metadata.get(field):
            errors.append(f"missing metadata {field}: {relative}")

    status = metadata.get("status", "")
    if status and status not in VALID_STATUS:
        errors.append(f"invalid status in {relative}: {status}")
    if status == "deprecated":
        warnings.append(f"deprecated status outside memory/deprecated/: {relative}")
    if status == "superseded" and not metadata.get("superseded-by"):
        warnings.append(f"superseded memory missing superseded-by metadata: {relative}")

    expected_category = ACTIVE_MEMORY_DIRS[path.relative_to(repo_root / "memory").parts[0]]
    category = metadata.get("category", "")
    if category and category not in set(ACTIVE_MEMORY_DIRS.values()):
        errors.append(f"invalid category in {relative}: {category}")
    elif category and category != expected_category:
        errors.append(f"category mismatch in {relative}: expected {expected_category}, got {category}")

    confidence = metadata.get("confidence", "")
    if confidence and confidence not in VALID_CONFIDENCE:
        errors.append(f"invalid confidence in {relative}: {confidence}")

    for section in REQUIRED_SECTIONS:
        if not has_heading(text, section):
            errors.append(f"missing section {section}: {relative}")

    reviewed = metadata.get("last_reviewed", "")
    if reviewed:
        try:
            if (dt.date.today() - dt.date.fromisoformat(reviewed)).days > 180:
                warnings.append(f"last_reviewed older than 180 days: {relative}")
        except ValueError:
            warnings.append(f"last_reviewed is not YYYY-MM-DD: {relative}")

    return errors, warnings


def parse_metadata(text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in text.splitlines()[:30]:
        if line.startswith("## "):
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        if key:
            metadata[key] = value.strip()
    return metadata


def first_h1(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# ") and not line.startswith("## "):
            return line[2:].strip()
    return None


def has_heading(text: str, heading: str) -> bool:
    return any(line.strip() == heading for line in text.splitlines())


def is_active_memory_file(repo_root: Path, path: Path) -> bool:
    try:
        parts = path.relative_to(repo_root / "memory").parts
    except ValueError:
        return False
    return len(parts) >= 2 and parts[0] in ACTIVE_MEMORY_DIRS and path.suffix == ".md" and path.name != ".gitkeep"


def is_deprecated_memory_file(repo_root: Path, path: Path) -> bool:
    try:
        parts = path.relative_to(repo_root / "memory").parts
    except ValueError:
        return False
    return len(parts) >= 2 and parts[0] == "deprecated" and path.suffix == ".md"


def _display(repo_root: Path, path: Path) -> str:
    return path.relative_to(repo_root).as_posix()
