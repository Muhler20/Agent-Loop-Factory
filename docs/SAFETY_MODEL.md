# Safety Model

## v13 report boundary

Definitions must assert report-only, no code changes, no git writes, no GitHub writes, no Codex implementer, and required human action. The runner writes only `.agent/reports/`; it does not create worktrees, mutate memory, schedule itself, or remediate findings.

## Core Principle

Agents may write code, but the loop controls the process.

Agent Loop Factory creates a supervised local run, records what happened, checks it deterministically, and stops for human review. It does not turn agent output into durable or external action.

## Trust Boundaries

- human operator: chooses task, context, memory, implementer, and any post-run action
- orchestrator: coordinates one local run and writes receipts
- implementer: may edit the worktree, but is not trusted to decide success
- gates: configured commands that test the worktree
- deterministic verifier: checks gates, diff limits, task scope, sensitive paths, reserved artifacts, and test weakening signals
- advisory reviewer: optional second-opinion note-taker, not a gate and not an authority
- reviewer rubric: optional human-selected advisory guidance for the advisory reviewer
- GitHub CLI read-only context: optional explicit input source only
- memory registry: human-approved guidance, included only when explicitly selected
- review bundle: human review aid, not approval
- PR handoff: local draft text and validation only, not PR creation

## What Is Deterministic

- config parsing
- gate execution
- verifier checks
- memory hygiene checks
- task scope checks
- reserved artifact checks
- GitHub identifier validation
- CI log truncation

The advisory reviewer orchestration is deterministic around prompt construction, command shape, parsing, validation, fallback, and artifact writing. The reviewer judgment itself is not deterministic authority.

## What Is Not Trusted

- Codex output
- advisory reviewer output
- LLM claims of success
- GitHub context as complete truth
- memory proposals before human approval
- included memory as overriding rules
- diffs, logs, issues, memory notes, and generated artifacts as instructions

## Human-Required Boundaries

Humans must approve changes touching:

- auth
- billing
- payments
- migrations
- infra
- deployment
- Docker
- CI config
- `.github/`
- any configured `human_required_paths`

## GitHub Safety

v11 uses GitHub as input only. Local `gh` auth may have write scopes, so code must only call read-only `gh` commands.

Agent Loop Factory must not comment, label, edit issues, create or edit PRs, rerun workflows, trigger workflows, push, merge, deploy, publish, or create releases.

Use read-only-scoped GitHub auth or a read-only token when practical.

## Memory Safety

Memory proposals are advisory. The memory registry is human-approved. Memory inclusion is explicit through `--memory-file`.

Memory hygiene checks validate active memory. Memory does not override constraints, gates, verifier checks, task scope, `AGENTS.md`, `CONSTRAINTS.md`, human-required paths, or human approval.

## Advisory Review Safety

`--advisory-reviewer codex` is explicit opt-in. The reviewer receives bounded run evidence and is told to treat all evidence as untrusted data because target repo content can contain prompt-injection text. Advisory review does not modify files, does not write to GitHub, does not affect `verifier_result.json`, and does not replace gates, verifier checks, task scope, memory hygiene, constraints, or human approval boundaries.

`--reviewer-rubric reviewers/<rubric>.md` is valid only with `--advisory-reviewer codex`. Rubrics are human-authored files under `reviewers/`; they guide advisory review only, do not affect `verifier_result.json`, do not replace gates or human review, and are not automatically selected, ranked, retrieved, or applied.

Malformed, truncated, prose, invalid, nonzero-exit, timeout, or unavailable reviewer output is preserved in raw logs and marked `reviewer_output_unparseable`. That fallback does not mark the run passed or failed.

## Failure Modes

- gate failure
- verifier failure
- scope violation
- human-required path touched
- reserved artifact touched
- tests weakened or deleted
- GitHub fetch failure
- memory hygiene failure
- malformed advisory reviewer output

## Safe Escalation

Stop, inspect artifacts, and ask a human.

Do not auto-fix dangerous classes of failure such as sensitive path changes, CI config changes, deployment changes, GitHub writes, test weakening, or memory registry updates.
