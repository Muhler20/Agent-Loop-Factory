from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .config import Config


def run_gates(config: Config, cwd: Path, run_dir: Path, dry_run: bool = False) -> list[dict[str, object]]:
    results = []
    stdout_log = run_dir / "stdout.log"
    stderr_log = run_dir / "stderr.log"
    stdout_log.write_text("")
    stderr_log.write_text("")

    for command in config.gates:
        result: dict[str, object] = {"command": command, "ok": False, "returncode": None, "warning": None}
        if command not in config.allowed_commands:
            result["warning"] = "command not allowed by config"
        elif dry_run:
            result["ok"] = True
            result["warning"] = "dry-run: command not executed"
        elif shutil.which(command.split()[0]) is None:
            result["warning"] = f"command unavailable: {command.split()[0]}"
        else:
            completed = subprocess.run(command.split(), cwd=cwd, capture_output=True, text=True)
            stdout_log.write_text(stdout_log.read_text() + completed.stdout)
            stderr_log.write_text(stderr_log.read_text() + completed.stderr)
            result["ok"] = completed.returncode == 0
            result["returncode"] = completed.returncode
        results.append(result)

    (run_dir / "gate_results.json").write_text(json.dumps(results, indent=2) + "\n")
    return results
