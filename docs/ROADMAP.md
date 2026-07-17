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
- v10 reviewable memory proposals
- v10.1 human-approved memory registry
- v10.2 explicit memory inclusion in prompts
- v10.3 memory hygiene checks
- v11 read-only GitHub issue / CI fetch using gh
- v11.1 operator documentation consolidation

## Current Capabilities

- Manual CLI-triggered runs.
- Isolated git worktree per run.
- Inline tasks with `--task`.
- Markdown task specs with `--task-file`.
- Task spec allowed/forbidden file guardrails.
- Explicit local skills with `--skill`.
- Optional local issue and CI log context intake with `--issue-file` and `--ci-log-file`.
- Optional explicit read-only GitHub issue / CI context intake with `--github-issue`, `--github-repo`, and `--github-ci-run`.
- Safe default implementer `none`.
- Optional one-shot Codex implementer with `--implementer codex`.
- Configured string or named gates.
- Required and optional gate results.
- Deterministic verifier for gates, diff size, changed files, human-required paths, task guardrails, reserved artifacts, and simple test weakening signals.
- Repository CI that runs only the unittest suite.
- Human-readable `review_bundle.md` with checklist and conservative recommendation.
- Local draft PR handoff artifacts: `pr_title.txt`, `pr_body.md`, `pr_commands.md`, `pr_handoff.md`, `pr_handoff_check.md`, and `pr_handoff_check.json`.
- Reviewable memory proposal artifacts: `memory_proposal.md` and `memory_proposal.json`.
- Human-approved memory registry skeleton under `memory/`.
- Memory registry validation with `--check-memory`, including active memory metadata and section hygiene.
- Explicit human-selected memory prompt inclusion with `--memory-file`.
- Run artifacts under `.agent/runs/<run_id>/`.
- Human review boundary after every run.

## Next Recommended Milestone

v12 optional advisory reviewer. The reviewer is advisory only and does not replace configured gates, deterministic verifier checks, or human review.

## Future Milestones

- v12 optional advisory reviewer
- v12.1 reviewer rubric files
- v13 scheduler / recurring reporting only
- v13.1 scheduled task queue
- v14 multi-agent / parallel worktrees
- v15 explicit draft PR creation
- v16 explicit GitHub issue update/comment
- v17 dependency/update loops
- v18 policy packs / repo profiles
- v19 controlled memory suggestion/retrieval
- v20 narrow managed autonomous mode

These are planned milestones except completed items listed above.

## Explicit Non-Goals

Current Agent Loop Factory does not provide:

- autonomous operation
- production readiness
- auto-merge
- auto-deploy
- GitHub writes
- automatic memory writes to durable project rules
- automatic memory search, ranking, retrieval, or selection
- automatic issue or CI discovery
- PR creation
- scheduler support
- parallel agents
- advisory reviewer
- Docker sandboxing
- GitHub Actions workflows that run Agent Loop Factory or other automation
- MCP/connectors
- skill auto-selection
- skill marketplace
- release publishing

The intended boundary is supervised, local, deterministic, and human-in-the-loop.
