from __future__ import annotations

import subprocess
from pathlib import Path


def write_diff_summary(repo_path: Path, output_path: Path, max_lines: int, dry_run: bool = False) -> str:
    if dry_run:
        summary = "dry-run: diff not collected\n"
    else:
        try:
            tracked = subprocess.run(["git", "-C", str(repo_path), "diff", "--stat", "HEAD", "--"], capture_output=True, text=True, check=False)
            untracked = subprocess.run(["git", "-C", str(repo_path), "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True, check=False)
            if tracked.returncode != 0 or untracked.returncode != 0:
                summary = "diff summary failed\n"
            else:
                sections = []
                tracked_lines = tracked.stdout.splitlines()[:max_lines]
                untracked_lines = [line for line in untracked.stdout.splitlines() if line]
                if tracked_lines:
                    sections.append("Tracked diff:\n" + "\n".join(tracked_lines))
                if untracked_lines:
                    sections.append("Untracked files:\n" + "\n".join(f"- {line}" for line in untracked_lines))
                summary = "\n\n".join(sections) + ("\n" if sections else "No diff.\n")
        except OSError as exc:
            summary = f"diff summary failed: {exc}\n"
    output_path.write_text(summary)
    return summary
