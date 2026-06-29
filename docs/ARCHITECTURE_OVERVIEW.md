# Architecture Overview

## Purpose

Agent Loop Factory is a supervised local control loop for software-agent coding runs. Its job is to make one agent attempt auditable: isolate the target repo in a git worktree, run configured gates, verify the diff and scope deterministically, write artifacts, and stop for human review.

## High-Level Flow

1. A human starts a run from the CLI.
2. The orchestrator reads `.agent/config.yaml`.
3. The task is loaded from `--task` or `--task-file`.
4. An explicitly selected local skill is loaded, if provided.
5. A run directory is created under `.agent/runs/<run_id>/`.
6. A git worktree is created under the configured worktree base path.
7. The selected implementer runs. The default is `none`; `codex` runs once when requested.
8. Configured gates run in the worktree.
9. The deterministic verifier inspects gates, diff size, changed files, task guardrails, sensitive paths, and test weakening signals.
10. Artifacts and local draft PR handoff files are written, progress/state files are updated, and the loop stops.

## Core Components

### Manual Trigger

Runs start with `python3 scripts/run_agent_loop.py`. There is no scheduler, webhook listener, GitHub integration, or background daemon.

### Orchestrator

The orchestrator coordinates a single run: config loading, task loading, worktree creation, implementer execution, gates, verification, artifact writing, and progress updates.

### Config

`.agent/config.yaml` defines the target repo path, worktree base path, gate allowlist, gates, implementer defaults, diff limits, and human-required paths.

### Task Spec

An inline `--task` provides a simple task body. A Markdown `--task-file` provides a structured job order and can include `Allowed files` and `Forbidden files` guardrails.

### Skill

A skill is an explicitly selected local playbook at `skills/<skill_name>/SKILL.md`. It is copied into the run artifacts and included in the Codex prompt. Skills are not auto-selected or fetched remotely.

### Worktree Isolation

Each non-dry run creates a new git worktree under `worktree_base_path`. The target repo's main checkout is not edited directly.

### Implementer

`--implementer none` is the safe default and makes no code changes. `--implementer codex` runs `codex exec` once inside the worktree and records the prompt, stdout, stderr, and result JSON.

### Gates

Gates are configured commands that must be present in `allowed_commands`. They can be string commands or named objects with `name`, `command`, and `required`. Required failures fail the run; optional failures become warnings.

### Verifier

The verifier is deterministic. It checks required gate results, changed file count, diff line count, human-required paths, reserved artifact filenames, task allowed/forbidden file rules, and simple test weakening signals.

### Artifacts

Run artifacts are written under `.agent/runs/<run_id>/`, including `run_report.md`, `review_bundle.md`, `pr_title.txt`, `pr_body.md`, `pr_commands.md`, `pr_handoff.md`, `gate_results.json`, `verifier_result.json`, logs, `diff_summary.md`, and `task_spec.md`. Skill and Codex artifacts are written only when those features are used.

### Progress and State Memory

`.agent/state.json` stores the last run id and run outcomes. `PROGRESS.md` gives a human-readable current status and next action.

### Human Review Boundary

The loop stops after artifacts are written. `review_bundle.md` collects the diff summary, gates, verifier result, task guardrails, and checklist for the human decision. The draft PR handoff files provide a local title, body, and suggested manual commands. They are review aids only; Agent Loop Factory does not commit, push, open PRs, approve, merge, or deploy.

## Current Implemented System Through v7

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

## Intentionally Not Implemented Yet

Agent Loop Factory does not currently implement scheduler support, GitHub webhooks, GitHub Actions integration, PR creation, Docker sandboxing, an LLM verifier, MCP/connectors, parallel agents, skill auto-selection, auto-merge, auto-deploy, publishing, or release creation.

## Safety Model

The safety model is local, supervised, and deterministic:

- Manual runs only.
- Isolated git worktree per run.
- Default no-op implementer.
- Explicit opt-in for Codex.
- Gate commands limited by `allowed_commands`.
- Sensitive paths flagged through `human_required_paths`.
- Task file guardrails for allowed and forbidden files.
- Hard limits for changed files and diff lines.
- Deterministic verifier decides pass/fail.
- Human review before any merge, deploy, release, or external publication.
- Draft PR handoff is local text generation only.

## Future Roadmap

- v8.1 optional explicit local gh draft PR creation, still no auto-merge
- v9 GitHub issue / CI trigger support
- v10 optional LLM reviewer or PR review integration
- v11 scheduler / recurring runs
- v12 multi-agent or parallel execution

These are planned milestones, not current capabilities.

## Summary

Agent Loop Factory is a local, supervised, deterministic control loop that makes coding-agent worktree runs reviewable before any human chooses to merge or ship them.
