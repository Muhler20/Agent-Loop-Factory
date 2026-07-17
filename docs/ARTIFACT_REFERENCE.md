# Artifact Reference

## Run Directory

Each run writes local receipts under:

```text
.agent/runs/<run_id>/
```

Artifacts are review inputs only. They do not commit, push, open PRs, merge, deploy, or update durable memory.

## Core Artifacts

### `run_report.md`

What it is: human-readable run summary.
When it exists: every run.
Why read it: start here for status, task, worktree path, gates, verifier result, and recommendation.
Warning signs: failed status, missing worktree, required gate failure, verifier failure, scope warning, or Codex unavailable.

### `stdout.log`

What it is: orchestrator stdout capture.
When it exists: every run.
Why read it: debug unexpected orchestration behavior.
Warning signs: command errors, truncated output, or messages that conflict with JSON artifacts.

### `stderr.log`

What it is: orchestrator stderr capture.
When it exists: every run.
Why read it: debug setup, gate, or subprocess failures.
Warning signs: tracebacks, missing command errors, permission errors, or failed external tool calls.

### `gate_results.json`

What it is: structured results for configured gates.
When it exists: every non-dry run with gates.
Why read it: confirm required gates passed and optional gate warnings are understood.
Warning signs: required failures, skipped expected gates, unknown commands, or suspiciously short output.

### `diff_summary.md`

What it is: changed-file and diff summary from the worktree.
When it exists: every non-dry run with a worktree.
Why read it: see what changed before opening individual files.
Warning signs: unexpected files, too many changed files, test weakening, generated noise, or unrelated edits.

### `verifier_result.json`

What it is: deterministic verifier decision and findings.
When it exists: every non-dry run.
Why read it: confirm the run passed required checks.
Warning signs: failed required gates, diff limit violations, forbidden files, human-required paths, reserved artifacts, or test weakening signals.

## Codex Artifacts

### `codex_prompt.md`

Prompt sent to Codex, including task, constraints, selected skill, optional context, and optional explicit memory. Exists only with `--implementer codex`. Read it to confirm Codex saw the right instructions. Watch for missing scope, wrong context, or included memory that should not have been used.

### `codex_stdout.log`

Codex stdout. Exists only with `--implementer codex`. Read it when the implementation is surprising. Watch for claims not backed by gates or verifier artifacts.

### `codex_stderr.log`

Codex stderr. Exists only with `--implementer codex`. Read it for tool failures. Watch for missing executable, auth problems, or command failures.

### `codex_result.json`

Structured Codex result. Exists only with `--implementer codex`. Read it to confirm whether Codex ran. Watch for unavailable Codex, nonzero exit, or timeout.

## Review Artifacts

### `review_bundle.md`

Human review bundle containing task, context pointers, changed files, gates, verifier result, diff summary, checklist, and recommendation. Exists every run. Warning signs are any conservative recommendation other than ready for human review.

### `pr_title.txt`

Draft PR title text. Exists every run. Read it only after the diff is acceptable. Watch for misleading scope.

### `pr_body.md`

Draft PR body text. Exists every run. Read it as a handoff aid, not proof of correctness. Watch for unsupported claims.

### `pr_commands.md`

Suggested manual commands for a human. Exists every run. Agent Loop Factory does not execute them. Watch for commands that do not match the reviewed worktree state.

### `pr_handoff.md`

Local PR handoff summary. Exists every run. Read it before any manual PR work. Watch for warnings or missing prerequisites.

### `pr_handoff_check.md`

Human-readable handoff validation. Exists every run. Warning signs include verifier failure, required gate failure, dirty state surprises, missing origin, or reserved artifact warnings.

### `pr_handoff_check.json`

Structured handoff validation. Exists every run. Use it for exact fields behind `pr_handoff_check.md`. Watch for non-ok status or warnings.

## Advisory Review Artifacts

These exist only when `--advisory-reviewer codex` is requested. They are receipts, not authority. Advisory review never changes `verifier_result.json`, never replaces gates, never replaces human review, and must not modify files.

### `advisory_review_prompt.md`

