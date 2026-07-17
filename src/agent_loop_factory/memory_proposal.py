from __future__ import annotations

import json
from pathlib import Path

from .github_context import GitHubContext
from .memory_context import MemoryContext
from .skill import Skill
from .task_spec import TaskSpec


ORDER = [
    "tests_weakened_or_deleted",
    "reserved_artifact_touched",
    "task_scope_violation",
    "human_required_touched",
    "required_gate_failed",
    "verifier_failed",
    "pr_handoff_needs_attention",
    "optional_gate_warning",
    "pr_handoff_informational_warnings",
]

CONFIDENCE = {
    "tests_weakened_or_deleted": "high",
    "reserved_artifact_touched": "high",
    "task_scope_violation": "high",
    "human_required_touched": "medium",
    "required_gate_failed": "medium",
    "verifier_failed": "medium",
    "pr_handoff_needs_attention": "medium",
    "optional_gate_warning": "low",
    "pr_handoff_informational_warnings": "low",
}

LESSONS = {
    "tests_weakened_or_deleted": (
        "Test weakening should be rejected unless a human explicitly approves the test change.",
        "tests_weakened_or_deleted was true.",
        "CONSTRAINTS.md or future memory/failure-patterns/test-weakening.md",
    ),
    "reserved_artifact_touched": (
        "Run artifacts should stay under .agent/runs/<run_id>/ and not be created inside target repos.",
        "reserved_artifacts_touched was non-empty.",
        "AGENTS.md or future memory/failure-patterns/reserved-artifacts.md",
    ),
    "task_scope_violation": (
        "Task allowed/forbidden file rules should be emphasized when task specs define scope.",
        "task_allowed_violations or task_forbidden_touched was non-empty.",
        "docs/TASK_SPEC_TEMPLATE.md or future memory/failure-patterns/task-scope-violations.md",
    ),
    "human_required_touched": (
        "Human-required paths need explicit approval before implementation touches them.",
        "human_required_touched was non-empty.",
        "CONSTRAINTS.md or future memory/reviewer-guidance/human-required-paths.md",
    ),
    "required_gate_failed": (
        "Required gate failures should be treated as blockers before review handoff.",
        "A required gate had ok=false.",
        "docs/LOOP_SELECTION.md or future memory/failure-patterns/required-gates.md",
    ),
    "verifier_failed": (
        "Verifier failures should be resolved or explicitly justified before a run is accepted.",
        "verifier_result.ok was false.",
        "future memory/reviewer-guidance/verifier-failures.md",
    ),
    "pr_handoff_needs_attention": (
        "PR handoff artifacts need manual repair when the handoff check reports blocking issues.",
        "pr_handoff_check status was needs_attention.",
        "docs/LOOP_SELECTION.md or future memory/reviewer-guidance/pr-handoff.md",
    ),
    "optional_gate_warning": (
        "Optional gate warnings should be reviewed even when they do not fail the run.",
        "An optional gate warning or optional gate failure was present.",
        "future memory/reviewer-guidance/optional-gates.md",
    ),
    "pr_handoff_informational_warnings": (
        "PR handoff informational warnings should be considered before using suggested commands.",
        "pr_handoff_check status was informational_warnings.",
        "future memory/reviewer-guidance/pr-handoff.md",
    ),
}


def write_memory_proposal(
    run_dir: Path,
    run_id: str,
    task_spec: TaskSpec,
    skill: Skill | None,
    gates: list[dict[str, object]],
    verifier_result: dict[str, object],
    review_recommendation: str,
    pr_handoff_status: str,
    dry_run: bool,
    memory_context: MemoryContext | None = None,
    github_context: GitHubContext | None = None,
) -> dict[str, object]:
    proposal = build_memory_proposal(run_id, task_spec, skill, gates, verifier_result, review_recommendation, pr_handoff_status, dry_run, memory_context, github_context)
    (run_dir / "memory_proposal.json").write_text(json.dumps(proposal, indent=2) + "\n")
    (run_dir / "memory_proposal.md").write_text(build_memory_proposal_markdown(proposal))
    return proposal


