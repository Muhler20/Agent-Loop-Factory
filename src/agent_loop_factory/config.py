from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


NODE_GATES = ["npm test", "npm run lint", "npm run typecheck"]
PYTHON_GATES = ["pytest", "ruff check .", "mypy ."]


@dataclass
class Config:
    target_repo_path: str = "."
    worktree_base_path: str = "../agent-worktrees"
    max_iterations: int = 3
    max_changed_files: int = 8
    max_diff_lines: int = 500
    allowed_commands: list[str] = field(default_factory=lambda: NODE_GATES + PYTHON_GATES)
    gates: list[str] = field(default_factory=lambda: ["auto"])
    implementer: str = "none"
    codex_command: str = "codex"
    codex_exec_args: list[str] = field(default_factory=list)
    human_required_paths: list[str] = field(
        default_factory=lambda: [
            "auth/",
            "billing/",
            "payments/",
            "migrations/",
            "infra/",
            ".github/",
            "Dockerfile",
            "docker-compose.yml",
        ]
    )
    output_mode: str = "draft_pr_only"
    auto_merge: bool = False
    auto_deploy: bool = False


def load_config(config_path: Path) -> Config:
    data = _parse_simple_yaml(config_path.read_text() if config_path.exists() else "")
    config = Config(**{k: v for k, v in data.items() if k in Config.__dataclass_fields__})
    target = (config_path.parent.parent / config.target_repo_path).resolve()
    if not config.gates or config.gates == ["auto"]:
        config.gates = detect_gates(target)
    return config


def detect_gates(repo_path: Path) -> list[str]:
    if (repo_path / "package.json").exists():
        return NODE_GATES.copy()
    if any((repo_path / name).exists() for name in ("pyproject.toml", "setup.py", "requirements.txt")):
        return PYTHON_GATES.copy()
    return []


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: str | None = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line:
            continue
        if line.startswith("  - "):
            if current_key is None:
                raise ValueError(f"List item without key: {raw}")
            data.setdefault(current_key, []).append(_scalar(line[4:]))
            continue
        if ":" not in line:
            raise ValueError(f"Unsupported config line: {raw}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        current_key = key
        data[key] = [] if value == "" else _scalar(value)
    return data


def _scalar(value: str) -> Any:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value == "[]":
        return []
    if value.isdigit():
        return int(value)
    return value
