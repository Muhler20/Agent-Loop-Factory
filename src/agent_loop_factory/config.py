from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


NODE_GATES = ["npm test", "npm run lint", "npm run typecheck"]
PYTHON_GATES = ["pytest", "ruff check .", "mypy ."]
GATE_FIELDS = {"name", "command", "required"}


class ConfigError(ValueError):
    pass


@dataclass
class Config:
    target_repo_path: str = "."
    worktree_base_path: str = "../agent-worktrees"
    max_iterations: int = 3
    max_changed_files: int = 8
    max_diff_lines: int = 500
    allowed_commands: list[str] = field(default_factory=lambda: NODE_GATES + PYTHON_GATES)
    gates: list[object] = field(default_factory=lambda: ["auto"])
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
    config.gates = normalize_gates(config.gates)
    return config


def detect_gates(repo_path: Path) -> list[str]:
    if (repo_path / "package.json").exists():
        return NODE_GATES.copy()
    if any((repo_path / name).exists() for name in ("pyproject.toml", "setup.py", "requirements.txt")):
        return PYTHON_GATES.copy()
    return []


def normalize_gates(gates: list[object]) -> list[dict[str, object]]:
    return [_normalize_gate(gate, index) for index, gate in enumerate(gates)]


def _normalize_gate(gate: object, index: int) -> dict[str, object]:
    if isinstance(gate, str):
        return {"name": gate, "command": gate, "required": True}
    if not isinstance(gate, dict):
        raise ValueError(f"Invalid gate at index {index}: expected string or object")
    extra_fields = sorted(set(gate) - GATE_FIELDS)
    if extra_fields:
        raise ValueError(f"Invalid gate at index {index}: unsupported field(s): {', '.join(extra_fields)}")
    command = gate.get("command")
    if command is None:
        raise ValueError(f"Invalid gate at index {index}: missing command")
    if not isinstance(command, str):
        raise ValueError(f"Invalid gate at index {index}: command must be a string")
    name = gate.get("name", command)
    if not isinstance(name, str):
        raise ValueError(f"Invalid gate at index {index}: name must be a string")
    required = gate.get("required", True)
    if type(required) is not bool:
        raise ValueError(f"Invalid gate at index {index}: required must be boolean")
    return {"name": name, "command": command, "required": required}


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: str | None = None
    current_list_item: dict[str, Any] | None = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line:
            continue
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)
        if stripped.startswith("- ") and indent != 2:
            raise ConfigError(f"List item has unsupported indentation: {raw}")
        if indent not in (0, 2, 4):
            raise ConfigError(f"Unsupported indentation in config line: {raw}")
        if line.startswith("  - "):
            if current_key is None:
                raise ConfigError(f"List item without key: {raw}")
            item = line[4:]
            if current_key == "gates" and _looks_like_mapping(item):
                key, value = item.split(":", 1)
                key = key.strip()
                if not key:
                    raise ConfigError(f"Malformed key/value line: {raw}")
                current_list_item = {key: _scalar(value.strip(), raw)}
                data.setdefault(current_key, []).append(current_list_item)
            else:
                current_list_item = None
                data.setdefault(current_key, []).append(_scalar(item, raw))
            continue
        if line.startswith("    "):
            if current_list_item is None:
                raise ConfigError(f"Nested field without list object: {raw}")
            item = line.strip()
            if ":" not in item:
                raise ConfigError(f"Malformed key/value line: {raw}")
            key, value = item.split(":", 1)
            key = key.strip()
            if not key:
                raise ConfigError(f"Malformed key/value line: {raw}")
            current_list_item[key] = _scalar(value.strip(), raw)
            continue
        if indent != 0:
            raise ConfigError(f"Unsupported indentation in config line: {raw}")
        if ":" not in line:
            raise ConfigError(f"Malformed key/value line: {raw}")
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise ConfigError(f"Malformed key/value line: {raw}")
        if key in data:
            raise ConfigError(f"Duplicate top-level key: {key}")
        value = value.strip()
        parsed_value = [] if value == "" else _scalar(value, raw)
        if isinstance(parsed_value, dict):
            raise ConfigError(f"Nested mappings are not supported here: {raw}")
        current_key = key
        current_list_item = None
        data[key] = parsed_value
    return data


def _looks_like_mapping(value: str) -> bool:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return False
    return ":" in value


def _scalar(value: str, raw: str = "") -> Any:
    value = value.strip()
    if value in ("|", ">"):
        raise ConfigError(f"Multiline block scalars are not supported: {raw}")
    if value.startswith("*") or any(token.startswith("&") and token != "&&" for token in value.split()):
        raise ConfigError(f"YAML anchors and aliases are not supported: {raw}")
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
