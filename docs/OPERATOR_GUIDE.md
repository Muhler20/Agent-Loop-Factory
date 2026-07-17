# Operator Guide

## What Agent Loop Factory Is

Agent Loop Factory is a local supervised control loop for software-agent runs. It is not the target application and it is not autonomous.

Runs are manually triggered. Agents may write code in an isolated worktree, but the loop controls the process: read inputs, create the worktree, run gates, run deterministic verification, write artifacts, update local progress, and stop.

Humans approve durable or irreversible actions such as commits, pushes, PRs, merges, deployments, memory changes, and any sensitive path changes.

## What It Does Not Do

- does not auto-push
- does not auto-merge
- does not auto-deploy
- does not auto-create PRs
- does not write to GitHub
- does not schedule runs
- does not auto-select memory
- does not auto-update memory
- does not replace human review

## Standard Preflight

```bash
git status
python3 -m unittest discover -s tests
python3 scripts/run_agent_loop.py --check-memory
```

When using GitHub context, also check local auth first:

```bash
gh auth status
```

Prefer a read-only-scoped GitHub token or account when practical.

## Choosing Inputs

- `--task`: use for a short inline task when file guardrails are not needed.
- `--task-file`: use for normal runs; supports structured scope, allowed files, forbidden files, gates, and stop condition.
- `--issue-file`: attach a local issue or bug report as supporting evidence.
- `--ci-log-file`: attach a local CI log as supporting evidence.
- `--github-issue`: fetch one explicit GitHub issue as read-only context with `gh`.
- `--github-repo + --github-ci-run`: fetch one explicit GitHub Actions run and tail-truncated log as read-only context with `gh`.
- `--skill`: include one explicit local playbook from `skills/<name>/SKILL.md`.
- `--memory-file`: include one explicit human-approved memory file from `memory/`; repeat when needed.
- `--implementer codex`: ask Codex to make one attempt in the worktree.
- `--dry-run`: validate the run setup without creating a worktree or running gates.
- `--check-memory`: validate the memory registry without creating a run or changing progress.

## Recommended Run Patterns

Dry-run sanity check:

```bash
python3 scripts/run_agent_loop.py --task-file tasks/fix-sample-add.md --dry-run
```

Local task file plus skill:

```bash
python3 scripts/run_agent_loop.py --task-file tasks/fix-sample-add.md --skill failing-test-fix
```

Local issue and CI context:

```bash
python3 scripts/run_agent_loop.py \
  --task-file tasks/fix-sample-add.md \
  --issue-file examples/issues/fix-sample-add.md \
  --ci-log-file examples/ci/failing-unit-test.log
```

Read-only GitHub CI context:

```bash
python3 scripts/run_agent_loop.py \
  --task-file tasks/fix-sample-add.md \
  --github-repo owner/repo \
  --github-ci-run 123456789
```

Explicit approved memory inclusion:

```bash
python3 scripts/run_agent_loop.py \
  --task-file tasks/fix-sample-add.md \
  --memory-file memory/path/to/approved-memory.md
```

Codex implementation run:

```bash
python3 scripts/run_agent_loop.py \
  --task-file tasks/fix-sample-add.md \
  --skill failing-test-fix \
  --implementer codex
```

Review-only, no implementer:

```bash
python3 scripts/run_agent_loop.py --task-file tasks/fix-sample-add.md --implementer none
```

## Reviewing A Run

Review artifacts in this order:

1. `run_report.md`
2. `gate_results.json`
3. `verifier_result.json`
4. `diff_summary.md`
5. `review_bundle.md`
6. `pr_handoff_check.md`
7. `pr_body.md` / `pr_handoff.md`
8. `memory_proposal.md`
9. context artifacts, if present

## Deciding What To Do After A Run

`ready_for_human_review` means the loop found no deterministic blocker. A human still reviews the diff, gates, verifier result, and task scope before any commit, PR, merge, or deploy.

`manual_review_required` means gates or verifier checks need human judgment. Inspect the warning, then either accept the risk, ask for rework, or abandon the run.

Reject or rework when required gates fail, the verifier fails, task scope is violated, tests are weakened, human-required paths are touched without approval, or reserved artifacts are changed.

Accept memory proposals only after a human edits or approves them. Per-run proposals are advisory and must not be copied blindly into durable memory.

Rerun when the task or context was wrong, a gate had an environmental failure, or the implementation needs another supervised attempt.

Abandon a run when the task is obsolete, too broad, unsafe, or better handled manually.

## Cleanup After Smoke Tests

After smoke tests, restore the clean starter state.

`.agent/state.json`:

```json
{
  "last_run_id": null,
  "runs": []
}
```

`PROGRESS.md` should not contain local smoke-test run IDs. Clean starter shape:

```markdown
# Progress

## Current Goal

None.

## Last Run

None.

## In Progress

Manual supervised loop skeleton.

## Blockers

None.

## Next Action

Choose the first supervised task.

## Decisions

- v0 is manual and deterministic.
- v1 can call Codex only when explicitly requested.
- The default implementer is none.
- This project does not push, merge, deploy, or open PRs.
```

Also make sure `.agent/config.yaml` is not still pointed at the sample target repo.

## Safety Checklist

- working tree clean before run
- task scope clear
- gates configured
- memory explicitly selected only if needed
- GitHub context read-only
- verifier ok
- no human-required paths touched
- no tests weakened
- no reserved artifacts touched
- human reviews before PR, merge, or deploy
