# Version History

## v13.1 external report trigger handoff artifacts

Added deterministic, manually generated trigger instructions under `.agent/report_handoffs/`. Explicit trigger hints use local time for cron/systemd-user and UTC for GitHub Actions. No trigger is installed, no report is run, and no code, memory, worktree, `.github/workflows/`, Codex, or GitHub write path was added.

## v13 manually invoked report definitions

Added human-authored JSON definitions and read-only report artifacts. Cadence is metadata only; no scheduler, worktree, Codex implementation, code/memory mutation, or GitHub write behavior was added.

## v0 deterministic loop skeleton

Purpose: prove a manual local loop can create a run record and stop.
Main artifacts/features: CLI entrypoint, config read, state/progress updates.
Safety boundary preserved: no autonomous action.

## v0.5 sample target repo smoke test

Purpose: provide a tiny target repo for end-to-end local testing.
Main artifacts/features: sample repo creator and smoke task.
Safety boundary preserved: local-only test fixture.

## v1 optional Codex implementer

Purpose: allow one explicit Codex attempt.
Main artifacts/features: `--implementer codex`, Codex prompt and logs.
Safety boundary preserved: default implementer remains `none`.

## v2 deterministic verifier

Purpose: make success independent of LLM claims.
Main artifacts/features: verifier JSON and deterministic pass/fail checks.
Safety boundary preserved: gates and verifier decide run status.

## v2.5 constraints and task docs

Purpose: document operating constraints and task shape.
Main artifacts/features: `CONSTRAINTS.md` and task guidance.
Safety boundary preserved: human-readable rules included in runs.

## v3 task spec file support

Purpose: move larger tasks into reviewable Markdown specs.
Main artifacts/features: `--task-file` and `task_spec.md`.
Safety boundary preserved: task is explicit input.

## v4 task spec guardrails

Purpose: constrain changed files from task specs.
Main artifacts/features: `Allowed files` and `Forbidden files` verifier checks.
Safety boundary preserved: scope violations fail verification.

## v5 local skills

Purpose: include explicit local playbooks.
Main artifacts/features: `--skill` and `skill.md`.
Safety boundary preserved: no skill auto-selection or remote skills.

## v6 named gates and diff reporting

Purpose: make gates readable and diffs easier to review.
Main artifacts/features: named required/optional gates and `diff_summary.md`.
Safety boundary preserved: commands must match `allowed_commands`.

## v6.1 docs and roadmap cleanup

Purpose: align docs with implemented milestones.
Main artifacts/features: README and roadmap cleanup.
Safety boundary preserved: documentation only.

## v7 human review bundle

Purpose: put review signals in one artifact.
Main artifacts/features: `review_bundle.md` with checklist and recommendation.
Safety boundary preserved: loop stops for human review.

## v7.1 review bundle gate-warning polish

Purpose: improve optional gate warning visibility.
Main artifacts/features: clearer gate warnings in review artifacts.
Safety boundary preserved: optional gates warn without replacing required gates.

## v8 draft PR handoff package

Purpose: prepare local PR text for a human.
Main artifacts/features: `pr_title.txt`, `pr_body.md`, `pr_commands.md`, `pr_handoff.md`.
Safety boundary preserved: no PR is created.

## v8.1 PR handoff validation

Purpose: validate the local handoff package.
Main artifacts/features: `pr_handoff_check.md` and `pr_handoff_check.json`.
Safety boundary preserved: validation is local and advisory.

## v9 local issue / CI context intake

Purpose: include local issue and CI evidence.
Main artifacts/features: `--issue-file`, `--ci-log-file`, context artifacts.
Safety boundary preserved: context does not expand task scope.

## v9.1 config and safety hardening + GitHub Actions CI

Purpose: harden config and run repository tests in CI.
Main artifacts/features: stricter config expectations and unittest CI.
Safety boundary preserved: CI tests this repo only; no agent automation.

## v10 reviewable memory proposals

Purpose: suggest lessons without changing durable memory.
Main artifacts/features: `memory_proposal.md` and `memory_proposal.json`.
Safety boundary preserved: proposals are advisory.

## v10.1 human-approved memory registry

Purpose: create a durable location for accepted lessons.
Main artifacts/features: `memory/` registry skeleton.
Safety boundary preserved: humans approve registry entries.

## v10.2 explicit memory inclusion in prompts

Purpose: allow selected approved memory in Codex prompts.
Main artifacts/features: repeatable `--memory-file`, `memory_context.md`, `memory_context.json`.
Safety boundary preserved: no memory auto-selection.

## v10.3 memory hygiene checks

Purpose: validate active memory shape and safety.
Main artifacts/features: `--check-memory`.
Safety boundary preserved: check-only command does not create runs or update progress.

## v11 read-only GitHub issue / CI context intake using gh

Purpose: fetch explicit GitHub issue and CI context.
Main artifacts/features: `--github-issue`, `--github-repo`, `--github-ci-run`, GitHub context artifacts.
Safety boundary preserved: GitHub is input only; no writes.

## v11.1 operator documentation consolidation

Purpose: make operation, artifacts, safety, and history easy to inspect.
Main artifacts/features: operator guide, artifact reference, safety model, version history.
Safety boundary preserved: documentation only; no runtime behavior change.

## v12 optional advisory reviewer

Purpose: add an explicit second-opinion reviewer after deterministic facts exist.
Main artifacts/features: `--advisory-reviewer codex`, advisory prompt/stdout/stderr/result/markdown/JSON artifacts, malformed-output fallback.
Safety boundary preserved: advisory review is not a gate, does not affect `verifier_result.json`, does not replace gates or human review, treats evidence as untrusted data, and must not modify files or write to GitHub.

## v12.1 reviewer rubric files

Purpose: let humans explicitly include reviewer guidance for advisory review.
Main artifacts/features: `reviewers/`, `--reviewer-rubric reviewers/<rubric>.md`, `advisory_review_rubric.md`, and `advisory_review_rubric.json`.
Safety boundary preserved: rubrics are advisory only, do not affect `verifier_result.json`, do not replace gates or human review, and are not automatically selected, ranked, retrieved, or applied.
