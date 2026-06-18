# agent-loop-factory

`agent-loop-factory` is a local control loop for supervised software-factory runs. It is the orchestrator that will eventually run agentic implementation loops against target repositories.

It is not the target app being modified. v1 can optionally call Codex once inside a created worktree, then runs gates and stops. By default it does not call LLMs, push branches, merge code, deploy, open PRs, or listen for webhooks.

## v1

v1 adds one optional implementer worker:

- `--implementer none` is the default and keeps the existing safe behavior.
- `--implementer codex` runs `codex exec` once inside the created worktree.
- Gates run after the implementer attempt.
- Artifacts record the prompt, Codex output, gate results, diff summary, and run report.

## Run

```bash
python3 scripts/run_agent_loop.py --task "test task description"
```

This is equivalent to:

```bash
python3 scripts/run_agent_loop.py --task "test task description" --implementer none
```

Run with Codex:

```bash
python3 scripts/run_agent_loop.py --task "fix the failing test" --implementer codex
```

Dry-run creates the run record and planned artifacts without creating a git worktree or running gates:

```bash
python3 scripts/run_agent_loop.py --task "test task description" --dry-run
```

Each run writes:

- `.agent/runs/<run_id>/run_report.md`
- `.agent/runs/<run_id>/gate_results.json`
- `.agent/runs/<run_id>/stdout.log`
- `.agent/runs/<run_id>/stderr.log`
- `.agent/runs/<run_id>/diff_summary.md`

When `--implementer codex` is used, the run also writes:

- `.agent/runs/<run_id>/codex_prompt.md`
- `.agent/runs/<run_id>/codex_stdout.log`
- `.agent/runs/<run_id>/codex_stderr.log`
- `.agent/runs/<run_id>/codex_result.json`

The orchestrator also updates `PROGRESS.md`.

## v1 Smoke Test

Create a tiny target repo with one intentionally failing unittest next to this repo:

```bash
python3 scripts/create_sample_target_repo.py --failing
```

Point `.agent/config.yaml` at it and use the stdlib unittest gate:

```yaml
target_repo_path: "../sample-target-repo"
worktree_base_path: "../agent-worktrees"
allowed_commands:
  - "python3 -m unittest discover -s tests"
gates:
  - "python3 -m unittest discover -s tests"
```

Run the loop without `--dry-run`:

```bash
python3 scripts/run_agent_loop.py --task "Fix the failing sample_math add test." --implementer codex
```

Confirm the output mentions a `run_id`, then check:

```bash
ls ../agent-worktrees
ls .agent/runs/<run_id>/{run_report.md,gate_results.json,stdout.log,stderr.log,diff_summary.md,codex_prompt.md,codex_stdout.log,codex_stderr.log,codex_result.json}
```

Gates run after Codex. If Codex is unavailable or fails, `codex_result.json` and `run_report.md` include the error and the loop stops without pushing, merging, deploying, or opening a PR.

## Config

Edit `.agent/config.yaml` to point at a future target repo:

```yaml
target_repo_path: "../some-target-repo"
worktree_base_path: "../agent-worktrees"
implementer: "none"
codex_command: "codex"
codex_exec_args: []
```

Default gates are detected from the target repo:

- Node/TypeScript: `npm test`, `npm run lint`, `npm run typecheck`
- Python: `pytest`, `ruff check .`, `mypy .`

For a stdlib-only Python repo, set `allowed_commands` and `gates` to `python3 -m unittest discover -s tests`.

Unavailable commands are warnings in the run report, not crashes.

## Safety Boundaries

v1 keeps hard limits in config and repeats them in the Codex prompt:

- `max_iterations`
- `max_changed_files`
- `max_diff_lines`
- `allowed_commands`
- `human_required_paths`
- `implementer: "none"`
- `auto_merge: false`
- `auto_deploy: false`

Codex is told to make the smallest change, avoid weakening tests, avoid sensitive paths without approval, stop after editing files, and not claim success. Gates decide success.

## Troubleshooting

If Codex is not installed or not on `PATH`, runs with `--implementer codex` write `codex unavailable` into:

- `.agent/runs/<run_id>/codex_result.json`
- `.agent/runs/<run_id>/codex_stderr.log`
- `.agent/runs/<run_id>/run_report.md`

Set `codex_command` if your executable has a different name or path.

## Roadmap

- v2: add a verifier agent
- v3: add Docker build and Docker Compose gates
- v4: add draft PR creation only
- v5: add GitHub Actions or webhook triggers
- v6: add parallel planner, triage, implementer, and verifier agents
