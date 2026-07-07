# agent-loop-factory

`agent-loop-factory` is a supervised software-agent control loop for local coding-agent runs. It creates an isolated git worktree for a target repository, optionally asks Codex to make one small change, runs configured gates, verifies the resulting diff deterministically, writes audit artifacts, and stops for human review.

It is not an autonomous coding platform. Through v9 it is local, manually triggered, and human-in-the-loop. It does not push, merge, deploy, open PRs, listen for webhooks, run a scheduler, use Docker sandboxing, run parallel agents, auto-select skills, call an LLM verifier, or connect to GitHub/MCP services.

## What It Solves

Agent Loop Factory is for small, repeatable coding tasks where the target repo has runnable checks and a human wants a clear review boundary. It turns a coding-agent attempt into a controlled run with:

- a fresh git worktree
- configured required or optional gates
- deterministic checks on changed files, diff size, task scope, sensitive paths, and test weakening
- run artifacts under `.agent/runs/<run_id>/`
- a progress/state record for manual follow-up

## What It Does Today

Implemented through v9:

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

Current capabilities:

- Manual CLI trigger with `--task` or `--task-file`.
- Safe default implementer: `--implementer none`.
- Optional one-shot Codex implementer: `--implementer codex`.
- Local skill playbooks selected explicitly with `--skill`.
- Optional local issue and CI log context files with `--issue-file` and `--ci-log-file`.
- Git worktree isolation under the configured worktree base path.
- Required and optional named gates.
- Diff summary including tracked stats and untracked files.
- Deterministic verifier results written as JSON.
- Human review boundary after every run.

## How The Loop Works

1. Read `.agent/config.yaml`.
2. Load the inline task or Markdown task spec.
3. Load optional local context files from `--issue-file` and `--ci-log-file`.
4. Load an explicitly selected local skill, if `--skill` is provided.
5. Create `.agent/runs/<run_id>/`.
6. Create a git worktree for the configured target repo.
7. Run the selected implementer. The default `none` makes no code changes; `codex` runs `codex exec` once inside the worktree.
8. Run configured gates from the worktree.
9. Run the deterministic verifier.
10. Write audit artifacts and update `.agent/state.json` and `PROGRESS.md`.
11. Stop for human review.

## Basic Dry Run

From the repo root:

```bash
cd ~/coding-projects/agent-loop-factory
python3 scripts/run_agent_loop.py --task "test task description" --dry-run
```

This creates a run record and planned artifacts without creating a git worktree or executing gates.

## Common Commands

Inline task with the safe default implementer:

```bash
python3 scripts/run_agent_loop.py --task "Fix the failing test."
```

The same command with the default made explicit:

```bash
python3 scripts/run_agent_loop.py --task "Fix the failing test." --implementer none
```

Task spec file:

```bash
python3 scripts/run_agent_loop.py --task-file tasks/fix-sample-add.md
```

Task spec with a local skill:

```bash
python3 scripts/run_agent_loop.py --task-file tasks/fix-sample-add.md --skill failing-test-fix
```

Task spec with local issue and CI context:

```bash
python3 scripts/run_agent_loop.py \
  --task-file tasks/fix-sample-add.md \
  --issue-file examples/issues/fix-sample-add.md \
  --ci-log-file examples/ci/failing-unit-test.log \
  --skill failing-test-fix
```

Task spec with the Codex implementer:

```bash
python3 scripts/run_agent_loop.py --task-file tasks/fix-sample-add.md --skill failing-test-fix --implementer codex
```

## Local Issue / CI Context

`--issue-file PATH` and `--ci-log-file PATH` attach local text files as supporting evidence for the run. They do not replace the task spec, and they do not expand scope. The task spec, allowed files, forbidden files, constraints, gates, and human-review rules still control the run.

Context intake is local-only. Agent Loop Factory reads the provided files from disk as UTF-8 text, validates that they are non-empty files under a fixed size limit, writes run artifacts, and does not contact GitHub, GitHub Actions, webhooks, `gh`, or any network service.

