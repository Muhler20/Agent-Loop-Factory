# Memory Registry

## Purpose

The memory registry is the durable home for reusable lessons that a human has accepted for this project.

Memory proposals are generated per run in `.agent/runs/<run_id>/` as `memory_proposal.md` and `memory_proposal.json`. They are suggestions only. Accepted lessons may be copied or edited into `memory/` by a human.

Agent Loop Factory does not automatically apply memory proposals. Registry memory is included in Codex prompts only when a human explicitly names files with `--memory-file`.

## Human Approval Rule

Only humans should add accepted memory lessons to this registry. The loop may propose memory, but it must not copy proposal content into these files.

## Explicit Inclusion

Use repeatable `--memory-file` flags to include approved memory in a run:

```bash
python3 scripts/run_agent_loop.py --task-file tasks/fix-sample-add.md --memory-file memory/prompt-guidance/small-diffs.md
```

The loop does not search, rank, retrieve, or auto-select memory. Included memory is guidance only; task specs, constraints, gates, verifier rules, and human approval boundaries still win. Runs do not modify memory files.

## Current Categories

- `failure-patterns/`: repeatable mistakes or failure modes to watch for.
- `prompt-guidance/`: human-approved guidance that may later shape prompts.
- `reviewer-guidance/`: review checks or judgment calls for human reviewers.
- `deprecated/`: old lessons kept for provenance instead of being silently deleted.

## How To Apply A Memory Proposal

1. Open `.agent/runs/<run_id>/memory_proposal.md`.
2. Decide whether the proposal is reusable.
3. Reject noisy or over-generalized lessons.
4. If accepted, create or edit a file under `memory/`.
5. Include provenance: source run_id, date, and reason.
6. Commit the memory change like normal code.

## Rules

- Do not store secrets.
- Do not store credentials.
- Do not store private customer data.
- Do not accept memories from failed or suspicious runs without extra review.
- Prefer narrow lessons over broad rules.
- Prefer verifier rules over memory when the lesson can be checked deterministically.
- Deprecated lessons should move to `deprecated/` instead of being silently deleted.
