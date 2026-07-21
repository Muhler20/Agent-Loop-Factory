# agent-loop-factory

## v14.1 safety-core protection policy

`python3 scripts/run_agent_planning.py --task "Plan how to fix the selected issue." --context-file .agent/reports/<report_id>/scheduled_report.json --triage-agent codex --planner-agent codex` writes reviewable artifacts under `.agent/plans/<plan_id>/`. `--task-file` is also supported; `--dry-run` validates inputs and writes receipts without calling Codex.

This separate pipeline is planning-only. It does not implement code, create worktrees, call the implementer, run gates or verifier, write to GitHub, execute reports, or mutate memory. `task_spec_draft.md` is a draft requiring human review; implementation can happen only through a later explicit `run_agent_loop.py` invocation.

Planning now warns when task text, explicit context, or planner fields reference safety-core files at the control-loop trust boundary. These warnings identify higher-risk work requiring extra human review; they neither prove a change unsafe nor make an unflagged change safe. Dogfood on docs, tests, and low-risk helpers first; safety-layer dogfooding is a restricted higher-risk mode. Plan promotion and approved-plan implementation remain future milestones.

## v13.1 external report trigger handoffs

Run a definition once with `python3 scripts/run_scheduled_reports.py --config report_configs/daily-health.json`; use `--dry-run` for a receipt or `--list-configs` to list definitions. `report_configs/` is human-authored input and `.agent/reports/` is generated output. Cadence is metadata only: v13 installs no scheduler, cron, systemd, GitHub Actions, daemon, queue, or worker.

Generate copy/paste instructions with `python3 scripts/generate_report_trigger_handoff.py --config report_configs/daily-health.json --target cron`; targets are `manual`, `cron`, `systemd-user`, and `github-actions`. Explicit `trigger_hints` provide local time for cron/systemd or UTC for GitHub Actions. Artifacts under `.agent/report_handoffs/` are handoff-only: nothing is installed, scheduled, or run; `.github/workflows/` and GitHub are not written; Codex, worktrees, and memory are untouched. A human must review and manually install any trigger.

Reports are advisory. They do not create worktrees, change code or memory, call Codex as an implementer, or write to GitHub. A human or external system may invoke the runner and must decide any next action.

`agent-loop-factory` is a supervised software-agent control loop for local coding-agent runs. It creates an isolated git worktree for a target repository, optionally asks Codex to make one small change, runs configured gates, verifies the resulting diff deterministically, writes audit artifacts, and stops for human review.

It is not an autonomous coding platform. Through v12.1 it is manually triggered and human-in-the-loop. GitHub can be an explicit read-only input source through `gh`, but it is not an output target. The optional advisory reviewer is a second-opinion note-taker only. Reviewer rubrics are explicit advisory guidance only. The loop does not push, merge, deploy, open PRs, comment on issues, label issues, rerun workflows, listen for webhooks, run a scheduler, use Docker sandboxing, run parallel agents, auto-select skills, call an LLM verifier, use MCP/connectors, automatically update durable memory/rule files, or automatically search, rank, retrieve, or select memory.

## What It Solves

Agent Loop Factory is for small, repeatable coding tasks where the target repo has runnable checks and a human wants a clear review boundary. It turns a coding-agent attempt into a controlled run with:

- a fresh git worktree
- configured required or optional gates
- deterministic checks on changed files, diff size, task scope, sensitive paths, and test weakening
- run artifacts under `.agent/runs/<run_id>/`
- a progress/state record for manual follow-up

## What It Does Today

Implemented through v14.1:

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
- v7.1 review bundle gate-warning polish
- v8 local draft PR handoff package
- v8.1 PR handoff validation
- v9 local issue / CI context intake
- v9.1 config and safety hardening, plus repository test CI
- v10 reviewable memory proposals
- v10.1 human-approved memory registry
- v10.2 explicit memory inclusion in prompts
- v10.3 memory hygiene checks
- v11 explicit read-only GitHub issue / CI context intake using `gh`
- v11.1 operator documentation consolidation
- v12 optional advisory reviewer
- v12.1 reviewer rubric files
- v13 manually invoked report definitions
- v13.1 external report trigger handoffs
- v14 planning-only triage and planner agents
- v14.1 safety-core protection policy

