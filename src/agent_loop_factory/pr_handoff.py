from __future__ import annotations

import shlex
from pathlib import Path

from .skill import Skill
from .task_spec import TaskSpec


def write_pr_handoff(
    run_dir: Path,
    run_id: str,
    task_spec: TaskSpec,
    skill: Skill | None,
    worktree,
    gates: list[dict[str, object]],
    verifier_result: dict[str, object],
    recommendation: str,
    handoff_check_status: str = "Unavailable",
    context_summary: dict[str, object] | None = None,
) -> None:
    title = pr_title(run_id, task_spec)
    (run_dir / "pr_title.txt").write_text(title + "\n")
    (run_dir / "pr_body.md").write_text(build_pr_body(task_spec, skill, gates, verifier_result, recommendation, handoff_check_status, context_summary))
    (run_dir / "pr_commands.md").write_text(build_pr_commands(run_dir, title, worktree, verifier_result))
    (run_dir / "pr_handoff.md").write_text(build_pr_handoff(run_dir, recommendation, handoff_check_status, context_summary))


def pr_title(run_id: str, task_spec: TaskSpec) -> str:
    source = task_spec.task_title or task_spec.task_body or f"Agent Loop Factory run {run_id}"
    title = " ".join(source.split()).strip() or f"Agent Loop Factory run {run_id}"
    return title[:100].rstrip()


def build_pr_body(
    task_spec: TaskSpec,
    skill: Skill | None,
    gates: list[dict[str, object]],
    verifier_result: dict[str, object],
    recommendation: str,
    handoff_check_status: str = "Unavailable",
    context_summary: dict[str, object] | None = None,
) -> str:
    task_source = "file" if task_spec.task_file_path else "inline"
    context_summary = context_summary or {}
    return f"""# Summary

{task_spec.task_title or task_spec.task_body or "Agent Loop Factory run"}

# Task

* task source: {task_source}
* task file path: {task_spec.task_file_path or "None"}
* task title: {task_spec.task_title or "None"}
* allowed files:
{_bullets(task_spec.allowed_files)}
* forbidden files:
{_bullets(task_spec.forbidden_files)}

# Skill

* skill name: {skill.skill_name if skill else "None"}
* skill file path: {skill.skill_file_path if skill else "None"}

# External Context

* issue context: {_basename(context_summary.get("issue_artifact_path"))}
* CI log context: {_basename(context_summary.get("ci_log_artifact_path"))}
* context summary: {_basename(context_summary.get("context_summary_path"))}

# Changed Files

{_bullets(verifier_result.get("changed_files"))}
* changed_file_count: {_value(verifier_result.get("changed_file_count"))}
* diff_line_count: {_value(verifier_result.get("diff_line_count"))}

# Gates

{_gates(gates)}

# Verifier

* ok: {_value(verifier_result.get("ok"))}
* reasons:
{_bullets(verifier_result.get("reasons"))}
* warnings:
{_bullets(verifier_result.get("warnings"))}
* human_required_touched:
{_bullets(verifier_result.get("human_required_touched"))}
* reserved_artifacts_touched:
{_bullets(verifier_result.get("reserved_artifacts_touched"))}
* task_allowed_violations:
{_bullets(verifier_result.get("task_allowed_violations"))}
* task_forbidden_touched:
{_bullets(verifier_result.get("task_forbidden_touched"))}
* tests_weakened_or_deleted: {_value(verifier_result.get("tests_weakened_or_deleted"))}

# Review

* recommendation: {recommendation}
* review bundle: review_bundle.md
* handoff check: pr_handoff_check.md
* handoff check json: pr_handoff_check.json
* handoff check status: {handoff_check_status}

# Safety

* This PR handoff was prepared by Agent Loop Factory.
* Agent Loop Factory did not push, open a PR, merge, or deploy.
* A human must review the diff and artifacts before running any commands.
"""


def build_pr_commands(run_dir: Path, pr_title_text: str, worktree, verifier_result: dict[str, object]) -> str:
    worktree_path = getattr(worktree, "path", None)
    branch = getattr(worktree, "branch", None)
    changed_files = verifier_result.get("changed_files")
    files = changed_files if isinstance(changed_files, list) else []
    add_command = f"git add {' '.join(shlex.quote(str(path)) for path in files)}" if files else "# No changed files to add."
    worktree_text = str(worktree_path) if worktree_path else "Unavailable"
    branch_text = str(branch) if branch else "Unavailable"
    adjustment = ""
    if not worktree_path or not branch:
        adjustment = "\nNote: worktree path or branch is unavailable; adjust these commands manually.\n"
    return f"""# Draft PR Commands

Warnings:

* Review before running.
* Do not run if verifier failed.
* Do not run if required gates failed.
* Do not run if changed files are unexpected.
* Do not run if human-required paths were touched.
* These commands are suggestions only.
{adjustment}
## Inspect the worktree

```bash
cd {shlex.quote(worktree_text)}
git status
git diff
```

## Commit locally

```bash
{add_command}
git commit -m {_double_quote(pr_title_text)}
```

## Push branch

```bash
git push -u origin {shlex.quote(branch_text)}
```

## Create draft PR using GitHub CLI

```bash
gh pr create \\
  --draft \\
  --base main \\
  --head {shlex.quote(branch_text)} \\
  --title "$(cat {shlex.quote(str((run_dir / "pr_title.txt").resolve()))})" \\
  --body-file {shlex.quote(str((run_dir / "pr_body.md").resolve()))}
```
"""


def build_pr_handoff(run_dir: Path, recommendation: str, handoff_check_status: str = "Unavailable", context_summary: dict[str, object] | None = None) -> str:
    context_summary = context_summary or {}
    return f"""# Draft PR Handoff

* pr_title.txt: {run_dir / "pr_title.txt"}
* pr_body.md: {run_dir / "pr_body.md"}
* pr_commands.md: {run_dir / "pr_commands.md"}
* pr_handoff_check.md: {run_dir / "pr_handoff_check.md"}
* pr_handoff_check.json: {run_dir / "pr_handoff_check.json"}
* issue_context.md: {_none(context_summary.get("issue_artifact_path"))}
* ci_context.log: {_none(context_summary.get("ci_log_artifact_path"))}
* context_summary.json: {_none(context_summary.get("context_summary_path"))}
* recommendation: {recommendation}
* handoff check status: {handoff_check_status}
* no commands were executed: true
"""


def _gates(gates: list[dict[str, object]]) -> str:
    if not gates:
        return "* None"
    return "\n".join(
        "\n".join(
            [
                f"* name: {_value(gate.get('name'))}",
                f"  * command: {_value(gate.get('command'))}",
                f"  * required: {_value(gate.get('required', True))}",
                f"  * result: {'ok' if gate.get('ok') else 'not ok'}",
                f"  * warning: {gate.get('warning') or 'None'}",
            ]
        )
        for gate in gates
    )


def _bullets(values: object) -> str:
    return "\n".join(f"  * {value}" for value in values) if isinstance(values, list) and values else "  * None"


def _value(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return "Unavailable" if value is None else str(value)


def _none(value: object) -> str:
    return "None" if value is None else str(value)


def _basename(value: object) -> str:
    return Path(str(value)).name if value else "None"


def _double_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`") + '"'
