from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path

from .config import Config, normalize_gates


def run_gates(config: Config, cwd: Path, run_dir: Path, dry_run: bool = False) -> list[dict[str, object]]:
    results = []
    stdout_log = run_dir / "stdout.log"
    stderr_log = run_dir / "stderr.log"

    for gate in normalize_gates(config.gates):
        command = str(gate["command"])
        required = bool(gate["required"])
        result: dict[str, object] = {
            "name": gate["name"],
            "command": command,
            "required": required,
            "ok": False,
            "returncode": None,
            "warning": None,
        }
        if command not in config.allowed_commands:
            result["warning"] = (
                f"command not allowed by config: {command!r}; "
                f"allowed_commands uses exact command strings: {config.allowed_commands!r}"
            )
        elif dry_run:
            result["ok"] = True
            result["warning"] = "dry-run: command not executed"
        else:
            args = shlex.split(command)
            if shutil.which(args[0]) is None:
                result["warning"] = f"command unavailable: {args[0]}"
                results.append(result)
                continue
            completed = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
            with stdout_log.open("a") as stdout:
                stdout.write(completed.stdout)
            with stderr_log.open("a") as stderr:
                stderr.write(completed.stderr)
            result["ok"] = completed.returncode == 0
            result["returncode"] = completed.returncode
            if not result["ok"] and not required:
                result["warning"] = "optional gate failed"
        results.append(result)

    (run_dir / "gate_results.json").write_text(json.dumps(results, indent=2) + "\n")
    return results