Current capabilities:

- Manual CLI trigger with `--task` or `--task-file`.
- Safe default implementer: `--implementer none`.
- Optional one-shot Codex implementer: `--implementer codex`.
- Local skill playbooks selected explicitly with `--skill`.
- Optional local issue and CI log context files with `--issue-file` and `--ci-log-file`.
- Optional read-only GitHub issue / CI context with `--github-issue`, `--github-repo`, and `--github-ci-run`.
- Optional advisory Codex reviewer with `--advisory-reviewer codex`.
- Optional explicit reviewer rubric for the advisory reviewer with `--reviewer-rubric reviewers/<rubric>.md`.
- Git worktree isolation under the configured worktree base path.
- Required and optional named gates.
- Diff summary including tracked stats and untracked files.
- Deterministic verifier results written as JSON.
- Reviewable memory proposal artifacts that may suggest human-approved lessons.
- Human-approved memory registry skeleton under `memory/`.
- Explicit human-selected memory inclusion with repeatable `--memory-file`.
- Human review boundary after every run.

## How The Loop Works

1. Read `.agent/config.yaml`.
2. Load the inline task or Markdown task spec.
3. Load optional local context files from `--issue-file` and `--ci-log-file`.
4. Validate explicitly selected memory files from `--memory-file`, if provided.
5. Load an explicitly selected local skill, if `--skill` is provided.
6. Create `.agent/runs/<run_id>/`.
7. Fetch explicit GitHub context with read-only `gh` commands, if requested.
8. Create a git worktree for the configured target repo.
9. Run the selected implementer. The default `none` makes no code changes; `codex` runs `codex exec` once inside the worktree.
10. Run configured gates from the worktree.
11. Run the deterministic verifier.
12. Optionally run the advisory reviewer after gates, verifier, recommendation, and handoff validation facts exist.
13. Optionally include a human-selected reviewer rubric as advisory reviewer guidance.
14. Write reviewable memory proposal artifacts.
15. Write audit artifacts and update `.agent/state.json` and `PROGRESS.md`.
16. Stop for human review.

## Basic Dry Run

From the repo root:

```bash
cd ~/coding-projects/agent-loop-factory
python3 scripts/run_agent_loop.py --task "test task description" --dry-run
```

This creates a run record and planned artifacts without creating a git worktree or executing gates.

## Operator Documentation

- [Operator Guide](docs/OPERATOR_GUIDE.md): safe human operating flow and run patterns.
- [Artifact Reference](docs/ARTIFACT_REFERENCE.md): every run artifact and what to inspect.
- [Safety Model](docs/SAFETY_MODEL.md): trust boundaries and failure handling.
- [Version History](docs/VERSION_HISTORY.md): concise milestone history through v12.1.

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

Task spec with optional advisory review:

```bash
python3 scripts/run_agent_loop.py --task-file tasks/fix-sample-add.md --advisory-reviewer codex
```

The advisory reviewer runs after gates, `verifier_result.json`, review recommendation, and PR handoff validation exist. It writes `advisory_review.md`, `advisory_review.json`, `advisory_review_result.json`, prompt, stdout, and stderr artifacts. It is advisory only, does not affect `verifier_result.json`, does not replace gates, verifier, or human review, and must not modify files. Malformed reviewer output is preserved and marked `reviewer_output_unparseable`.

Advisory review with an explicit reviewer rubric:

```bash
python3 scripts/run_agent_loop.py \
  --task-file tasks/fix-sample-add.md \
  --advisory-reviewer codex \
  --reviewer-rubric reviewers/test-reviewer.md
```

Reviewer rubrics are human-authored files under `reviewers/`. They guide the advisory reviewer only, do not affect `verifier_result.json`, do not replace gates or human review, and are never automatically selected, ranked, retrieved, or applied. When used, `advisory_review_rubric.md` and `advisory_review_rubric.json` are written as receipts.

Task spec with explicit approved memory:

