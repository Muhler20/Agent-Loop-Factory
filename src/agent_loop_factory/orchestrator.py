from __future__ import annotations

import json
import secrets
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .codex_implementer import run_codex_implementer, write_codex_skip
from .config import load_config
from .context_intake import ContextData
from .create_worktree import create_worktree
from .memory_proposal import write_memory_proposal
from .pr_handoff import write_pr_handoff
from .pr_handoff_check import write_pr_handoff_check
from .run_gates import run_gates
from .review_bundle import recommendation, write_review_bundle
from .skill import Skill
from .summarize_diff import write_diff_summary
from .task_spec import TaskSpec, inline_task_spec, task_spec_from_body
from .update_progress import build_progress
from .verifier import run_verifier


def run(
    task_body: str,
    repo_root: Path,
    dry_run: bool = False,
    implementer: str | None = None,
    codex_runner=None,
    task_file_path: str | None = None,
    skill: Skill | None = None,
    context: ContextData | None = None,
) -> dict[str, object]:
    repo_root = repo_root.resolve()
    agent_dir = repo_root / ".agent"
    run_id = _run_id()
    run_dir = agent_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    task_spec = task_spec_from_body(task_body, task_file_path) if task_file_path else inline_task_spec(task_body)
    (run_dir / "task_spec.md").write_text(task_spec.task_body)
    if skill:
        (run_dir / "skill.md").write_text(skill.skill_body)
    context_summary = _write_context_artifacts(run_dir, run_id, context)

    config = load_config(agent_dir / "config.yaml")
    target_repo = (repo_root / config.target_repo_path).resolve()
    worktree_base = (repo_root / config.worktree_base_path).resolve()

    stdout_log = run_dir / "stdout.log"
    stderr_log = run_dir / "stderr.log"
    stdout_log.write_text(f"run_id={run_id}\ntask={task_spec.task_title}\ndry_run={dry_run}\n")
    stderr_log.write_text("")

    # TODO: future GitHub webhook trigger
    worktree = create_worktree(target_repo, worktree_base, run_id, dry_run=dry_run)
    gate_cwd = worktree.path if worktree.ok and worktree.path and not dry_run else target_repo

    selected_implementer = implementer if implementer is not None else config.implementer
    codex_result = None
    if selected_implementer == "codex":
        if dry_run:
            codex_result = write_codex_skip(run_dir, "dry-run: codex not executed")
        elif not worktree.ok or not worktree.path:
            codex_result = write_codex_skip(run_dir, "worktree unavailable: codex not executed")
        else:
            codex_result = run_codex_implementer(task_spec.task_body, worktree.path, run_dir, config, skill=skill, context=context, runner=codex_runner or subprocess.run)
    # TODO: future verifier agent call
    # TODO: future Docker build gate
    # TODO: future Docker Compose deployment check
    gates = run_gates(config, gate_cwd, run_dir, dry_run=dry_run or not worktree.ok)
    verifier_result = run_verifier(config, worktree.path if worktree.ok and not dry_run else None, run_dir, gates, task_spec)
    diff_summary = write_diff_summary(gate_cwd, run_dir / "diff_summary.md", config.max_diff_lines, dry_run=dry_run or not worktree.ok)
    implementer_ok = selected_implementer != "codex" or bool(codex_result and codex_result.ok)
    gates_ok = all(bool(gate["ok"]) for gate in gates if gate.get("required", True))
    ok = worktree.ok and implementer_ok and gates_ok and bool(verifier_result["ok"])

    review_recommendation, _ = recommendation(verifier_result, gates)
    handoff_check = write_pr_handoff_check(run_dir, worktree, gates, verifier_result, review_recommendation)
    memory_proposal = write_memory_proposal(run_dir, run_id, task_spec, skill, gates, verifier_result, review_recommendation, str(handoff_check["status"]), dry_run)
    write_review_bundle(run_dir, run_id, task_spec, skill, selected_implementer, worktree, gates, verifier_result, diff_summary, ok, handoff_check["status"], context_summary, memory_proposal)
    write_pr_handoff(run_dir, run_id, task_spec, skill, worktree, gates, verifier_result, review_recommendation, handoff_check["status"], context_summary, memory_proposal)
    report = _report(task_spec, skill, run_id, dry_run, selected_implementer, codex_result, config, worktree, gates, verifier_result, diff_summary, ok, review_recommendation, handoff_check["status"], context_summary, memory_proposal)
    (run_dir / "run_report.md").write_text(report)
    _update_state(agent_dir / "state.json", run_id, ok)

    blocker = "None." if worktree.ok else worktree.message
    (repo_root / "PROGRESS.md").write_text(
        build_progress(
            run_id=run_id,
            task=task_spec.task_title,
            status="passed" if ok else "failed",
            next_action="Review run artifacts and decide the next manual task.",
            blocker=blocker,
        )
    )

    # TODO: future draft PR creation
    return {"run_id": run_id, "run_dir": str(run_dir), "ok": ok, "dry_run": dry_run}


