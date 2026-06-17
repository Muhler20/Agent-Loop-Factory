# agent-loop-factory

`agent-loop-factory` is a local control loop for supervised software-factory runs. It is the orchestrator that will eventually run agentic implementation loops against target repositories.

It is not the target app being modified. It is not autonomous yet. v0 does not call LLMs, push branches, merge code, deploy, open PRs, or listen for webhooks.

## Run

```bash
python scripts/run_agent_loop.py --task "test task description"
```

Dry-run creates the run record and planned artifacts without creating a git worktree or running gates:

```bash
python scripts/run_agent_loop.py --task "test task description" --dry-run
```

Each run writes:

- `.agent/runs/<run_id>/run_report.md`
- `.agent/runs/<run_id>/gate_results.json`
- `.agent/runs/<run_id>/stdout.log`
- `.agent/runs/<run_id>/stderr.log`
- `.agent/runs/<run_id>/diff_summary.md`

The orchestrator also updates `PROGRESS.md`.

## Config

Edit `.agent/config.yaml` to point at a future target repo:

```yaml
target_repo_path: "../some-target-repo"
worktree_base_path: "../agent-worktrees"
```

Default gates are detected from the target repo:

- Node/TypeScript: `npm test`, `npm run lint`, `npm run typecheck`
- Python: `pytest`, `ruff check .`, `mypy .`

Unavailable commands are warnings in the run report, not crashes.

## Safety Limits

v0 keeps hard limits in config:

- `max_iterations`
- `max_changed_files`
- `max_diff_lines`
- `allowed_commands`
- `human_required_paths`
- `auto_merge: false`
- `auto_deploy: false`

Paths listed in `human_required_paths` are reserved for human approval in future versions.

## Roadmap

- v1: add Codex as the implementer at the TODO in `orchestrator.py`
- v2: add a verifier agent
- v3: add Docker build and Docker Compose gates
- v4: add draft PR creation only
- v5: add GitHub Actions or webhook triggers
- v6: add parallel planner, triage, implementer, and verifier agents