## Sample Target Repo Smoke Test

Create a tiny failing target repo next to this repo:

```bash
cd ~/coding-projects/agent-loop-factory
python3 scripts/create_sample_target_repo.py --failing
```

Temporarily point `.agent/config.yaml` at it:

```yaml
target_repo_path: "../sample-target-repo"
worktree_base_path: "../agent-worktrees"
allowed_commands:
  - "python3 -m unittest discover -s tests"
gates:
  - name: unit tests
    command: "python3 -m unittest discover -s tests"
    required: true
```

Run the proven sample task:

```bash
python3 scripts/run_agent_loop.py \
  --task-file tasks/fix-sample-add.md \
  --skill failing-test-fix \
  --implementer codex
```

See [docs/SMOKE_TEST_WALKTHROUGH.md](docs/SMOKE_TEST_WALKTHROUGH.md) for artifact checks and cleanup commands.

## Task Specs

A task spec is a Markdown job order passed with `--task-file`. Inline `--task` still works, but file-backed specs enable guardrails.

Use [docs/TASK_SPEC_TEMPLATE.md](docs/TASK_SPEC_TEMPLATE.md) as the starting shape:

```markdown
## Goal

## Scope

## Out of scope

## Allowed files

## Forbidden files

## Gates

## Stop condition
```

Every run writes the effective task body to `.agent/runs/<run_id>/task_spec.md`.

## Task Spec Guardrails

For file-backed task specs, the verifier reads `Allowed files` and `Forbidden files` sections:

```markdown
## Allowed files

- `sample_math/__init__.py`
- `src/`

## Forbidden files

- `tests/`
- `pyproject.toml`
```

If `Allowed files` is present, every changed target repo file must match an entry. Any changed file matching `Forbidden files` fails verification. Matching is intentionally simple: exact file match, or directory prefix match for entries ending in `/`. Globs are not implemented.

Inline `--task` runs do not get task file guardrails.

## Local Skills

A local skill is a reusable Markdown playbook stored at:

```text
skills/<skill_name>/SKILL.md
```

Select one explicitly:

```bash
python3 scripts/run_agent_loop.py --task-file tasks/fix-sample-add.md --skill failing-test-fix --implementer codex
```

When selected, the skill is included in the Codex prompt and copied to `.agent/runs/<run_id>/skill.md`. Skills are repo-local playbooks only. There is no skill auto-selection, marketplace, plugin install flow, MCP connector, or remote skill source.

## Named Gates

String gates are still supported:

```yaml
gates:
  - "python3 -m unittest discover -s tests"
```

Named gate objects are also supported:

```yaml
allowed_commands:
  - "python3 -m unittest discover -s tests"
  - "ruff check ."
gates:
  - name: unit tests
    command: "python3 -m unittest discover -s tests"
    required: true
  - name: lint
    command: "ruff check ."
    required: false
```

Required gate failures fail the run. Optional gate failures are recorded as warnings in `gate_results.json`, `verifier_result.json`, and `run_report.md`, but do not fail the run by themselves. `allowed_commands` checks the command string, not the display name.

Default gate detection is intentionally small:

- Node/TypeScript: `npm test`, `npm run lint`, `npm run typecheck`
- Python: `pytest`, `ruff check .`, `mypy .`

For a stdlib-only Python repo, configure `python3 -m unittest discover -s tests` explicitly.

## Artifacts

Each run writes:

- `.agent/runs/<run_id>/run_report.md`
- `.agent/runs/<run_id>/gate_results.json`
- `.agent/runs/<run_id>/verifier_result.json`
- `.agent/runs/<run_id>/stdout.log`
- `.agent/runs/<run_id>/stderr.log`
- `.agent/runs/<run_id>/diff_summary.md`
- `.agent/runs/<run_id>/review_bundle.md`
- `.agent/runs/<run_id>/pr_title.txt`
- `.agent/runs/<run_id>/pr_body.md`
- `.agent/runs/<run_id>/pr_commands.md`
- `.agent/runs/<run_id>/pr_handoff.md`
- `.agent/runs/<run_id>/pr_handoff_check.md`
- `.agent/runs/<run_id>/pr_handoff_check.json`
- `.agent/runs/<run_id>/task_spec.md`

