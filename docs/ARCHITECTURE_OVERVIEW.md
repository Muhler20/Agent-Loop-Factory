# Architecture Overview

## Purpose

Agent Loop Factory is a supervised local control loop for software-agent coding runs. Its job is to make one agent attempt auditable: isolate the target repo in a git worktree, run configured gates, verify the diff and scope deterministically, write artifacts, and stop for human review.

## High-Level Flow

1. A human starts a run from the CLI.
2. The orchestrator reads `.agent/config.yaml`.
3. The task is loaded from `--task` or `--task-file`.
4. Optional local issue and CI log context files are loaded.
5. Explicit memory files are validated if `--memory-file` is provided.
6. An explicitly selected local skill is loaded, if provided.
7. A run directory is created under `.agent/runs/<run_id>/`.
8. Explicit GitHub issue / CI context is fetched with read-only `gh` commands, if requested.
9. A git worktree is created under the configured worktree base path.
10. The selected implementer runs. The default is `none`; `codex` runs once when requested.
11. Configured gates run in the worktree.
12. The deterministic verifier inspects gates, diff size, changed files, task guardrails, sensitive paths, and test weakening signals.
13. Reviewable memory proposal artifacts are generated from deterministic run facts.
14. Artifacts and local draft PR handoff files are written, progress/state files are updated, and the loop stops.

## Core Components

### Manual Trigger

Runs start with `python3 scripts/run_agent_loop.py`. There is no scheduler, webhook listener, background daemon, GitHub write path, or automatic GitHub discovery.

### Orchestrator

The orchestrator coordinates a single run: config loading, task loading, worktree creation, implementer execution, gates, verification, artifact writing, and progress updates.

### Config

`.agent/config.yaml` defines the target repo path, worktree base path, gate allowlist, gates, implementer defaults, diff limits, and human-required paths.

### Task Spec

An inline `--task` provides a simple task body. A Markdown `--task-file` provides a structured job order and can include `Allowed files` and `Forbidden files` guardrails.

### Context Intake

`--issue-file` and `--ci-log-file` load optional local UTF-8 text files as supporting evidence. They are copied to run artifacts and included in the Codex prompt when Codex is used. They do not replace the task spec. Local and GitHub context for the same slot cannot be combined.

`--github-issue owner/repo#number` and `--github-repo owner/repo --github-ci-run number` fetch explicit GitHub issue and Actions run context using only `gh issue view owner/repo#number`, `gh run view run_id --repo owner/repo`, and `gh run view run_id --repo owner/repo --log`. GitHub is an input source only. CI logs are tail-truncated at 50 KB. Local `gh` auth may have write permissions, so a read-only-scoped token or account is preferred when possible.

### Skill

A skill is an explicitly selected local playbook at `skills/<skill_name>/SKILL.md`. It is copied into the run artifacts and included in the Codex prompt. Skills are not auto-selected or fetched remotely.

### Memory Context

`--memory-file` is a repeatable CLI flag for explicitly including human-approved Markdown files from `memory/` in the Codex prompt. The loop validates paths, active memory hygiene, and writes `memory_context.md` and `memory_context.json` for the run. It does not search, rank, retrieve, auto-select, auto-apply, or modify memory files. Included memory is guidance only; task specs, constraints, human-required paths, gates, verifier rules, and approval boundaries still win.

### Worktree Isolation

Each non-dry run creates a new git worktree under `worktree_base_path`. The target repo's main checkout is not edited directly.

### Implementer

`--implementer none` is the safe default and makes no code changes. `--implementer codex` runs `codex exec` once inside the worktree and records the prompt, stdout, stderr, and result JSON.

### Gates

Gates are configured commands that must be present in `allowed_commands`. They can be string commands or named objects with `name`, `command`, and `required`. Required failures fail the run; optional failures become warnings.

### Verifier

The verifier is deterministic. It checks required gate results, changed file count, diff line count, human-required paths, reserved artifact filenames, task allowed/forbidden file rules, and simple test weakening signals.

### Artifacts

