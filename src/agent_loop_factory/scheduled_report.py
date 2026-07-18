from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .github_context import MAX_CI_LOG_BYTES, parse_repo
from .memory_registry import validate_memory_registry
from .report_config import ReportConfig, load_report_config

Clock = Callable[[], datetime]
Runner = Callable[..., subprocess.CompletedProcess]
SAFETY = {
    "report_only": True,
    "no_code_changes": True,
    "no_git_writes": True,
    "no_github_writes": True,
    "no_codex_implementer": True,
    "requires_human_action": True,
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def run_scheduled_report(
    repo_root: Path,
    config_path: Path | str,
    *,
    dry_run: bool = False,
    clock: Clock = utc_now,
    runner: Runner = subprocess.run,
) -> dict[str, object]:
    root = repo_root.resolve()
    config = load_report_config(root, config_path)
    created = clock()
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    created = created.astimezone(timezone.utc)
    report_id = f"{created.strftime('%Y%m%dT%H%M%SZ')}-{config.name}"
    report_dir = root / ".agent" / "reports" / report_id
    report_dir.mkdir(parents=True, exist_ok=False)

    result: dict[str, object] = {
        "report_id": report_id,
        "config_name": config.name,
        "config_path": config.path.relative_to(root).as_posix(),
        "cadence": config.cadence,
        "dry_run": dry_run,
        "enabled": config.enabled,
        **SAFETY,
        "report_types_requested": list(config.report_types),
        "report_types_completed": [],
        "report_types_failed": [],
        "artifacts": [],
        "human_attention_items": [],
        "created_at_utc": created.isoformat().replace("+00:00", "Z"),
    }
    if dry_run or not config.enabled:
        result["report_sections_skipped"] = True
        if not config.enabled:
            result["status"] = "disabled"
            result["human_attention_items"] = ["Report definition is disabled; no report sections ran."]
    else:
        for report_type in config.report_types:
            try:
                if report_type == "stale_runs":
                    section = write_stale_runs_report(root, report_dir, config.stale_runs_max)
                elif report_type == "memory_hygiene":
                    section = write_memory_hygiene_report(root, report_dir)
                else:
                    section = write_github_ci_report(report_dir, config.github_repo or "", config.ci_runs_limit, runner)
                result["report_types_completed"].append(report_type)
                result["artifacts"].extend(section["artifacts"])
                result["human_attention_items"].extend(section["human_attention_items"])
            except Exception as exc:  # section failures belong in the combined report
                result["report_types_failed"].append(report_type)
                result["human_attention_items"].append(f"{report_type}: {exc}")
    result["status"] = result.get("status") or ("failed" if result["report_types_failed"] else "ok_with_attention" if result["human_attention_items"] else "ok")
    result["artifacts"].extend(["scheduled_report.md", "scheduled_report.json"])
    _write_json(report_dir / "scheduled_report.json", result)
    (report_dir / "scheduled_report.md").write_text(_combined_markdown(config, result), encoding="utf-8")
    return result | {"report_dir": str(report_dir)}


def write_stale_runs_report(repo_root: Path, report_dir: Path, max_runs: int = 25) -> dict[str, object]:
    if isinstance(max_runs, bool) or not isinstance(max_runs, int) or not 1 <= max_runs <= 100:
        raise ValueError("max_runs must be an integer from 1 to 100")
    runs_dir = repo_root / ".agent" / "runs"
    runs = sorted((path for path in runs_dir.iterdir() if path.is_dir()), key=lambda path: path.name, reverse=True)[:max_runs] if runs_dir.is_dir() else []
    keys = {
        "runs_with_verifier_failed": [], "runs_with_handoff_needs_attention": [],
        "runs_with_memory_proposals": [], "runs_with_advisory_review": [],
        "runs_with_github_context": [], "runs_with_missing_expected_artifacts": [],
    }
    attention: list[str] = []
    expected = ("verifier_result.json", "pr_handoff_check.json")
    for run in runs:
        parsed: dict[str, object] = {}
        for filename in ("verifier_result.json", "pr_handoff_check.json", "memory_proposal.json", "advisory_review.json", "github_context_summary.json"):
            path = run / filename
            if not path.is_file():
                continue
            try:
                parsed[filename] = json.loads(path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                attention.append(f"{run.name}: malformed {filename}: {exc}")
        verifier = parsed.get("verifier_result.json")
        if isinstance(verifier, dict) and (verifier.get("ok") is False or verifier.get("status") in {"failed", "failure"}):
            keys["runs_with_verifier_failed"].append(run.name)
        handoff = parsed.get("pr_handoff_check.json")
        if isinstance(handoff, dict) and (handoff.get("needs_attention") is True or handoff.get("status") == "needs_attention"):
            keys["runs_with_handoff_needs_attention"].append(run.name)
        for filename, key in (("memory_proposal.json", "runs_with_memory_proposals"), ("advisory_review.json", "runs_with_advisory_review"), ("github_context_summary.json", "runs_with_github_context")):
            if filename in parsed:
                keys[key].append(run.name)
        missing = [name for name in expected if not (run / name).is_file()]
        if missing:
            keys["runs_with_missing_expected_artifacts"].append({"run_id": run.name, "missing": missing})
    for key, value in keys.items():
        if value and key != "runs_with_missing_expected_artifacts":
            attention.append(f"{key}: {len(value)} run(s)")
    data = {"latest_run_id": runs[0].name if runs else None, "scanned_run_count": len(runs), "max_runs": max_runs, **keys, "human_attention_items": attention}
    _write_json(report_dir / "stale_runs_report.json", data)
    (report_dir / "stale_runs_report.md").write_text(_section_markdown("Stale Runs Report", data), encoding="utf-8")
    return {"artifacts": ["stale_runs_report.md", "stale_runs_report.json"], "human_attention_items": attention}


def write_memory_hygiene_report(repo_root: Path, report_dir: Path) -> dict[str, object]:
    result = validate_memory_registry(repo_root)
    status = "invalid" if result.errors else "ok_with_warnings" if result.warnings else "ok"
    attention = [*result.errors, *result.warnings]
    data = {"status": status, "warnings_count": len(result.warnings), "errors_count": len(result.errors), "summary": f"Memory registry {status.replace('_', ' ')}.", "warnings": result.warnings, "errors": result.errors, "human_attention_items": attention}
    _write_json(report_dir / "memory_hygiene_report.json", data)
    (report_dir / "memory_hygiene_report.md").write_text(_section_markdown("Memory Hygiene Report", data), encoding="utf-8")
    return {"artifacts": ["memory_hygiene_report.md", "memory_hygiene_report.json"], "human_attention_items": attention}


def write_github_ci_report(report_dir: Path, repo: str, limit: int = 5, runner: Runner = subprocess.run) -> dict[str, object]:
    parse_repo(repo)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
        raise ValueError("limit must be an integer from 1 to 20")
    command = ["gh", "run", "list", "--repo", repo, "--limit", str(limit)]
    try:
        completed = runner(command, capture_output=True, check=False, shell=False)
        code = completed.returncode
        stdout, stderr = _bytes(completed.stdout), _bytes(completed.stderr)
        available = True
    except OSError as exc:
        code, stdout, stderr, available = None, b"", str(exc).encode(), False
    stdout_included, stdout_truncated = stdout[:MAX_CI_LOG_BYTES], len(stdout) > MAX_CI_LOG_BYTES
    stderr_included, stderr_truncated = stderr[:MAX_CI_LOG_BYTES], len(stderr) > MAX_CI_LOG_BYTES
    (report_dir / "github_ci_stdout.log").write_bytes(stdout_included)
    (report_dir / "github_ci_stderr.log").write_bytes(stderr_included)
    attention = [] if code == 0 else ["GitHub CI could not be read; inspect github_ci_stderr.log."]
    recent = stdout_included.decode("utf-8", errors="replace").splitlines() if code == 0 else []
    data = {"repo": repo, "limit": limit, "gh_available": available, "command_return_code": code, "raw_stdout_path": "github_ci_stdout.log", "raw_stderr_path": "github_ci_stderr.log", "recent_runs": recent, "status": "ok" if code == 0 else "unavailable", "stdout_original_bytes": len(stdout), "stdout_included_bytes": len(stdout_included), "stdout_truncated": stdout_truncated, "stderr_original_bytes": len(stderr), "stderr_included_bytes": len(stderr_included), "stderr_truncated": stderr_truncated, "human_attention_items": attention}
    _write_json(report_dir / "github_ci_report.json", data)
    (report_dir / "github_ci_report.md").write_text(_section_markdown("GitHub CI Report", data), encoding="utf-8")
    return {"artifacts": ["github_ci_report.md", "github_ci_report.json", "github_ci_stdout.log", "github_ci_stderr.log"], "human_attention_items": attention}


def _combined_markdown(config: ReportConfig, result: dict[str, object]) -> str:
    completed = "\n".join(f"- {item}" for item in result["report_types_completed"]) or "- None"
    artifacts = "\n".join(f"- {item}" for item in result["artifacts"])
    attention = "\n".join(f"- {item}" for item in result["human_attention_items"]) or "- None"
    return f"""# Scheduled Report: {config.name}

Status: {result['status']}

## Safety Notice

Report-only; no code, memory, git, GitHub, or Codex implementer writes are authorized.

## Config Summary

- Description: {config.description}
- Cadence: {config.cadence} (metadata only)
- Enabled: {config.enabled}
- Dry run: {result['dry_run']}

## Report Sections Completed

{completed}

## Artifacts

{artifacts}

## Human Attention Items

{attention}

## Non-authority Notice

This is a report only. It does not modify code. It does not modify memory. It does not write to GitHub. It does not call Codex as an implementer. A human must decide any next action.
"""


def _section_markdown(title: str, data: dict[str, object]) -> str:
    attention = "\n".join(f"- {item}" for item in data["human_attention_items"]) or "- None"
    summary = data.get("summary", data.get("status", "ok"))
    return f"# {title}\n\n{summary}\n\n## Human Attention Items\n\n{attention}\n"


def _write_json(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _bytes(value: bytes | str | None) -> bytes:
    if value is None:
        return b""
    return value.encode() if isinstance(value, str) else value


run_report = run_scheduled_report
