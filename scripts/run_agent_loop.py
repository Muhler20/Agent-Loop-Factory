#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_loop_factory.orchestrator import run
from agent_loop_factory.task_spec import load_task_spec


def main() -> int:
    parser = argparse.ArgumentParser()
    task_group = parser.add_mutually_exclusive_group(required=True)
    task_group.add_argument("--task")
    task_group.add_argument("--task-file", type=Path)
    parser.add_argument("--implementer", choices=["none", "codex"], default="none")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        task_spec = load_task_spec(args.task_file) if args.task_file else None
    except ValueError as exc:
        parser.error(str(exc))

    result = run(
        task_spec.task_body if task_spec else args.task,
        ROOT,
        dry_run=args.dry_run,
        implementer=args.implementer,
        task_file_path=task_spec.task_file_path if task_spec else None,
    )
    print(f"run_id={result['run_id']}")
    print(f"run_dir={result['run_dir']}")
    return 0 if result["ok"] or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
