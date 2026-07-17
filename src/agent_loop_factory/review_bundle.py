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
    handoff_check_status: str | None = None,
    context_summary: dict[str, object] | None = None,
    memory_proposal: dict[str, object] | None = None,
    memory_summary: dict[str, object] | None = None,
    github_summary: dict[str, object] | None = None,
    advisory_review: dict[str, object] | None = None,
) -> tuple[str, str]:
    decision, reason = recommendation(verifier_result, gates)
    (run_dir / "review_bundle.md").write_text(
        build_review_bundle(run_id, task_spec, skill, implementer, worktree, gates, verifier_result, diff_summary, ok, decision, reason, handoff_check_status, context_summary, memory_proposal, memory_summary, github_summary, advisory_review)
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
    handoff_check_status: str | None = None,
    context_summary: dict[str, object] | None = None,
    memory_proposal: dict[str, object] | None = None,
    memory_summary: dict[str, object] | None = None,
    github_summary: dict[str, object] | None = None,
    advisory_review: dict[str, object] | None = None,
) -> str:
    decision, reason = (decision, reason) if decision and reason else recommendation(verifier_result, gates)
    task_source = "file" if task_spec.task_file_path else "inline"
    task_file = task_spec.task_file_path or "None"
    skill_name = skill.skill_name if skill else "None"
    skill_file = skill.skill_file_path if skill else "None"
    context_summary = context_summary or {}
    proposal_status = (memory_proposal or {}).get("proposal_status", "Unavailable")
    memory_context = _memory_context(memory_summary)
    github_context = _github_context(github_summary)
    advisory_context = _advisory_context(advisory_review)
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

## External Context

- issue context artifact path: {_none(context_summary.get("issue_artifact_path"))}
- CI log context artifact path: {_none(context_summary.get("ci_log_artifact_path"))}
- context summary artifact path: {_none(context_summary.get("context_summary_path"))}

{memory_context}

{github_context}

{advisory_context}

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

## Memory Proposal

- memory_proposal.md
- memory_proposal.json
- proposal_status: {proposal_status}
- No durable memory or rule files were modified automatically.

## Draft PR Handoff

- pr_title.txt
- pr_body.md
- pr_commands.md
- pr_handoff.md
- pr_handoff_check.md
- pr_handoff_check.json
- handoff check status: {handoff_check_status or "Unavailable"}
- No push or PR creation was performed.
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


def _none(value: object) -> str:
    return "None" if value is None else str(value)


def _warning(value: object) -> str:
    return str(value) if value else "None"


def _memory_context(memory_summary: dict[str, object] | None) -> str:
    if not memory_summary:
        return ""
    return """## Memory Context

- memory_context.md
- memory_context.json
- Memory files were explicitly selected by the human.
- No memory files were modified.
"""


def _github_context(github_summary: dict[str, object] | None) -> str:
    if not github_summary:
        return ""
    lines = [
        "## GitHub Context",
        "",
        "- GitHub context was fetched read-only.",
        "- No GitHub writes were performed.",
    ]
    if github_summary.get("issue_context_included"):
        lines.append("- See github_issue_context.md / github_issue_context.json.")
    if github_summary.get("ci_context_included"):
        lines.append("- See github_ci_context.log / github_ci_context.json.")
    lines.append("- See github_context_summary.json.")
    return "\n".join(lines) + "\n"


def _advisory_context(advisory_review: dict[str, object] | None) -> str:
    if not advisory_review:
        return ""
    rubric = ""
    if advisory_review.get("reviewer_rubric_included"):
        rubric = f"""- Reviewer rubric was explicitly selected.
- See advisory_review_rubric.md / advisory_review_rubric.json.
- Rubric source: {advisory_review.get("reviewer_rubric_path")}
- Automatic rubric selection: false
"""
    return f"""## Advisory Review

- Advisory review was run.
- It is advisory only.
- It does not affect verifier_result.json.
- See advisory_review.md and advisory_review.json.
- Recommendation: {advisory_review.get("recommendation")}
{rubric}
"""
