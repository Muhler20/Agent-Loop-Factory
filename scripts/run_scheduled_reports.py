#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_loop_factory.report_config import load_report_config
from agent_loop_factory.scheduled_report import run_scheduled_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one report definition once; this command does not schedule itself.")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list-configs", action="store_true")
    args = parser.parse_args()
    if args.list_configs:
        if args.config or args.dry_run:
            parser.error("--list-configs cannot be combined with --config or --dry-run")
        for path in sorted((ROOT / "report_configs").glob("*.json")):
            print(path.relative_to(ROOT))
        return 0
    if not args.config:
        parser.error("--config is required unless --list-configs is used")
    try:
        load_report_config(ROOT, args.config)
        result = run_scheduled_report(ROOT, args.config, dry_run=args.dry_run)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"report_id={result['report_id']}")
    print(f"report_dir={result['report_dir']}")
    return 0 if not result["report_types_failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