Run artifacts are written under `.agent/runs/<run_id>/`, including `run_report.md`, `review_bundle.md`, `pr_title.txt`, `pr_body.md`, `pr_commands.md`, `pr_handoff.md`, `pr_handoff_check.md`, `pr_handoff_check.json`, `memory_proposal.md`, `memory_proposal.json`, `gate_results.json`, `verifier_result.json`, logs, `diff_summary.md`, `task_spec.md`, and `context_summary.json`. `issue_context.md`, `ci_context.log`, `github_issue_context.md`, `github_issue_context.json`, `github_ci_context.log`, `github_ci_context.json`, `github_context_summary.json`, `memory_context.md`, and `memory_context.json` are written only when their matching context flags are provided. Skill and Codex artifacts are written only when those features are used.

### Memory Proposals

Memory proposals are deterministic, advisory run artifacts. They may suggest reusable lessons and destinations for human review, but they do not automatically modify `memory/`, `AGENTS.md`, `CONSTRAINTS.md`, skills, docs, task specs, or durable project rule files.

### Memory Registry

`memory/` is the durable registry for human-approved lessons. Humans may copy or edit accepted per-run proposals into the registry with provenance. `--check-memory` validates the registry shape, active memory metadata, and required sections. Stale memory, duplicate active titles, deprecated placement, and small conservative conflict signals warn without failing. `--memory-file` can include named registry files in a run, but only when a human explicitly provides the paths.

### Progress and State Memory

`.agent/state.json` stores the last run id and run outcomes. `PROGRESS.md` gives a human-readable current status and next action.

### Human Review Boundary

The loop stops after artifacts are written. `review_bundle.md` collects the diff summary, gates, verifier result, task guardrails, and checklist for the human decision. The draft PR handoff files provide a local title, body, suggested manual commands, and local-only handoff validation status. They are review aids only; Agent Loop Factory does not commit, push, open PRs, approve, merge, or deploy.

## Current Implemented System Through v11

- v0 deterministic loop skeleton
- v0.5 sample target repo smoke test
- v1 optional Codex implementer
- v2 deterministic verifier
- v2.5 constraints and task docs
- v3 task spec file support
- v4 task spec guardrails
- v5 local skills
- v6 named gates and diff reporting
- v7 human review bundle
- v8 local draft PR handoff package
- v8.1 PR handoff validation
- v9 local issue / CI context intake
- v9.1 config and safety hardening with repository test CI
- v10 reviewable memory proposals
- v10.1 human-approved memory registry
- v10.2 explicit memory inclusion in prompts
- v10.3 memory hygiene checks
- v11 explicit read-only GitHub issue / CI context intake using `gh`

## Intentionally Not Implemented Yet

Agent Loop Factory does not currently implement scheduler support, GitHub webhooks, GitHub Actions changes, automatic issue or CI discovery, GitHub writes, PR creation, Docker sandboxing, an LLM verifier, MCP/connectors, parallel agents, skill auto-selection, automatic memory writes, automatic memory search/ranking/retrieval/selection, auto-merge, auto-deploy, publishing, or release creation.

## Safety Model

The safety model is local, supervised, and deterministic:

- Manual runs only.
- Isolated git worktree per run.
- Default no-op implementer.
- Explicit opt-in for Codex.
- Explicit opt-in for read-only GitHub context.
- Gate commands limited by `allowed_commands`.
- Sensitive paths flagged through `human_required_paths`.
- Task file guardrails for allowed and forbidden files.
- Hard limits for changed files and diff lines.
- Deterministic verifier decides pass/fail.
- Human review before any merge, deploy, release, or external publication.
- Draft PR handoff is local text generation only.
- No GitHub comments, labels, edits, workflow reruns, pushes, merges, deploys, or releases.
- Memory proposals are advisory and require human approval before any durable rule change.
- Memory registry entries are human-approved, hygiene-checked, and loaded into prompts only when explicitly named with `--memory-file`.

## Future Roadmap

- v12 optional LLM reviewer / PR review integration
- v13 scheduler / recurring runs
- v14 multi-agent / parallel execution
- v15 optional draft PR creation with explicit human command/flag

These are planned milestones, not current capabilities.

## Summary

Agent Loop Factory is a local, supervised, deterministic control loop that makes coding-agent worktree runs reviewable before any human chooses to merge or ship them.
