#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_loop_factory.orchestrator import run
from agent_loop_factory.context_intake import load_context
from agent_loop_factory.github_context import validate_github_flags
from agent_loop_factory.memory_context import load_memory_context
from agent_loop_factory.memory_registry import validate_memory_registry
from agent_loop_factory.skill import load_skill
from agent_loop_factory.task_spec import load_task_spec


def main() -> int:
    parser = argparse.ArgumentParser()
    task_group = parser.add_mutually_exclusive_group()
    task_group.add_argument("--task")
    task_group.add_argument("--task-file", type=Path)
    parser.add_argument("--check-memory", action="store_true")
    parser.add_argument("--implementer", choices=["none", "codex"], default="none")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skill")
    parser.add_argument("--issue-file", type=Path)
    parser.add_argument("--ci-log-file", type=Path)
    parser.add_argument("--github-issue")
    parser.add_argument("--github-repo")
    parser.add_argument("--github-ci-run")
    parser.add_argument("--memory-file", action="append", type=Path)
    parser.add_argument("--advisory-reviewer", choices=["codex"])
    args = parser.parse_args()

    try:
        validate_github_flags(args.github_issue, args.github_repo, args.github_ci_run)
        if args.issue_file and args.github_issue:
            raise ValueError("--issue-file cannot be used with --github-issue")
        if args.ci_log_file and args.github_ci_run:
            raise ValueError("--ci-log-file cannot be used with --github-ci-run")
        if args.check_memory and (args.github_issue or args.github_repo or args.github_ci_run):
            raise ValueError("--check-memory cannot be combined with GitHub context flags")
        if args.check_memory and args.advisory_reviewer:
            raise ValueError("--check-memory cannot be combined with --advisory-reviewer")
    except ValueError as exc:
        parser.error(str(exc))

    if args.check_memory:
        result = validate_memory_registry(ROOT)
        if result.ok:
            print("memory registry ok with warnings" if result.warnings else "memory registry ok")
            for warning in result.warnings:
                print(f"- {warning}")
            return 0
        print("memory registry invalid")
        for error in result.errors:
            print(f"- {error}")
        return 1
    if not args.task and not args.task_file:
        parser.error("one of the arguments --task --task-file is required")

    try:
        task_spec = load_task_spec(args.task_file) if args.task_file else None
        skill = load_skill(ROOT, args.skill) if args.skill else None
        context = load_context(args.issue_file, args.ci_log_file)
        memory_context = load_memory_context(ROOT, args.memory_file)
    except ValueError as exc:
        parser.error(str(exc))

    try:
        result = run(
            task_spec.task_body if task_spec else args.task,
            ROOT,
            dry_run=args.dry_run,
            implementer=args.implementer,
            task_file_path=task_spec.task_file_path if task_spec else None,
            skill=skill,
            context=context,
            memory_context=memory_context,
            github_issue=args.github_issue,
            github_repo=args.github_repo,
            github_ci_run=args.github_ci_run,
            advisory_reviewer=args.advisory_reviewer,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(f"run_id={result['run_id']}")
    print(f"run_dir={result['run_dir']}")
    return 0 if result["ok"] or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
