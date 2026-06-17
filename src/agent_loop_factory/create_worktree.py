from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WorktreeResult:
    ok: bool
    branch: str
    path: Path | None
    message: str


def create_worktree(target_repo: Path, base_path: Path, run_id: str, dry_run: bool = False) -> WorktreeResult:
    branch = f"agent/{run_id}"
    repo_name = target_repo.resolve().name
    worktree_path = (base_path / f"{repo_name}-{run_id}").resolve()
    if dry_run:
        return WorktreeResult(True, branch, worktree_path, "dry-run: skipped git worktree creation")

    try:
        subprocess.run(["git", "-C", str(target_repo), "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True)
        base_path.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "-C", str(target_repo), "worktree", "add", "-b", branch, str(worktree_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        return WorktreeResult(False, branch, None, f"git worktree creation failed: {exc}")
    return WorktreeResult(True, branch, worktree_path, "git worktree created")
