from __future__ import annotations

import json
import secrets
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .codex_implementer import run_codex_implementer, write_codex_skip
from .config import load_config
from .create_worktree import create_worktree
from .run_gates import run_gates
from .summarize_diff import write_diff_summary
from .update_progress import build_progress


def run(task: str, repo_root: Path, dry_run: bool = False, implementer: str | None = None, codex_runner=None) -> dict[str, object]:
    repo_root = repo_root.resolve()
    agent_dir = repo_root / ".agent"
    run_id = _run_id()
    run_dir = agent_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(agent_dir / "config.yaml")
    target_repo = (repo_root / config.target_repo_path).resolve()
    worktree_base = (repo_root / config.worktree_base_path).resolve()

    stdout_log = run_dir / "stdout.log"
    stderr_log = run_dir / "stderr.log"
    stdout_log.write_text(f"run_id={run_id}\ntask={task}\ndry_run={dry_run}\n")
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
            codex_result = run_codex_implementer(task, worktree.path, run_dir, config, runner=codex_runner or subprocess.run)
    # TODO: future verifier agent call
    # TODO: future Docker build gate
    # TODO: future Docker Compose deployment check
    gates = run_gates(config, gate_cwd, run_dir, dry_run=dry_run or not worktree.ok)
    diff_summary = write_diff_summary(gate_cwd, run_dir / "diff_summary.md", config.max_diff_lines, dry_run=dry_run or not worktree.ok)
    implementer_ok = selected_implementer != "codex" or bool(codex_result and codex_result.ok)
    ok = worktree.ok and implementer_ok and all(bool(gate["ok"]) for gate in gates)

    report = _report(task, run_id, dry_run, selected_implementer, codex_result, config, worktree, gates, diff_summary, ok)
    (run_dir / "run_report.md").write_text(report)
    _update_state(agent_dir / "state.json", run_id, ok)

    blocker = "None." if worktree.ok else worktree.message
    (repo_root / "PROGRESS.md").write_text(
        build_progress(
            run_id=run_id,
            task=task,
            status="passed" if ok else "stopped",
            next_action="Review run artifacts and decide the next manual task.",
            blocker=blocker,
        )
    )

    # TODO: future draft PR creation
    return {"run_id": run_id, "run_dir": str(run_dir), "ok": ok, "dry_run": dry_run}


def _run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{secrets.token_hex(3)}"


def _report(task: str, run_id: str, dry_run: bool, implementer: str, codex_result, config, worktree, gates, diff_summary: str, ok: bool) -> str:
    warnings = [str(gate["warning"]) for gate in gates if gate.get("warning")]
    if not worktree.ok:
        warnings.append(worktree.message)
    if codex_result and codex_result.error:
        warnings.append(codex_result.error)
    warning_text = "\n".join(f"- {warning}" for warning in warnings) or "- None."
    gate_text = "\n".join(f"- {gate['command']}: {'ok' if gate['ok'] else 'not ok'}" for gate in gates) or "- No gates detected."
    codex_text = "- Not used." if implementer != "codex" else (
        f"- command: {' '.join(codex_result.command)}\n"
        f"- returncode: {codex_result.returncode}\n"
        f"- result: {'ok' if codex_result.ok else 'not ok'}\n"
        f"- error: {codex_result.error or 'None.'}"
    )
    return f"""# Run Report

## Run

- run_id: {run_id}
- task: {task}
- dry_run: {dry_run}
- implementer: {implementer}
- status: {"passed" if ok else "stopped"}

## Worktree

- branch: {worktree.branch}
- path: {worktree.path}
- result: {worktree.message}

## Gates

{gate_text}

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