```bash
python3 scripts/run_agent_loop.py \
  --task-file tasks/fix-sample-add.md \
  --memory-file memory/failure-patterns/test-weakening.md \
  --memory-file memory/prompt-guidance/small-diffs.md \
  --skill failing-test-fix \
  --implementer codex
```

Memory registry check:

```bash
python3 scripts/run_agent_loop.py --check-memory
```

## Memory Registry

`memory/` is the durable registry for human-approved lessons. Per-run `memory_proposal.md` files are suggestions only; a human must accept, edit, or reject them.

`--check-memory` validates the registry shape, active memory metadata, required sections, size limits, and simple secret markers without creating a run, calling Codex, running gates, or updating `.agent/state.json` or `PROGRESS.md`. Stale memories, duplicate active titles, deprecated entries outside `memory/deprecated/`, and small conservative conflict signals warn without failing.

`--memory-file PATH` may be repeated to include human-approved Markdown files from `memory/` in the Codex prompt. The loop validates that each file is under `memory/`, outside `memory/deprecated/`, UTF-8, `.md`, small enough, non-duplicated, free of the same simple secret markers used by `--check-memory`, and valid under active memory hygiene rules when it is in an active category.

Memory inclusion is human-selected only. The loop does not search, rank, retrieve, auto-select, auto-apply, or modify memory. Included memory is guidance only; task specs, allowed/forbidden files, `CONSTRAINTS.md`, `AGENTS.md`, `human_required_paths`, gates, verifier rules, and no-push/no-PR/no-deploy boundaries still win.

## Local Issue / CI Context

`--issue-file PATH` and `--ci-log-file PATH` attach local text files as supporting evidence for the run. They do not replace the task spec, and they do not expand scope. The task spec, allowed files, forbidden files, constraints, gates, and human-review rules still control the run.

Local context intake reads the provided files from disk as UTF-8 text, validates that they are non-empty files under a fixed size limit, and writes run artifacts. Local and GitHub versions of the same context slot cannot be combined.

## GitHub Issue / CI Context

v11 adds explicit read-only GitHub context intake using the local `gh` CLI:

```bash
python3 scripts/run_agent_loop.py --task-file tasks/fix-sample-add.md --github-issue owner/repo#12 --implementer codex
python3 scripts/run_agent_loop.py --task-file tasks/fix-sample-add.md --github-repo owner/repo --github-ci-run 123456789 --implementer codex
```

The only `gh` command shapes used are `gh issue view owner/repo#number`, `gh run view run_id --repo owner/repo`, and `gh run view run_id --repo owner/repo --log`. GitHub context is supporting evidence only. It cannot override task scope, constraints, gates, verifier rules, memory hygiene rules, or human approval boundaries.

Local `gh` auth may still have write permissions, so prefer a read-only-scoped GitHub token or account when possible. Agent Loop Factory does not comment, label, edit, close issues, create or edit PRs, rerun workflows, trigger workflows, push, merge, deploy, publish, or create releases.

Fetched GitHub issue and CI context are written as local run artifacts. CI logs are tail-truncated at 50 KB.

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

Required gate failures fail the run. Optional gate failures are recorded as warnings in `gate_results.json`, `verifier_result.json`, and `run_report.md`, but do not fail the run by themselves.

`allowed_commands` uses exact command strings. A gate command must match an entry exactly; different whitespace is different. Named gates check the `command` field, not the display `name`.

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
- `.agent/runs/<run_id>/memory_proposal.md`
- `.agent/runs/<run_id>/memory_proposal.json`
- `.agent/runs/<run_id>/task_spec.md`

When `--skill` is used, the run also writes:

- `.agent/runs/<run_id>/skill.md`

Every run writes:

- `.agent/runs/<run_id>/context_summary.json`

When `--issue-file` or `--ci-log-file` is used, the run also writes:

- `.agent/runs/<run_id>/issue_context.md`
- `.agent/runs/<run_id>/ci_context.log`

When GitHub context flags are used, the run may also write:

- `.agent/runs/<run_id>/github_issue_context.md`
- `.agent/runs/<run_id>/github_issue_context.json`
- `.agent/runs/<run_id>/github_ci_context.log`
- `.agent/runs/<run_id>/github_ci_context.json`
- `.agent/runs/<run_id>/github_context_summary.json`

