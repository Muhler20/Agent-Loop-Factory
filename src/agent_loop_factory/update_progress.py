from __future__ import annotations


def build_progress(run_id: str, task: str, status: str, next_action: str, blocker: str = "None.") -> str:
    return f"""# Progress

## Current Goal

{task}

## Last Run

{run_id}: {status}

## In Progress

Manual supervised loop skeleton.

## Blockers

{blocker}

## Next Action

{next_action}

## Decisions

- v0 is manual and deterministic.
- v0 does not call LLMs.
- v0 does not push, merge, deploy, or open PRs.
"""
