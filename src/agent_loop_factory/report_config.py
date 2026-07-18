from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .github_context import parse_repo

MAX_CONFIG_BYTES = 25 * 1024
VALID_CADENCES = {"manual", "daily", "weekly", "monthly"}
VALID_REPORT_TYPES = {"memory_hygiene", "github_ci", "stale_runs"}
SAFETY_FIELDS = (
    "report_only",
    "no_code_changes",
    "no_git_writes",
    "no_github_writes",
    "no_codex_implementer",
    "requires_human_action",
)
SECRET_MARKERS = (
    "BEGIN PRIVATE KEY",
    "AWS_SECRET_ACCESS_KEY",
    "OPENAI_API_KEY",
    "GITHUB_TOKEN",
    "password=",
    "secret=",
)
NAME_RE = re.compile(r"^[a-z0-9_-]+$")
TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
TRIGGER_HINT_FIELDS = {"local_time", "utc_time", "weekday", "day_of_month"}


@dataclass(frozen=True)
class ReportConfig:
    path: Path
    name: str
    description: str
    cadence: str
    enabled: bool
    report_types: tuple[str, ...]
    github_repo: str | None
    ci_runs_limit: int
    stale_runs_max: int
    safety: dict[str, bool]
    trigger_hints: dict[str, str | int]


def load_report_config(repo_root: Path, config_path: Path | str) -> ReportConfig:
    root = repo_root.resolve()
    path = Path(config_path)
    path = (root / path).resolve() if not path.is_absolute() else path.resolve()
    config_dir = (root / "report_configs").resolve()
    if not path.exists():
        raise ValueError(f"report config does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"report config is not a file: {path}")
    if not path.is_relative_to(config_dir):
        raise ValueError("report config must resolve inside report_configs/")
    if path.suffix != ".json":
        raise ValueError("report config extension must be .json")
    size = path.stat().st_size
    if size > MAX_CONFIG_BYTES:
        raise ValueError(f"report config exceeds {MAX_CONFIG_BYTES} bytes")
    try:
        raw = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("report config must be valid UTF-8") from exc
    for marker in SECRET_MARKERS:
        if marker.lower() in raw.lower():
            raise ValueError(f"secret-like string in report config: {marker}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid report config JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("report config must be a JSON object")

    name = data.get("name")
    if not isinstance(name, str) or not name or not NAME_RE.fullmatch(name):
        raise ValueError("name must contain only lowercase letters, numbers, hyphen, or underscore")
    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("description must be a non-empty string")
    cadence = data.get("cadence")
    if cadence not in VALID_CADENCES:
        raise ValueError("cadence must be manual, daily, weekly, or monthly")
    enabled = data.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean")
    report_types = data.get("report_types")
    if not isinstance(report_types, list) or not report_types:
        raise ValueError("report_types must be a non-empty list")
    if any(not isinstance(item, str) or item not in VALID_REPORT_TYPES for item in report_types):
        raise ValueError("report_types contains an unknown report type")
    if len(report_types) != len(set(report_types)):
        raise ValueError("report_types must not contain duplicates")

    github = data.get("github", {})
    stale = data.get("stale_runs", {})
    if not isinstance(github, dict) or not isinstance(stale, dict):
        raise ValueError("github and stale_runs must be JSON objects")
    repo = github.get("repo")
    if "github_ci" in report_types and not isinstance(repo, str):
        raise ValueError("github.repo is required when github_ci is selected")
    if repo is not None:
        if not isinstance(repo, str):
            raise ValueError("github.repo must be owner/repo")
        try:
            parse_repo(repo)
        except ValueError as exc:
            raise ValueError("github.repo must be exactly owner/repo") from exc
    ci_limit = github.get("ci_runs_limit", 5)
    max_runs = stale.get("max_runs", 25)
    if isinstance(ci_limit, bool) or not isinstance(ci_limit, int) or not 1 <= ci_limit <= 20:
        raise ValueError("github.ci_runs_limit must be an integer from 1 to 20")
    if isinstance(max_runs, bool) or not isinstance(max_runs, int) or not 1 <= max_runs <= 100:
        raise ValueError("stale_runs.max_runs must be an integer from 1 to 100")
    safety = data.get("safety")
    if not isinstance(safety, dict):
        raise ValueError("safety must be a JSON object")
    for field in SAFETY_FIELDS:
        if safety.get(field) is not True:
            raise ValueError(f"safety.{field} must exist and be true")

    trigger_hints = data.get("trigger_hints", {})
    if not isinstance(trigger_hints, dict):
        raise ValueError("trigger_hints must be a JSON object")
    unknown_hints = set(trigger_hints) - TRIGGER_HINT_FIELDS
    if unknown_hints:
        raise ValueError(f"unknown trigger_hints key: {sorted(unknown_hints)[0]}")
    for field in ("local_time", "utc_time"):
        value = trigger_hints.get(field)
        if value is not None and (not isinstance(value, str) or not TIME_RE.fullmatch(value)):
            raise ValueError(f"trigger_hints.{field} must use HH:MM 24-hour format")
    weekday = trigger_hints.get("weekday")
    if weekday is not None and (not isinstance(weekday, str) or weekday not in WEEKDAYS):
        raise ValueError("trigger_hints.weekday must be a lowercase weekday")
    day = trigger_hints.get("day_of_month")
    if day is not None and (isinstance(day, bool) or not isinstance(day, int) or not 1 <= day <= 28):
        raise ValueError("trigger_hints.day_of_month must be an integer from 1 to 28")

    return ReportConfig(path, name, description.strip(), cadence, enabled, tuple(report_types), repo, ci_limit, max_runs, {field: True for field in SAFETY_FIELDS}, trigger_hints)


validate_report_config = load_report_config
