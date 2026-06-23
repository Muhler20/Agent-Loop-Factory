from __future__ import annotations

import fnmatch
import json
import subprocess
from pathlib import Path

from .config import Config


SKIP_MARKERS = ("@unittest.skip", "pytest.mark.skip", "skipTest")
ASSERT_MARKERS = ("assert", "assertEqual", "assertTrue", "assertFalse", "assertRaises")


def run_verifier(config: Config, worktree_path: Path | None, run_dir: Path, gates: list[dict[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {
        "ok": True,
        "reasons": [],
        "warnings": [],
        "changed_files": [],
        "changed_file_count": 0,
        "diff_line_count": 0,
        "human_required_touched": [],
        "tests_weakened_or_deleted": False,
    }
    reasons = result["reasons"]

    if any(not gate.get("ok") for gate in gates):
        reasons.append("one or more gates failed")

    if not worktree_path or not worktree_path.exists():
        reasons.append("worktree unavailable")
        return _write(run_dir, result)

    name_status = _git(worktree_path, "diff", "--name-status", "HEAD")
    diff = _git(worktree_path, "diff", "HEAD", "--")
    untracked = _git(worktree_path, "ls-files", "--others", "--exclude-standard")
    if name_status is None or diff is None or untracked is None:
        reasons.append("diff unavailable")
        return _write(run_dir, result)

    untracked_files = _target_files([line for line in untracked.splitlines() if line])
    changed_files = _target_files(_changed_files(name_status)) + untracked_files
    result["changed_files"] = changed_files
    result["changed_file_count"] = len(changed_files)
    result["diff_line_count"] = sum(1 for line in diff.splitlines() if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))
    result["diff_line_count"] += sum(_line_count(worktree_path / path) for path in untracked_files)
    result["human_required_touched"] = [path for path in changed_files if _human_required(path, config.human_required_paths)]
    result["tests_weakened_or_deleted"] = _tests_weakened(name_status, diff)

    if result["changed_file_count"] > config.max_changed_files:
        reasons.append(f"changed_file_count exceeds max_changed_files: {result['changed_file_count']} > {config.max_changed_files}")
    if result["diff_line_count"] > config.max_diff_lines:
        reasons.append(f"diff_line_count exceeds max_diff_lines: {result['diff_line_count']} > {config.max_diff_lines}")
    if result["human_required_touched"]:
        reasons.append("human-required paths touched")
    if result["tests_weakened_or_deleted"]:
        reasons.append("tests appear weakened or deleted")
    return _write(run_dir, result)


def _git(cwd: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=False)
        return completed.stdout if completed.returncode == 0 else None
    except OSError:
        return None


def _line_count(path: Path) -> int:
    try:
        return len(path.read_text().splitlines())
    except (OSError, UnicodeDecodeError):
        return 0


def _changed_files(name_status: str) -> list[str]:
    files = []
    for line in name_status.splitlines():
        parts = line.split("\t")
        if not parts:
            continue
        files.append(parts[-1])
    return files


def _target_files(paths: list[str]) -> list[str]:
    return [path for path in paths if not path.startswith(".agent/runs/")]


def _human_required(path: str, patterns: list[str]) -> bool:
    return any(path.startswith(pattern) if pattern.endswith("/") else fnmatch.fnmatch(path, pattern) or path == pattern for pattern in patterns)


def _is_test(path: str) -> bool:
    parts = Path(path).parts
    return "tests" in parts or Path(path).name.startswith("test_") or Path(path).name.endswith("_test.py")


def _tests_weakened(name_status: str, diff: str) -> bool:
    for line in name_status.splitlines():
        parts = line.split("\t")
        if parts and parts[0] == "D" and parts[-1].startswith("tests/"):
            return True

    current_file = ""
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif _is_test(current_file) and line.startswith("-") and not line.startswith("---") and any(marker in line for marker in ASSERT_MARKERS):
            return True
        elif _is_test(current_file) and line.startswith("+") and not line.startswith("+++") and any(marker in line for marker in SKIP_MARKERS):
            return True
    return False


def _write(run_dir: Path, result: dict[str, object]) -> dict[str, object]:
    result["ok"] = not result["reasons"]
    (run_dir / "verifier_result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
