# Roadmap

This roadmap distinguishes implemented capabilities from planned work. Planned milestones are not current features.

## Completed Milestones

- v0 deterministic loop skeleton
- v0.5 sample target repo smoke test
- v1 optional Codex implementer
- v2 deterministic verifier
- v2.5 constraints and task docs
- v3 task spec file support
- v4 task spec guardrails
- v5 local skills
- v6 named gates and diff reporting
- v6.1 docs and roadmap cleanup
- v7 human review bundle
- v8 draft PR handoff package
- v8.1 PR handoff validation
- v9 issue / CI context intake
- v9.1 config and safety hardening with repository test CI

## Current Capabilities

- Manual CLI-triggered runs.
- Isolated git worktree per run.
- Inline tasks with `--task`.
- Markdown task specs with `--task-file`.
- Task spec allowed/forbidden file guardrails.
- Explicit local skills with `--skill`.
- Optional local issue and CI log context intake with `--issue-file` and `--ci-log-file`.
- Safe default implementer `none`.
- Optional one-shot Codex implementer with `--implementer codex`.
- Configured string or named gates.
- Required and optional gate results.
- Deterministic verifier for gates, diff size, changed files, human-required paths, task guardrails, reserved artifacts, and simple test weakening signals.
- Repository CI that runs only the unittest suite.
- Human-readable `review_bundle.md` with checklist and conservative recommendation.
- Local draft PR handoff artifacts: `pr_title.txt`, `pr_body.md`, `pr_commands.md`, `pr_handoff.md`, `pr_handoff_check.md`, and `pr_handoff_check.json`.
- Run artifacts under `.agent/runs/<run_id>/`.
- Human review boundary after every run.

## Next Recommended Milestone

v10 optional explicit local GitHub fetch using `gh`, read-only, no PR creation.

## Future Milestones

- v10 optional explicit local GitHub fetch using gh, read-only, no PR creation
- v11 optional LLM reviewer or PR review integration
- v12 scheduler / recurring runs
- v13 multi-agent or parallel execution

These are planned milestones. They are not implemented in v9.1.

## Explicit Non-Goals

Current Agent Loop Factory does not provide:

- autonomous operation
- production readiness
- auto-merge
- auto-deploy
- GitHub integration
- automatic issue or CI fetching
- PR creation
- scheduler support
- parallel agents
- LLM reviewer
- Docker sandboxing
- GitHub Actions workflows that run Agent Loop Factory or other automation
- MCP/connectors
- skill auto-selection
- skill marketplace
- release publishing

The intended boundary is supervised, local, deterministic, and human-in-the-loop.
