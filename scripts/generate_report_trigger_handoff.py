#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_loop_factory.report_trigger_handoff import TARGETS, generate_report_trigger_handoff


def main() -> int:
    parser = argparse.ArgumentParser(description="Write external report trigger handoff instructions; install and run nothing.")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--target", choices=TARGETS)
    parser.add_argument("--list-targets", action="store_true")
    args = parser.parse_args()
    if args.list_targets:
        if args.config or args.target:
            parser.error("--list-targets cannot be combined with --config or --target")
        print("\n".join(TARGETS))
        return 0
    if not args.config or not args.target:
        parser.error("--config and --target are required unless --list-targets is used")
    try:
        result = generate_report_trigger_handoff(ROOT, args.config, args.target)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"handoff_id={result['handoff_id']}")
    print(f"handoff_dir={result['handoff_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
