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

## Current Capabilities

- Manual CLI-triggered runs.
- Isolated git worktree per run.
- Inline tasks with `--task`.
- Markdown task specs with `--task-file`.
- Task spec allowed/forbidden file guardrails.
- Explicit local skills with `--skill`.
- Safe default implementer `none`.
- Optional one-shot Codex implementer with `--implementer codex`.
- Configured string or named gates.
- Required and optional gate results.
- Deterministic verifier for gates, diff size, changed files, human-required paths, task guardrails, reserved artifacts, and simple test weakening signals.
- Run artifacts under `.agent/runs/<run_id>/`.
- Human review boundary after every run.

## Next Recommended Milestone

v7 human review bundle.

Generate:

```text
.agent/runs/<run_id>/review_bundle.md
```

Include:

- task summary
- skill used
- changed files
- gate results
- verifier result
- diff summary
- human review checklist
- recommended human decision

The bundle should make review easier without changing runtime autonomy. It should not merge, deploy, publish, open PRs, or approve its own work.

## Future Milestones

- v8 draft PR support, no auto-merge
- v9 GitHub issue / CI trigger support
- v10 optional LLM reviewer
- v11 scheduler / recurring runs
- v12 multi-agent or parallel execution

These are planned milestones. They are not implemented in v6.1.

## Explicit Non-Goals

Current Agent Loop Factory does not provide:

- autonomous operation
- production readiness
- auto-merge
- auto-deploy
- GitHub integration
- PR creation
- scheduler support
- parallel agents
- LLM reviewer
- Docker sandboxing
- GitHub Actions workflows
- MCP/connectors
- skill auto-selection
- skill marketplace
- release publishing

The intended boundary is supervised, local, deterministic, and human-in-the-loop.