Prompt sent to the reviewer. Read it to confirm the evidence bundle was bounded and that untrusted diffs, logs, issues, memory notes, and generated artifacts were framed as data, not instructions.

### `advisory_review_stdout.log`

Raw reviewer stdout. Preserved even when malformed, prose, truncated, or invalid JSON.

### `advisory_review_stderr.log`

Raw reviewer stderr. Read it for missing Codex, nonzero exit, timeout, or tool errors.

### `advisory_review_result.json`

Process receipt with command, return code, timeout flag, artifact paths, parse status, validation status, and advisory-only invariants.

### `advisory_review.md`

Human-readable advisory findings. If reviewer output was malformed, it includes a visible warning and raw stdout.

### `advisory_review.json`

Structured advisory result. `recommendation` may be `no_concerns`, `review_suggested`, `human_attention_required`, or `reviewer_output_unparseable`. It records parse and validation errors without changing verifier status.

### `advisory_review_rubric.md`

Rubric receipt. Exists only when a human explicitly passes `--reviewer-rubric reviewers/<rubric>.md` with `--advisory-reviewer codex`. It includes the selected rubric contents and notes that automatic rubric selection was false.

### `advisory_review_rubric.json`

Structured rubric receipt. Exists only with an explicit reviewer rubric. It records source path, byte size, validation status, advisory-only status, and `automatic_selection: false`.

## Context Artifacts

### `context_summary.json`

Summary of local context inputs. Exists every run. Watch for missing or unexpected local context.

### `issue_context.md`

Copied local issue context. Exists with `--issue-file`. Watch for stale, oversized, or wrong issue text.

### `ci_context.log`

Copied local CI log context. Exists with `--ci-log-file`. Watch for stale logs or failures unrelated to the task.

### `github_issue_context.md`

Markdown GitHub issue context fetched with `gh`. Exists with `--github-issue`. Watch for wrong repository, wrong issue number, or incomplete issue signal.

### `github_issue_context.json`

Structured GitHub issue context. Exists with `--github-issue`. Watch for fetch failures or unexpected identifiers.

### `github_ci_context.log`

Tail-truncated GitHub CI log fetched with `gh`. Exists with `--github-repo --github-ci-run`. Watch for truncation hiding earlier failures.

### `github_ci_context.json`

Structured GitHub CI run metadata. Exists with `--github-repo --github-ci-run`. Watch for wrong run ID, wrong repo, or failed fetch.

### `github_context_summary.json`

Summary of GitHub context inputs. Exists when GitHub context is used. Watch for missing requested context or fetch errors.

## Memory Artifacts

### `memory_context.md`

Included approved memory content. Exists only with `--memory-file`. Read it to confirm memory was intentionally selected. Watch for stale or irrelevant guidance.

### `memory_context.json`

Structured memory inclusion metadata. Exists only with `--memory-file`. Watch for unexpected paths or hygiene failures.

### `memory_proposal.md`

Advisory proposed memory from the run. Exists every run. Read it after reviewing the actual result. Watch for generic, incorrect, or over-broad lessons.

### `memory_proposal.json`

Structured memory proposal. Exists every run. Use it for exact proposed destination and facts. Watch for proposals unsupported by artifacts.

## Task/Skill Artifacts

### `task_spec.md`

Effective task body. Exists every run. Read it to confirm the run used the intended task and scope. Watch for missing allowed or forbidden file rules when they were expected.

### `skill.md`

Selected local skill. Exists with `--skill`. Read it to confirm the right playbook was used. Watch for stale or task-mismatched instructions.

## Reserved Artifact Rule

Target repositories must not create files with Agent Loop Factory artifact names such as `run_report.md`, `gate_results.json`, `verifier_result.json`, `review_bundle.md`, `pr_body.md`, `memory_proposal.md`, or advisory review receipt names including `advisory_review_rubric.md` and `advisory_review_rubric.json`. Those names are reserved for loop receipts. Creating them inside the target repo could spoof or confuse review artifacts, so the verifier treats reserved artifact touches as unsafe.
