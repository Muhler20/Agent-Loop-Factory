from __future__ import annotations

import fnmatch
import json
import subprocess
from pathlib import Path

from .config import Config
from .task_spec import TaskSpec


SKIP_MARKERS = ("@unittest.skip", "pytest.mark.skip", "skipTest")
ASSERT_MARKERS = ("assert", "assertEqual", "assertTrue", "assertFalse", "assertRaises")
RESERVED_ARTIFACT_FILENAMES = {
    "run_report.md",
    "gate_results.json",
    "verifier_result.json",
    "diff_summary.md",
    "review_bundle.md",
    "pr_title.txt",
    "pr_body.md",
    "pr_commands.md",
    "pr_handoff.md",
    "pr_handoff_check.md",
    "pr_handoff_check.json",
    "task_spec.md",
    "stdout.log",
    "stderr.log",
    "codex_prompt.md",
    "codex_stdout.log",
    "codex_stderr.log",
    "codex_result.json",
}


def run_verifier(
    config: Config,
    worktree_path: Path | None,
    run_dir: Path,
    gates: list[dict[str, object]],
    task_spec: TaskSpec | None = None,
) -> dict[str, object]:
    allowed_files = task_spec.allowed_files if task_spec else []
    forbidden_files = task_spec.forbidden_files if task_spec else []
    result: dict[str, object] = {
        "ok": True,
        "reasons": [],
        "warnings": [],
        "changed_files": [],
        "changed_file_count": 0,
        "diff_line_count": 0,
        "human_required_touched": [],
        "reserved_artifacts_touched": [],
        "tests_weakened_or_deleted": False,
        "task_allowed_files": allowed_files,
        "task_forbidden_files": forbidden_files,
        "task_allowed_violations": [],
        "task_forbidden_touched": [],
    }
    reasons = result["reasons"]

    failed_required_gates = [gate for gate in gates if gate.get("required", True) and not gate.get("ok")]
    failed_optional_gates = [gate for gate in gates if not gate.get("required", True) and not gate.get("ok")]
    if failed_required_gates:
        reasons.append("one or more gates failed")
    for gate in failed_optional_gates:
        result["warnings"].append(f"optional gate failed: {gate.get('name', gate.get('command', 'unknown'))}")

    if not worktree_path or not worktree_path.exists():
        reasons.append("worktree unavailable")
        return _write(run_dir, result)

    name_status = _git(worktree_path, "diff", "--name-status", "HEAD")
    diff = _git(worktree_path, "diff", "HEAD", "--")
    untracked = _git(worktree_path, "ls-files", "--others", "--exclude-standard")
    if name_status is None or diff is None or untracked is None:
        reasons.append("diff unavailable")
        return _write(run_dir, result)

    untracked_files = _target_files([line for line in untracked.splitlines() if line], worktree_path, run_dir)
    changed_files = _target_files(_changed_files(name_status), worktree_path, run_dir) + untracked_files
    result["changed_files"] = changed_files
    result["changed_file_count"] = len(changed_files)
    result["diff_line_count"] = sum(1 for line in diff.splitlines() if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))
    result["diff_line_count"] += sum(_line_count(worktree_path / path) for path in untracked_files)
    result["human_required_touched"] = [path for path in changed_files if _human_required(path, config.human_required_paths)]
    result["reserved_artifacts_touched"] = [path for path in changed_files if Path(path).name in RESERVED_ARTIFACT_FILENAMES]
    result["tests_weakened_or_deleted"] = _tests_weakened(name_status, diff)
    result["task_allowed_violations"] = [path for path in changed_files if allowed_files and not _matches_any(path, allowed_files)]
    result["task_forbidden_touched"] = [path for path in changed_files if _matches_any(path, forbidden_files)]

    if result["changed_file_count"] > config.max_changed_files:
        reasons.append(f"changed_file_count exceeds max_changed_files: {result['changed_file_count']} > {config.max_changed_files}")
    if result["diff_line_count"] > config.max_diff_lines:
        reasons.append(f"diff_line_count exceeds max_diff_lines: {result['diff_line_count']} > {config.max_diff_lines}")
    if result["human_required_touched"]:
        reasons.append("human-required paths touched")
    for path in result["reserved_artifacts_touched"]:
        reasons.append(f"reserved run artifact file changed in target repo: {path}")
    for path in result["task_allowed_violations"]:
        reasons.append(f"changed file outside task allowed files: {path}")
    for path in result["task_forbidden_touched"]:
        reasons.append(f"task forbidden file touched: {path}")
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


def _target_files(paths: list[str], worktree_path: Path, run_dir: Path) -> list[str]:
    run_prefix = _run_dir_prefix(worktree_path, run_dir)
    return [path for path in paths if not path.startswith(".agent/runs/") and (not run_prefix or not path.startswith(run_prefix))]


def _run_dir_prefix(worktree_path: Path, run_dir: Path) -> str | None:
    try:
        relative = run_dir.resolve().relative_to(worktree_path.resolve())
    except ValueError:
        return None
    return relative.as_posix().rstrip("/") + "/"


def _human_required(path: str, patterns: list[str]) -> bool:
    return any(path.startswith(pattern) if pattern.endswith("/") else fnmatch.fnmatch(path, pattern) or path == pattern for pattern in patterns)


def _matches_any(path: str, entries: list[str]) -> bool:
    normalized = _normalize(path)
    return any(normalized.startswith(entry) if entry.endswith("/") else normalized == entry for entry in map(_normalize, entries))


def _normalize(path: str) -> str:
    return path.replace("\\", "/")


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
