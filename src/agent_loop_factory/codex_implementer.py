from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from .config import Config


Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass
class CodexResult:
    ok: bool
    command: list[str]
    returncode: int | None
    error: str | None = None


def run_codex_implementer(
    task: str,
    worktree_path: Path,
    run_dir: Path,
    config: Config,
    runner: Runner = subprocess.run,
) -> CodexResult:
    prompt = build_prompt(task, worktree_path, config)
    (run_dir / "codex_prompt.md").write_text(prompt)

    command = [config.codex_command, "exec", "--cd", str(worktree_path), "--sandbox", "workspace-write", *config.codex_exec_args, "-"]
    try:
        completed = runner(command, cwd=worktree_path, input=prompt, capture_output=True, text=True, check=False)
        result = CodexResult(
            ok=completed.returncode == 0,
            command=command,
            returncode=completed.returncode,
            error=None if completed.returncode == 0 else "codex exec failed",
        )
        stdout = completed.stdout
        stderr = completed.stderr
    except OSError as exc:
        result = CodexResult(ok=False, command=command, returncode=None, error=f"codex unavailable: {exc}")
        stdout = ""
        stderr = str(exc)

    (run_dir / "codex_stdout.log").write_text(stdout)
    (run_dir / "codex_stderr.log").write_text(stderr)
    _write_result(run_dir, result)
    return result


def write_codex_skip(run_dir: Path, reason: str) -> CodexResult:
    result = CodexResult(ok=False, command=[], returncode=None, error=reason)
    (run_dir / "codex_prompt.md").write_text("")
    (run_dir / "codex_stdout.log").write_text("")
    (run_dir / "codex_stderr.log").write_text(reason + "\n")
    _write_result(run_dir, result)
    return result


def build_prompt(task: str, worktree_path: Path, config: Config) -> str:
    agents = worktree_path / "AGENTS.md"
    agents_text = agents.read_text() if agents.exists() else "No AGENTS.md found."
    sensitive_paths = "\n".join(f"- {path}" for path in config.human_required_paths)
    return f"""# Task

{task}

# Repository Rules

{agents_text}

# Safety Limits

- Make the smallest change that satisfies the task.
- Do not push, merge, deploy, or open PRs.
- Do not weaken tests to make gates pass.
- Do not touch sensitive paths without human approval:
{sensitive_paths}
- Stop after editing files.
- Do not claim success; gates decide success.
"""


def _write_result(run_dir: Path, result: CodexResult) -> None:
    (run_dir / "codex_result.json").write_text(json.dumps(asdict(result), indent=2) + "\n")
