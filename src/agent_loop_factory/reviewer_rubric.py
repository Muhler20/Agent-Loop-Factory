from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


MAX_BYTES = 25 * 1024
SECRET_MARKERS = (
    "BEGIN PRIVATE KEY",
    "AWS_SECRET_ACCESS_KEY",
    "OPENAI_API_KEY",
    "GITHUB_TOKEN",
    "password=",
    "secret=",
)
STATUSES = {"active", "deprecated"}
CATEGORIES = {"safety", "tests", "scope", "handoff", "general"}
HEADINGS = (
    "## Review Focus",
    "## Questions To Ask",
    "## Red Flags",
    "## Evidence To Cite",
    "## Suggested Human Actions",
    "## Non-Authority Reminder",
)


@dataclass(frozen=True)
class ReviewerRubric:
    source_path: str
    path: Path
    contents: str
    bytes: int


def load_reviewer_rubric(repo_root: Path, path: Path | str) -> ReviewerRubric:
    rubrics = load_reviewer_rubrics(repo_root, [path])
    return rubrics[0]


def load_reviewer_rubrics(repo_root: Path, paths: list[Path | str]) -> list[ReviewerRubric]:
    repo_root = repo_root.resolve()
    reviewers_dir = repo_root / "reviewers"
    resolved_seen: set[Path] = set()
    rubrics = []
    for raw_path in paths:
        path = (repo_root / raw_path).resolve() if not Path(raw_path).is_absolute() else Path(raw_path).resolve()
        if path in resolved_seen:
            raise ValueError(f"duplicate reviewer rubric path: {_source(repo_root, path)}")
        resolved_seen.add(path)
        rubrics.append(_load_one(repo_root, reviewers_dir, path))
    return rubrics


def _load_one(repo_root: Path, reviewers_dir: Path, path: Path) -> ReviewerRubric:
    source = _source(repo_root, path)
    if not path.exists():
        raise ValueError(f"reviewer rubric does not exist: {source}")
    if not path.is_file():
        raise ValueError(f"reviewer rubric is not a file: {source}")
    try:
        path.relative_to(reviewers_dir.resolve())
    except ValueError as exc:
        raise ValueError("reviewer rubric must be inside reviewers/") from exc
    if path.suffix != ".md":
        raise ValueError("reviewer rubric must use .md extension")
    if path.name in {"README.md", "RUBRIC_TEMPLATE.md"}:
        raise ValueError(f"{path.name} is not an includable reviewer rubric")
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise ValueError("reviewer rubric exceeds 25 KB")
    try:
        contents = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("reviewer rubric must be valid UTF-8") from exc
    for marker in SECRET_MARKERS:
        if marker in contents:
            raise ValueError(f"reviewer rubric contains secret-like marker: {marker}")
    metadata = _metadata(contents)
    _validate_metadata(metadata)
    for heading in HEADINGS:
        if heading not in contents:
            raise ValueError(f"reviewer rubric missing required heading: {heading}")
    return ReviewerRubric(source, path, contents, len(data))


def _metadata(contents: str) -> dict[str, str]:
    metadata = {}
    for line in contents.splitlines()[:20]:
        line = line.strip()
        if line.startswith("* "):
            line = line[2:].strip()
        if ":" in line:
            key, value = line.split(":", 1)
            if key.strip() in {"status", "category", "advisory_only"}:
                metadata[key.strip()] = value.strip()
    return metadata


def _validate_metadata(metadata: dict[str, str]) -> None:
    for key in ("status", "category", "advisory_only"):
        if key not in metadata:
            raise ValueError(f"reviewer rubric missing metadata: {key}")
    if metadata["status"] not in STATUSES:
        raise ValueError("reviewer rubric status must be active or deprecated")
    if metadata["status"] == "deprecated":
        raise ValueError("deprecated reviewer rubrics cannot be explicitly included")
    if metadata["category"] not in CATEGORIES:
        raise ValueError("reviewer rubric category is invalid")
    if metadata["advisory_only"] != "true":
        raise ValueError("reviewer rubric advisory_only must be true")


def _source(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)
