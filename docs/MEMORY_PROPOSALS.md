# Memory Proposals

Memory proposals are per-run review artifacts written to `.agent/runs/<run_id>/memory_proposal.md` and `.agent/runs/<run_id>/memory_proposal.json`.

They summarize whether a run produced a reusable lesson and suggest where a human might apply it later. They are advisory only. Agent Loop Factory does not automatically edit `AGENTS.md`, `CONSTRAINTS.md`, skills, task specs, docs, future memory files, or any durable project rule file.

## Why They Exist

Runs can reveal repeatable failure patterns: test weakening, task scope violations, reserved artifact leakage, failed required gates, verifier failures, or PR handoff problems. v10 captures those signals deterministically so a human reviewer can decide whether the lesson is worth preserving.

## Human Review

Every proposal has:

- `requires_human_approval: true`
- `no_files_modified: true`

A human may accept, edit, reject, or convert a proposal into a verifier rule, skill update, docs update, or constraints update. The run itself does not apply the lesson.

## Status

`proposed` means at least one deterministic trigger produced a candidate lesson.

`no_proposal` means the run was clean enough that no reusable lesson was suggested. Clean passing runs with no warnings, gate failures, verifier issues, scope violations, reserved artifact leakage, test weakening, PR handoff attention, or human-required path touches should usually be `no_proposal`.

## Dry Runs

Dry runs still write both memory proposal artifacts, but they do not create candidate lessons. Their JSON includes `dry_run: true`, `proposal_status: no_proposal`, and an empty `candidate_lessons` list.

Dry-run structural verifier failures, such as `worktree unavailable`, are not treated as reusable failure lessons.

## v10.1 Memory Registry

`memory_proposal.md` is a suggestion. The `memory/` directory is the durable, human-approved registry.

Humans decide what enters `memory/`. Accepted lessons should be edited for clarity, placed in the right category, and include provenance such as source run id, date, and reason. Broad, vague, noisy, or risky lessons should be rejected.

When a lesson can be checked deterministically, prefer a verifier rule over memory.

Agent Loop Factory does not automatically copy proposals into `memory/`, and it does not retrieve registry memory into Codex prompts yet.

## Applying Later

A human can apply a proposal by editing an appropriate durable file, such as `memory/`, `CONSTRAINTS.md`, `AGENTS.md`, `skills/<skill>/SKILL.md`, `docs/TASK_SPEC_TEMPLATE.md`, or `docs/LOOP_SELECTION.md`. v10.1 creates the memory registry structure, but no retrieval flow, scheduler, connector, or LLM verifier.

## Risks

- Over-generalization: one local failure may not deserve a project-wide rule.
- Stale lessons: old guidance can become wrong as the project changes.
- Reward hacking: agents may optimize for remembered wording instead of task correctness.
- Memory clutter: too many low-value lessons make review harder.
