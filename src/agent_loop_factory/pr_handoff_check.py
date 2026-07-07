from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Callable


CRITICAL_CHECKS = {
    "verifier_ok",
    "required_gates_ok",
    "review_recommendation_ready",
    "changed_files_present",
    "no_human_required_paths",
    "no_task_scope_violations",
    "no_reserved_artifacts_touched",
    "worktree_path_available",
    "worktree_path_exists",
    "worktree_is_git_repo",
    "branch_available",
}


def write_pr_handoff_check(
    run_dir: Path,
    worktree,
    gates: list[dict[str, object]],
    verifier_result: dict[str, object],
    review_recommendation: str,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    which: Callable[[str], str | None] = shutil.which,
) -> dict[str, object]:
    result = build_pr_handoff_check(worktree, gates, verifier_result, review_recommendation, runner, which)
    (run_dir / "pr_handoff_check.json").write_text(json.dumps(result, indent=2) + "\n")
    (run_dir / "pr_handoff_check.md").write_text(build_pr_handoff_check_markdown(result))
    return result


def build_pr_handoff_check(
    worktree,
    gates: list[dict[str, object]],
    verifier_result: dict[str, object],
    review_recommendation: str,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    which: Callable[[str], str | None] = shutil.which,
) -> dict[str, object]:
    worktree_path = getattr(worktree, "path", None)
    branch = getattr(worktree, "branch", None)
    path_exists = bool(worktree_path and Path(worktree_path).exists())
    checks = [
        _check("verifier_ok", verifier_result.get("ok") is True, "Verifier passed.", "Verifier did not pass."),
        _check("required_gates_ok", all(bool(gate.get("ok")) for gate in gates if gate.get("required", True)), "Required gates passed.", "One or more required gates failed."),
        _check("review_recommendation_ready", review_recommendation == "ready_for_human_review", "Review recommendation is ready_for_human_review.", f"Review recommendation is {review_recommendation}."),
        _check("changed_files_present", bool(verifier_result.get("changed_files")), "Changed files are present.", "No changed files were reported."),
        _check("no_human_required_paths", not verifier_result.get("human_required_touched"), "No human-required paths were touched.", "Human-required paths were touched."),
        _check("no_task_scope_violations", not verifier_result.get("task_allowed_violations") and not verifier_result.get("task_forbidden_touched"), "Task allowed/forbidden file rules passed.", "Task scope violations were reported."),
        _check("no_reserved_artifacts_touched", not verifier_result.get("reserved_artifacts_touched"), "No reserved run artifacts were touched in the target repo.", "Reserved run artifacts were touched in the target repo."),
        _check("worktree_path_available", bool(worktree_path), "Worktree path is present.", "Worktree path is missing."),
        _check("worktree_path_exists", path_exists, "Worktree path exists.", "Worktree path does not exist."),
        _check("worktree_is_git_repo", _git_ok(runner, worktree_path, "rev-parse", "--is-inside-work-tree") if path_exists else False, "Worktree is inside a git repo.", "Worktree is not inside a git repo."),
        _check("branch_available", bool(branch), "Branch is present.", "Branch is missing."),
        _check("origin_remote_present", _git_ok(runner, worktree_path, "remote", "get-url", "origin") if path_exists else False, "Origin remote is configured.", "Origin remote is missing.", critical=False),
        _check("gh_available", which("gh") is not None, "GitHub CLI is available for the optional gh pr create command.", "GitHub CLI is missing; this only affects the optional gh pr create command.", critical=False),
    ]
    blocking = [str(check["detail"]) for check in checks if check["critical"] and not check["ok"]]
    warnings = [str(check["detail"]) for check in checks if not check["critical"] and not check["ok"]]
    status = "needs_attention" if blocking else ("informational_warnings" if warnings else "ready")
    return {"status": status, "checks": checks, "warnings": warnings, "blocking_reasons": blocking}


def build_pr_handoff_check_markdown(result: dict[str, object]) -> str:
    status = result["status"]
    return f"""# PR Handoff Check

## Status

- status: {status}

## Blocking Reasons

{_items(result.get("blocking_reasons"))}

## Warnings

{_items(result.get("warnings"))}

## Checks

{_checks(result.get("checks"))}

## Next Step

{_next_step(str(status))}
"""


def _check(name: str, ok: bool, pass_detail: str, fail_detail: str, critical: bool = True) -> dict[str, object]:
    return {"name": name, "ok": ok, "critical": critical, "detail": pass_detail if ok else fail_detail}


def _git_ok(runner: Callable[..., subprocess.CompletedProcess], worktree_path: Path | str | None, *args: str) -> bool:
    if not worktree_path:
        return False
    try:
        completed = runner(["git", "-C", str(worktree_path), *args], capture_output=True, text=True, check=False)
    except OSError:
        return False
    return completed.returncode == 0


def _items(values: object) -> str:
    return "\n".join(f"- {value}" for value in values) if isinstance(values, list) and values else "- None"


def _checks(values: object) -> str:
    if not isinstance(values, list) or not values:
        return "- None"
    return "\n".join(
        f"- check name: {check['name']}\n  ok: {str(check['ok']).lower()}\n  critical: {str(check['critical']).lower()}\n  detail: {check['detail']}"
        for check in values
    )


def _next_step(status: str) -> str:
    if status == "ready":
        return "Review pr_commands.md manually before running any command."
    if status == "informational_warnings":
        return "Review warnings, then inspect pr_commands.md manually."
    return "Do not use pr_commands.md until the blocking reasons are resolved."
