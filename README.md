# agent-loop-factory

`agent-loop-factory` is a local control loop for supervised software-factory runs. It is the orchestrator that will eventually run agentic implementation loops against target repositories.

It is not the target app being modified. v2.5 can optionally call Codex once inside a created worktree, runs gates, runs a deterministic verifier, then stops. It is still manual and local. By default it does not call LLMs, push branches, merge code, deploy, open PRs, or listen for webhooks.

## v1

v1 adds one optional implementer worker:

- `--implementer none` is the default and keeps the existing safe behavior.
- `--implementer codex` runs `codex exec` once inside the created worktree.
- Gates run after the implementer attempt.
- Artifacts record the prompt, Codex output, gate results, diff summary, and run report.

## v2

v2 adds a deterministic verifier after gates. It does not use an LLM reviewer.

The verifier checks:

- gate results
- changed file count against `max_changed_files`
- diff line count against `max_diff_lines`
- touched `human_required_paths`
- simple test weakening signals, including deleted files under `tests/`, removed assertions in test files, and added skip markers

Each run writes `.agent/runs/<run_id>/verifier_result.json` with the verifier decision, reasons, warnings, changed files, diff size, human-required paths touched, and whether tests appear weakened or deleted.

The final run status is passed only when gates and the verifier both pass. v2 keeps verification deterministic.

## v2.5

v2.5 adds lightweight repo guidance, not a platform:

- `CONSTRAINTS.md` stores stable project constraints future runs should read.
- `docs/LOOP_SELECTION.md` explains which tasks should become loops.
- `docs/TASK_SPEC_TEMPLATE.md` is a small template for future task specs.
- Codex implementer prompts include `AGENTS.md` and `CONSTRAINTS.md` when those files exist.

This is not a scheduler, PR bot, swarm, autonomous deployment system, Docker setup, GitHub Actions workflow, MCP connector, skills system, or LLM verifier.

## v3

v3 adds structured task specs: written Markdown job orders that can be passed with `--task-file`. Inline `--task` still works, and every run writes the task order to `.agent/runs/<run_id>/task_spec.md`.

Use `docs/TASK_SPEC_TEMPLATE.md` for new specs. A sample is available at `tasks/fix-sample-add.md`.

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

Run from a task spec:

```bash
python3 scripts/run_agent_loop.py --task-file tasks/fix-sample-add.md --implementer codex
```

Dry-run creates the run record and planned artifacts without creating a git worktree or running gates:

```bash
python3 scripts/run_agent_loop.py --task "test task description" --dry-run
```

Each run writes:

- `.agent/runs/<run_id>/run_report.md`
- `.agent/runs/<run_id>/gate_results.json`
- `.agent/runs/<run_id>/verifier_result.json`
- `.agent/runs/<run_id>/stdout.log`
- `.agent/runs/<run_id>/stderr.log`
- `.agent/runs/<run_id>/diff_summary.md`
- `.agent/runs/<run_id>/task_spec.md`

When `--implementer codex` is used, the run also writes:

- `.agent/runs/<run_id>/codex_prompt.md`
- `.agent/runs/<run_id>/codex_stdout.log`
- `.agent/runs/<run_id>/codex_stderr.log`
- `.agent/runs/<run_id>/codex_result.json`

The orchestrator also updates `PROGRESS.md`.

## v2.5 Smoke Test

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

Or use the sample written job order:

```bash
python3 scripts/run_agent_loop.py --task-file tasks/fix-sample-add.md --implementer codex
```

Confirm the output mentions a `run_id`, then check:

```bash
ls ../agent-worktrees
ls .agent/runs/<run_id>/{run_report.md,gate_results.json,verifier_result.json,stdout.log,stderr.log,diff_summary.md,codex_prompt.md,codex_stdout.log,codex_stderr.log,codex_result.json}
grep -F "# CONSTRAINTS.md" .agent/runs/<run_id>/codex_prompt.md
grep -F "Keep the sample change small" .agent/runs/<run_id>/codex_prompt.md
```

Gates run after Codex, then the deterministic verifier runs. If Codex is unavailable, gates fail, or the verifier fails, the JSON artifacts and `run_report.md` include the reason and the loop stops without pushing, merging, deploying, or opening a PR.

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

v3 keeps hard limits in config, enforces them in the verifier, and repeats them in the Codex prompt:

- `max_iterations`
- `max_changed_files`
- `max_diff_lines`
- `allowed_commands`
- `human_required_paths`
- `implementer: "none"`
- `auto_merge: false`
- `auto_deploy: false`

Codex is told to make the smallest change, avoid weakening tests, avoid sensitive paths without approval, stop after editing files, and not claim success. The prompt also includes the task spec, plus `AGENTS.md` and `CONSTRAINTS.md` when present. Gates plus the deterministic verifier decide success.

## Troubleshooting

If Codex is not installed or not on `PATH`, runs with `--implementer codex` write `codex unavailable` into:

- `.agent/runs/<run_id>/codex_result.json`
- `.agent/runs/<run_id>/codex_stderr.log`
- `.agent/runs/<run_id>/run_report.md`

Set `codex_command` if your executable has a different name or path.

## Roadmap

- v3: manual and local; no scheduler, PR bot, swarm, LLM verifier, Docker, GitHub Actions, draft PRs, push, merge, deploy, publish, MCP, or connectors.
