#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_loop_factory.orchestrator import run


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--implementer", choices=["none", "codex"], default="none")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run(args.task, ROOT, dry_run=args.dry_run, implementer=args.implementer)
    print(f"run_id={result['run_id']}")
    print(f"run_dir={result['run_dir']}")
    return 0 if result["ok"] or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