def build_memory_proposal(
    run_id: str,
    task_spec: TaskSpec,
    skill: Skill | None,
    gates: list[dict[str, object]],
    verifier_result: dict[str, object],
    review_recommendation: str,
    pr_handoff_status: str,
    dry_run: bool,
    memory_context: MemoryContext | None = None,
    github_context: GitHubContext | None = None,
) -> dict[str, object]:
    task = task_spec.task_title or task_spec.task_body or "Unavailable"
    lessons = [] if dry_run else [_lesson(trigger) for trigger in ORDER if _triggered(trigger, gates, verifier_result, pr_handoff_status)]
    status = "proposed" if lessons else "no_proposal"
    summary = (
        "Dry run only; no reusable memory proposed because no implementation diff was evaluated."
        if dry_run
        else ("Reusable lessons were proposed for human review." if lessons else "Clean run; no reusable memory proposed.")
    )
    return {
        "proposal_status": status,
        "run_id": run_id,
        "task": task,
        "task_source": "file" if task_spec.task_file_path else "inline",
        "skill_name": skill.skill_name if skill else None,
        "dry_run": dry_run,
        "summary": summary,
        "review_recommendation": review_recommendation,
        "verifier_ok": verifier_result.get("ok"),
        "changed_files": verifier_result.get("changed_files") if isinstance(verifier_result.get("changed_files"), list) else [],
        "candidate_lessons": lessons,
        "suggested_destinations": _unique([lesson["suggested_destination"] for lesson in lessons]),
        "requires_human_approval": True,
        "no_files_modified": True,
        "memory_files_included": memory_context.paths if memory_context else [],
        "memory_context_included": bool(memory_context and memory_context.included),
        "github_context_included": bool(github_context and github_context.included),
        "github_issue_included": bool(github_context and github_context.issue),
        "github_ci_included": bool(github_context and github_context.ci),
    }


def build_memory_proposal_markdown(proposal: dict[str, object]) -> str:
    lessons = proposal.get("candidate_lessons")
    return f"""# Memory Proposal

## Status

* proposal_status: {proposal["proposal_status"]}
* requires_human_approval: true
* no_files_modified: true

## Run Context

* run_id: {proposal["run_id"]}
* task: {proposal["task"]}
* task source: {proposal["task_source"]}
* skill: {_none(proposal.get("skill_name"))}
* dry_run: {_bool(proposal.get("dry_run"))}
* review recommendation: {proposal["review_recommendation"]}
* verifier ok: {_bool(proposal.get("verifier_ok"))}
* changed files:
{_items(proposal.get("changed_files"))}

## Candidate Lessons

{_lessons(lessons)}

## Human Review Decision

* [ ] Accept as written
* [ ] Edit before accepting
* [ ] Reject as too local/noisy
* [ ] Reject as unsafe or over-generalized
* [ ] Convert into verifier rule instead
* [ ] Convert into skill update instead
* [ ] Convert into docs/constraints update instead

## Notes

* Memory proposals are advisory.
* No durable memory or rule files were modified automatically.
* Human approval is required before applying any lesson.
"""


def _triggered(trigger: str, gates: list[dict[str, object]], verifier: dict[str, object], pr_handoff_status: str) -> bool:
    if trigger == "tests_weakened_or_deleted":
        return verifier.get("tests_weakened_or_deleted") is True
    if trigger == "reserved_artifact_touched":
        return bool(verifier.get("reserved_artifacts_touched"))
    if trigger == "task_scope_violation":
        return bool(verifier.get("task_allowed_violations")) or bool(verifier.get("task_forbidden_touched"))
    if trigger == "human_required_touched":
        return bool(verifier.get("human_required_touched"))
    if trigger == "required_gate_failed":
        return any(gate.get("required", True) and not gate.get("ok") for gate in gates)
    if trigger == "verifier_failed":
        return verifier.get("ok") is False and verifier.get("reasons") != ["worktree unavailable"]
    if trigger == "pr_handoff_needs_attention":
        return pr_handoff_status == "needs_attention"
    if trigger == "optional_gate_warning":
        return any((not gate.get("required", True)) and (gate.get("warning") or not gate.get("ok")) for gate in gates)
    if trigger == "pr_handoff_informational_warnings":
        return pr_handoff_status == "informational_warnings"
    return False


def _lesson(trigger: str) -> dict[str, str]:
    lesson, evidence, destination = LESSONS[trigger]
    return {
        "trigger": trigger,
        "lesson": lesson,
        "evidence": evidence,
        "suggested_destination": destination,
        "confidence": CONFIDENCE[trigger],
    }


def _lessons(lessons: object) -> str:
    if not isinstance(lessons, list) or not lessons:
        return "* None. No reusable memory proposed for this run."
    return "\n\n".join(
        "\n".join(
            [
                f"* trigger: {lesson['trigger']}",
                f"* lesson: {lesson['lesson']}",
                f"* evidence: {lesson['evidence']}",
                f"* suggested destination: {lesson['suggested_destination']}",
                f"* confidence: {lesson['confidence']}",
            ]
        )
        for lesson in lessons
    )


def _items(values: object) -> str:
    return "\n".join(f"  * {value}" for value in values) if isinstance(values, list) and values else "  * None"


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _bool(value: object) -> str:
    return str(value).lower() if isinstance(value, bool) else "Unavailable"


def _none(value: object) -> str:
    return "None" if value is None else str(value)