def _run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{secrets.token_hex(3)}"


def _write_context_artifacts(run_dir: Path, run_id: str, context: ContextData | None) -> dict[str, object]:
    context = context or ContextData()
    issue_artifact = f".agent/runs/{run_id}/issue_context.md" if context.issue_body is not None else None
    ci_artifact = f".agent/runs/{run_id}/ci_context.log" if context.ci_log_body is not None else None
    if context.issue_body is not None:
        (run_dir / "issue_context.md").write_text(context.issue_body)
    if context.ci_log_body is not None:
        (run_dir / "ci_context.log").write_text(context.ci_log_body)
    summary = {
        "issue_file_path": context.issue_file_path,
        "issue_size_bytes": context.issue_size_bytes,
        "issue_artifact_path": issue_artifact,
        "ci_log_file_path": context.ci_log_file_path,
        "ci_log_size_bytes": context.ci_log_size_bytes,
        "ci_log_artifact_path": ci_artifact,
        "context_summary_path": f".agent/runs/{run_id}/context_summary.json",
    }
    (run_dir / "context_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def _report(task_spec: TaskSpec, skill: Skill | None, run_id: str, dry_run: bool, implementer: str, codex_result, config, worktree, gates, verifier_result, diff_summary: str, ok: bool, review_recommendation: str = "Unavailable", handoff_check_status: str = "Unavailable", context_summary: dict[str, object] | None = None, memory_proposal: dict[str, object] | None = None) -> str:
    warnings = [str(gate["warning"]) for gate in gates if gate.get("warning")]
    if not worktree.ok:
        warnings.append(worktree.message)
    if codex_result and codex_result.error:
        warnings.append(codex_result.error)
    warning_text = "\n".join(f"- {warning}" for warning in warnings) or "- None."
    gate_text = "\n".join(_gate_report(gate) for gate in gates) or "- No gates detected."
    verifier_reasons = "\n".join(f"- {reason}" for reason in verifier_result["reasons"]) or "- None."
    verifier_warnings = "\n".join(f"- {warning}" for warning in verifier_result["warnings"]) or "- None."
    verifier_human = "\n".join(f"- {path}" for path in verifier_result["human_required_touched"]) or "- None."
    verifier_allowed = _list(verifier_result["task_allowed_files"])
    verifier_forbidden = _list(verifier_result["task_forbidden_files"])
    verifier_allowed_violations = _list(verifier_result["task_allowed_violations"])
    verifier_forbidden_touched = _list(verifier_result["task_forbidden_touched"])
    codex_text = "- Not used." if implementer != "codex" else (
        f"- command: {' '.join(codex_result.command)}\n"
        f"- returncode: {codex_result.returncode}\n"
        f"- result: {'ok' if codex_result.ok else 'not ok'}\n"
        f"- error: {codex_result.error or 'None.'}"
    )
    task_source = "file" if task_spec.task_file_path else "inline"
    task_file = f"- task_file_path: {task_spec.task_file_path}\n" if task_spec.task_file_path else ""
    skill_source = "file" if skill else "none"
    skill_name = skill.skill_name if skill else "none"
    skill_file = f"- skill_file_path: {skill.skill_file_path}\n" if skill else ""
    context_summary = context_summary or {}
    memory_proposal = memory_proposal or {"proposal_status": "Unavailable", "requires_human_approval": True, "no_files_modified": True}
    return f"""# Run Report

## Run

- run_id: {run_id}
- task: {task_spec.task_title}
- dry_run: {dry_run}
- implementer: {implementer}
- status: {"passed" if ok else "failed"}

## Task Spec

- task_title: {task_spec.task_title}
- task_source: {task_source}
{task_file}
## Skill

- skill_name: {skill_name}
- skill_source: {skill_source}
{skill_file}
## External Context

- issue_file_path: {_value(context_summary.get("issue_file_path"))}
- issue_context: {_value(context_summary.get("issue_artifact_path"))}
- ci_log_file_path: {_value(context_summary.get("ci_log_file_path"))}
- ci_context: {_value(context_summary.get("ci_log_artifact_path"))}
- context_summary: {_value(context_summary.get("context_summary_path"))}

## Worktree

- branch: {worktree.branch}
- path: {worktree.path}
- result: {worktree.message}

## Gates

{gate_text}

## Verifier

- ok: {verifier_result["ok"]}
- changed_file_count: {verifier_result["changed_file_count"]}
- diff_line_count: {verifier_result["diff_line_count"]}
- tests_weakened_or_deleted: {verifier_result["tests_weakened_or_deleted"]}

Reasons:
{verifier_reasons}

Warnings:
{verifier_warnings}

Human-required paths touched:
{verifier_human}

Task allowed files:
{verifier_allowed}

Task forbidden files:
{verifier_forbidden}

Task allowed violations:
{verifier_allowed_violations}

Task forbidden touched:
{verifier_forbidden_touched}

## Review Bundle

- path: .agent/runs/{run_id}/review_bundle.md
- recommendation: {review_recommendation}

## Memory Proposal

- path: .agent/runs/{run_id}/memory_proposal.md
- json: .agent/runs/{run_id}/memory_proposal.json
- proposal_status: {memory_proposal["proposal_status"]}
- requires_human_approval: true
- no files modified: true

## Draft PR Handoff

- pr_title: .agent/runs/{run_id}/pr_title.txt
- pr_body: .agent/runs/{run_id}/pr_body.md
- pr_commands: .agent/runs/{run_id}/pr_commands.md
- pr_handoff: .agent/runs/{run_id}/pr_handoff.md
- pr_handoff_check: .agent/runs/{run_id}/pr_handoff_check.md
- pr_handoff_check_json: .agent/runs/{run_id}/pr_handoff_check.json
- handoff_check_status: {handoff_check_status}
- no commands executed: true

## Codex Implementer

{codex_text}

## Warnings

{warning_text}

## Config

```json
{json.dumps(asdict(config), indent=2)}
```

## Diff Summary

```text
{diff_summary}
```
"""


def _list(values: object) -> str:
    items = values if isinstance(values, list) else []
    return "\n".join(f"- {value}" for value in items) or "- None."


def _value(value: object) -> str:
    return "None" if value is None else str(value)


def _gate_report(gate: dict[str, object]) -> str:
    warning = f" ({gate['warning']})" if gate.get("warning") else ""
    return (
        f"- {gate.get('name', gate.get('command'))}: {'ok' if gate.get('ok') else 'not ok'}{warning}\n"
        f"  - command: {gate['command']}\n"
        f"  - required: {str(gate.get('required', True)).lower()}"
    )


def _update_state(path: Path, run_id: str, ok: bool) -> None:
    state = {"last_run_id": None, "runs": []}
    if path.exists():
        try:
            state = json.loads(path.read_text())
        except json.JSONDecodeError:
            state = {"last_run_id": None, "runs": []}
    state["last_run_id"] = run_id
    state.setdefault("runs", []).append({"run_id": run_id, "ok": ok})
    path.write_text(json.dumps(state, indent=2) + "\n")
