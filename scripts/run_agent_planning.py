#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_loop_factory.planning_agents import load_planning_input, run_planning, validate_agent_flags


def main() -> int:
    parser = argparse.ArgumentParser(description="Write planning-only triage and planner artifacts for human review.")
    tasks = parser.add_mutually_exclusive_group(required=True)
    tasks.add_argument("--task")
    tasks.add_argument("--task-file", type=Path)
    parser.add_argument("--context-file", action="append", type=Path, default=[])
    parser.add_argument("--triage-agent")
    parser.add_argument("--planner-agent")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        validate_agent_flags(args.triage_agent, args.planner_agent)
        inputs = load_planning_input(ROOT, task=args.task, task_file=args.task_file, context_files=args.context_file)
        result = run_planning(ROOT, inputs, triage_agent=args.triage_agent, planner_agent=args.planner_agent, dry_run=args.dry_run)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"plan_id={result['plan_id']}")
    print(f"plan_dir={result['plan_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
