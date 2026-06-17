from __future__ import annotations

import subprocess
from pathlib import Path


def write_diff_summary(repo_path: Path, output_path: Path, max_lines: int, dry_run: bool = False) -> str:
    if dry_run:
        summary = "dry-run: diff not collected\n"
    else:
        try:
            completed = subprocess.run(["git", "-C", str(repo_path), "diff", "--stat"], capture_output=True, text=True, check=False)
            lines = completed.stdout.splitlines()[:max_lines]
            summary = "\n".join(lines) + ("\n" if lines else "No diff.\n")
        except OSError as exc:
            summary = f"diff summary failed: {exc}\n"
    output_path.write_text(summary)
    return summary
