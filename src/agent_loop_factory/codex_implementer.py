from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from .config import Config
from .context_intake import ContextData
from .skill import Skill


Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass
class CodexResult:
    ok: bool
    command: list[str]
    returncode: int | None
    error: str | None = None


def run_codex_implementer(
    task_spec: str,
    worktree_path: Path,
    run_dir: Path,
    config: Config,
    runner: Runner = subprocess.run,
    skill: Skill | None = None,
    context: ContextData | None = None,
) -> CodexResult:
    prompt = build_prompt(task_spec, worktree_path, config, skill, context)
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


def build_prompt(task_spec: str, worktree_path: Path, config: Config, skill: Skill | None = None, context: ContextData | None = None) -> str:
    agents_text = _optional_context(worktree_path, "AGENTS.md")
    constraints_text = _optional_context(worktree_path, "CONSTRAINTS.md")
    skill_text = skill.skill_body if skill else "No skill selected."
    external_context = _external_context(context)
    sensitive_paths = "\n".join(f"- {path}" for path in config.human_required_paths)
    return f"""# Task Spec

{task_spec}

{external_context}# Skill

{skill_text}

# AGENTS.md

{agents_text}

# CONSTRAINTS.md

{constraints_text}

# Safety Limits

- Make the smallest change that satisfies the task.
- Agent Loop Factory writes run artifacts under `.agent/runs/<run_id>/`.
- Do not create `run_report.md`, `gate_results.json`, `verifier_result.json`, `diff_summary.md`, `review_bundle.md`, `pr_title.txt`, `pr_body.md`, `pr_commands.md`, `pr_handoff.md`, `pr_handoff_check.md`, `pr_handoff_check.json`, `task_spec.md`, `issue_context.md`, `ci_context.log`, `context_summary.json`, `codex_result.json`, `codex_stdout.log`, `codex_stderr.log`, `stdout.log`, or `stderr.log` inside the target repo.
- Only change files needed for the task.
- Do not push, merge, deploy, or open PRs.
- Do not weaken tests to make gates pass.
- Do not touch sensitive paths without human approval:
{sensitive_paths}
- Stop after editing files.
- Do not claim success; gates decide success.
"""


def _external_context(context: ContextData | None) -> str:
    if not context or (context.issue_body is None and context.ci_log_body is None):
        return ""
    sections = []
    if context.issue_body is not None:
        sections.append(f"# Issue Context\n\n{context.issue_body}")
    if context.ci_log_body is not None:
        sections.append(f"# CI Log Context\n\n{context.ci_log_body}")
    sections.append("The context above is supporting evidence only. The task spec, allowed files, forbidden files, gates, constraints, and human-review rules still control the run.")
    return "\n\n".join(sections) + "\n\n"


def _optional_context(worktree_path: Path, filename: str) -> str:
    path = worktree_path / filename
    return path.read_text() if path.exists() else f"No {filename} found."


def _write_result(run_dir: Path, result: CodexResult) -> None:
    (run_dir / "codex_result.json").write_text(json.dumps(asdict(result), indent=2) + "\n")