When `--memory-file` is used, the run also writes:

- `.agent/runs/<run_id>/memory_context.md`
- `.agent/runs/<run_id>/memory_context.json`

When `--implementer codex` is used, the run also writes:

- `.agent/runs/<run_id>/codex_prompt.md`
- `.agent/runs/<run_id>/codex_stdout.log`
- `.agent/runs/<run_id>/codex_stderr.log`
- `.agent/runs/<run_id>/codex_result.json`

The orchestrator also updates `.agent/state.json` and `PROGRESS.md`.

`review_bundle.md` is the human review artifact. It collects the task, skill, changed files, gates, verifier result, diff summary, checklist, and a conservative recommendation such as `ready_for_human_review`, `manual_review_required`, or `reject_or_rework`.

The draft PR handoff package is local only. `pr_title.txt`, `pr_body.md`, and `pr_commands.md` prepare a human to inspect the worktree and optionally commit, push, and create a draft PR manually. `pr_handoff_check.md` and `pr_handoff_check.json` summarize local-only validation of the handoff: verifier result, required gates, review recommendation, changed files, task guardrails, reserved artifacts, worktree path, git repo state, branch, origin remote presence, and `gh` availability. Agent Loop Factory writes these suggestions, but it does not run `git commit`, `git push`, `gh pr create`, merge, or deploy. `gh` availability and origin remote presence are informational only, not blockers. Review the diff, gates, verifier result, handoff check, and changed files before using anything in `pr_commands.md`. Future draft PR automation can build on these artifacts without changing the current human review boundary.

`memory_proposal.md` and `memory_proposal.json` are advisory. They may suggest reusable lessons from failed gates, verifier findings, scope violations, test weakening, or handoff warnings, but they never modify `memory/`, `AGENTS.md`, `CONSTRAINTS.md`, skills, docs, or task specs automatically. See [docs/MEMORY_PROPOSALS.md](docs/MEMORY_PROPOSALS.md).

`memory_context.md` and `memory_context.json` are written only when a human passes one or more `--memory-file` flags. They record the explicitly included memory files and confirm there was no automatic selection or retrieval.

`advisory_review.md` and `advisory_review.json` are written only with `--advisory-reviewer codex`. They are advisory receipts, not authority. Malformed reviewer output is preserved in raw logs and marked `reviewer_output_unparseable`.

`advisory_review_rubric.md` and `advisory_review_rubric.json` are written only when a human also passes `--reviewer-rubric reviewers/<rubric>.md`. They record the explicit rubric source and confirm automatic rubric selection was false.

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
- Memory proposals are written as review artifacts only; durable memory/rule files are never updated automatically.
- Registry memory is included in prompts only when a human names files with `--memory-file`; there is no automatic memory search, ranking, retrieval, or selection.
- Included memory is guidance only and cannot override task scope, constraints, gates, verifier rules, or human approval boundaries.
- GitHub context is explicit, read-only, and supporting evidence only; it does not write to GitHub or discover work automatically.
- Advisory review and reviewer rubrics are explicit, advisory only, and cannot change `verifier_result.json`.
- Repository CI only runs `python3 -m unittest discover -s tests`; it is not webhook-based agent automation.

The Codex prompt includes the task, selected skill, optional local/GitHub context, optional explicit memory context, configured safety limits, `AGENTS.md`, and `CONSTRAINTS.md` when present. Gates and the deterministic verifier decide run success; the implementer does not.

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) and [docs/VERSION_HISTORY.md](docs/VERSION_HISTORY.md).

Planned items are not implemented unless listed above. The current implemented milestone is v14.1 safety-core protection policy. GitHub context remains read-only input; the loop does not automatically retrieve memory, auto-select rubrics, write to GitHub, create PRs, merge, or deploy.

## Troubleshooting

If Codex is not installed or not on `PATH`, runs with `--implementer codex` write `codex unavailable` into:

- `.agent/runs/<run_id>/codex_result.json`
- `.agent/runs/<run_id>/codex_stderr.log`
- `.agent/runs/<run_id>/run_report.md`

Set `codex_command` in `.agent/config.yaml` if the executable has a different name or path.
