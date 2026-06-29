from __future__ import annotations

from pathlib import Path

from .skill import Skill
from .task_spec import TaskSpec


def recommendation(verifier_result: dict[str, object], gates: list[dict[str, object]]) -> tuple[str, str]:
    if not verifier_result.get("ok"):
        return "reject_or_rework", "verifier failed"
    if any(gate.get("required", True) and not gate.get("ok") for gate in gates):
        return "reject_or_rework", "required gate failed"
    if verifier_result.get("human_required_touched"):
        return "manual_review_required", "human-required paths touched"
    if verifier_result.get("warnings") or any((not gate.get("required", True)) and gate.get("warning") for gate in gates):
        return "manual_review_required", "warnings present"
    return "ready_for_human_review", "gates and verifier passed"


def write_review_bundle(
    run_dir: Path,
    run_id: str,
    task_spec: TaskSpec,
    skill: Skill | None,
    implementer: str,
    worktree,
    gates: list[dict[str, object]],
    verifier_result: dict[str, object],
    diff_summary: str,
    ok: bool,
) -> tuple[str, str]:
    decision, reason = recommendation(verifier_result, gates)
    (run_dir / "review_bundle.md").write_text(
        build_review_bundle(run_id, task_spec, skill, implementer, worktree, gates, verifier_result, diff_summary, ok, decision, reason)
    )
    return decision, reason


def build_review_bundle(
    run_id: str,
    task_spec: TaskSpec,
    skill: Skill | None,
    implementer: str,
    worktree,
    gates: list[dict[str, object]],
    verifier_result: dict[str, object],
    diff_summary: str,
    ok: bool,
    decision: str | None = None,
    reason: str | None = None,
) -> str:
    decision, reason = (decision, reason) if decision and reason else recommendation(verifier_result, gates)
    task_source = "file" if task_spec.task_file_path else "inline"
    task_file = task_spec.task_file_path or "None"
    skill_name = skill.skill_name if skill else "None"
    skill_file = skill.skill_file_path if skill else "None"
    return f"""# Human Review Bundle

## Run Summary

- run_id: {run_id}
- task: {task_spec.task_title or task_spec.task_body or "Unavailable"}
- status: {"passed" if ok else "failed"}
- implementer: {implementer or "Unavailable"}
- worktree path: {_value(getattr(worktree, "path", None))}
- branch: {_value(getattr(worktree, "branch", None))}

## Task

- task source: {task_source}
- task file path: {task_file}
- task title: {task_spec.task_title or "None"}
- allowed files:
{_list(task_spec.allowed_files)}
- forbidden files:
{_list(task_spec.forbidden_files)}

## Skill

- skill name: {skill_name}
- skill file path: {skill_file}

## Changed Files

{_list(verifier_result.get("changed_files"))}
- changed_file_count: {_value(verifier_result.get("changed_file_count"))}
- diff_line_count: {_value(verifier_result.get("diff_line_count"))}

## Gates

{_gates(gates)}

## Verifier

- ok: {_value(verifier_result.get("ok"))}
- reasons:
{_list(verifier_result.get("reasons"))}
- warnings:
{_list(verifier_result.get("warnings"))}
- human-required paths touched:
{_list(verifier_result.get("human_required_touched"))}
- reserved artifacts touched:
{_list(verifier_result.get("reserved_artifacts_touched"))}
- task allowed violations:
{_list(verifier_result.get("task_allowed_violations"))}
- task forbidden touched:
{_list(verifier_result.get("task_forbidden_touched"))}
- tests_weakened_or_deleted: {_value(verifier_result.get("tests_weakened_or_deleted"))}

## Diff Summary

```text
{diff_summary or "None"}
```

## Human Review Checklist

- Confirm the changed files match the task.
- Confirm no tests were weakened, skipped, or deleted.
- Confirm gates are appropriate for the task.
- Review the diff manually.
- Confirm the task spec allowed/forbidden files were respected.
- Confirm no human-required paths were touched.
- Confirm no generated artifacts leaked into the target repo.
- Decide whether to accept, reject, or request changes.

## Recommended Decision

- recommendation: {decision}
- reason: {reason}
"""


def _gates(gates: list[dict[str, object]]) -> str:
    if not gates:
        return "- None"
    return "\n".join(
        "\n".join(
            [
                f"- name: {_value(gate.get('name'))}",
                f"  command: {_value(gate.get('command'))}",
                f"  required: {_value(gate.get('required', True))}",
                f"  result: {'ok' if gate.get('ok') else 'not ok'}",
                f"  warning: {_warning(gate.get('warning'))}",
            ]
        )
        for gate in gates
    )


def _list(values: object) -> str:
    return "\n".join(f"  - {value}" for value in values) if isinstance(values, list) and values else "  - None"


def _value(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return "Unavailable" if value is None else str(value)


def _warning(value: object) -> str:
    return str(value) if value else "None"