When `--skill` is used, the run also writes:

- `.agent/runs/<run_id>/skill.md`

Every run writes:

- `.agent/runs/<run_id>/context_summary.json`

When `--issue-file` or `--ci-log-file` is used, the run also writes:

- `.agent/runs/<run_id>/issue_context.md`
- `.agent/runs/<run_id>/ci_context.log`

When `--implementer codex` is used, the run also writes:

- `.agent/runs/<run_id>/codex_prompt.md`
- `.agent/runs/<run_id>/codex_stdout.log`
- `.agent/runs/<run_id>/codex_stderr.log`
- `.agent/runs/<run_id>/codex_result.json`

The orchestrator also updates `.agent/state.json` and `PROGRESS.md`.

`review_bundle.md` is the human review artifact. It collects the task, skill, changed files, gates, verifier result, diff summary, checklist, and a conservative recommendation such as `ready_for_human_review`, `manual_review_required`, or `reject_or_rework`.

The draft PR handoff package is local only. `pr_title.txt`, `pr_body.md`, and `pr_commands.md` prepare a human to inspect the worktree and optionally commit, push, and create a draft PR manually. `pr_handoff_check.md` and `pr_handoff_check.json` summarize local-only validation of the handoff: verifier result, required gates, review recommendation, changed files, task guardrails, reserved artifacts, worktree path, git repo state, branch, origin remote presence, and `gh` availability. Agent Loop Factory writes these suggestions, but it does not run `git commit`, `git push`, `gh pr create`, merge, or deploy. `gh` availability and origin remote presence are informational only, not blockers. Review the diff, gates, verifier result, handoff check, and changed files before using anything in `pr_commands.md`. Future draft PR automation can build on these artifacts without changing the current human review boundary.

## Verifier Checks

The deterministic verifier checks:

- required gate failures
- optional gate failures as warnings
- changed file count against `max_changed_files`
- diff line count against `max_diff_lines`
- touched `human_required_paths`
- changed reserved artifact filenames inside the target repo
- task spec `Allowed files` violations
- task spec `Forbidden files` touches
- simple test weakening signals: deleted files under `tests/`, removed assertions in test files, and added skip markers

The final run status passes only when worktree creation, the selected implementer, required gates, and the verifier pass.

## Safety Boundaries

Current safety boundaries are local and deterministic:

- Manual trigger only.
- Isolated git worktree per run.
- Default implementer is `none`.
- Codex runs only when explicitly selected.
- Gates must appear in `allowed_commands`.
- Sensitive paths are listed in `human_required_paths`.
- Task spec file guardrails can restrict allowed and forbidden files.
- `auto_merge: false` and `auto_deploy: false` are fixed safety expectations, not implemented automation switches.
- The loop stops after writing artifacts for human review.
- Draft PR handoff commands are written as text only; they are not executed.

The Codex prompt includes the task, selected skill, configured safety limits, `AGENTS.md`, and `CONSTRAINTS.md` when present. Gates and the deterministic verifier decide run success; the implementer does not.

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md).

Planned items are not implemented unless listed above. The current implemented milestone is v9 local issue / CI context intake, not GitHub fetching, autonomous PR creation, merge, or deployment.

## Troubleshooting

If Codex is not installed or not on `PATH`, runs with `--implementer codex` write `codex unavailable` into:

- `.agent/runs/<run_id>/codex_result.json`
- `.agent/runs/<run_id>/codex_stderr.log`
- `.agent/runs/<run_id>/run_report.md`

Set `codex_command` in `.agent/config.yaml` if the executable has a different name or path.
