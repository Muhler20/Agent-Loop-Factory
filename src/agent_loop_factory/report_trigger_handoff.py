from __future__ import annotations

import json
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .report_config import ReportConfig, load_report_config

TARGETS = ("manual", "cron", "systemd-user", "github-actions")
Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_report_trigger_handoff(
    repo_root: Path, config_path: Path | str, target: str, *, clock: Clock = utc_now
) -> dict[str, object]:
    root = repo_root.resolve()
    config = load_report_config(root, config_path)
    if target not in TARGETS:
        raise ValueError(f"target must be one of: {', '.join(TARGETS)}")
    active = config.enabled and (target == "manual" or config.cadence != "manual")
    if active and target != "manual":
        _validate_timing(config, target)

    created = clock()
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    created = created.astimezone(timezone.utc)
    handoff_id = f"{created.strftime('%Y%m%dT%H%M%SZ')}-{config.name}-{target}"
    handoff_dir = root / ".agent" / "report_handoffs" / handoff_id
    handoff_dir.mkdir(parents=True, exist_ok=False)
    relative_config = config.path.relative_to(root).as_posix()
    command = f"cd {shlex.quote(str(root))} && python3 scripts/run_scheduled_reports.py --config {shlex.quote(relative_config)}"
    snippets = _snippets(config, target, command) if active else {}
    files = {"manual_command.txt": command + "\n", **snippets}
    for name, content in files.items():
        (handoff_dir / name).write_text(content, encoding="utf-8")

    artifact_names = ["trigger_handoff.md", "trigger_handoff.json", *files]
    timezone_notice = _timezone_notice(target)
    result: dict[str, object] = {
        "handoff_id": handoff_id,
        "config_name": config.name,
        "config_path": relative_config,
        "target": target,
        "cadence": config.cadence,
        "config_enabled": config.enabled,
        "active_trigger_generated": active,
        "handoff_only": True,
        "not_installed": True,
        "external_trigger_only": True,
        "requires_human_installation": True,
        "report_only": True,
        "no_code_changes": True,
        "no_git_writes": True,
        "no_github_writes": True,
        "no_codex_implementer": True,
        "no_worktrees": True,
        "no_memory_mutation": True,
        "report_command": command,
        "artifact_paths": artifact_names,
        "trigger_hints_used": config.trigger_hints,
        "timezone_notice": timezone_notice,
        "created_at_utc": created.isoformat().replace("+00:00", "Z"),
    }
    (handoff_dir / "trigger_handoff.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (handoff_dir / "trigger_handoff.md").write_text(_markdown(config, result, snippets), encoding="utf-8")
    return result | {"handoff_dir": str(handoff_dir)}


def _validate_timing(config: ReportConfig, target: str) -> None:
    time_field = "utc_time" if target == "github-actions" else "local_time"
    required = [time_field]
    if config.cadence == "weekly":
        required.append("weekday")
    elif config.cadence == "monthly":
        required.append("day_of_month")
    missing = [field for field in required if field not in config.trigger_hints]
    if missing:
        raise ValueError(f"{target} {config.cadence} trigger requires trigger_hints.{missing[0]}")


def _schedule(config: ReportConfig, target: str) -> tuple[str, str, str]:
    field = "utc_time" if target == "github-actions" else "local_time"
    hour, minute = str(config.trigger_hints[field]).split(":")
    if config.cadence == "daily":
        return minute, hour, "* *"
    if config.cadence == "weekly":
        day = str(config.trigger_hints["weekday"])
        return minute, hour, f"* {day}"
    return minute, hour, f"{config.trigger_hints['day_of_month']} *"


def _snippets(config: ReportConfig, target: str, command: str) -> dict[str, str]:
    if target == "manual":
        return {}
    minute, hour, ending = _schedule(config, target)
    if target == "cron":
        weekday = ending.split()[1]
        cron_day = {"sunday": 0, "monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4, "friday": 5, "saturday": 6}.get(weekday, "*")
        dom = ending.split()[0]
        return {"cron_entry.txt": f"# Handoff only; not installed. Time is local to the cron machine. Edit timing before manual installation.\n{minute} {hour} {dom} * {cron_day} {command}\n"}
    if target == "systemd-user":
        if config.cadence == "daily":
            calendar = f"*-*-* {hour}:{minute}:00"
        elif config.cadence == "weekly":
            calendar = f"{config.trigger_hints['weekday'].title()} *-*-* {hour}:{minute}:00"
        else:
            calendar = f"*-*-{int(config.trigger_hints['day_of_month']):02d} {hour}:{minute}:00"
        service = f"# Handoff only; not installed.\n[Unit]\nDescription=Agent Loop Factory report: {config.name}\n\n[Service]\nType=oneshot\nExecStart=/bin/sh -lc {shlex.quote(command)}\n"
        timer = f"# Handoff only; not installed. Time is local to the user systemd timer environment.\n[Unit]\nDescription=Trigger Agent Loop Factory report: {config.name}\n\n[Timer]\nOnCalendar={calendar}\nPersistent=false\n\n[Install]\nWantedBy=timers.target\n"
        return {"systemd_user_service.txt": service, "systemd_user_timer.txt": timer}
    cron = f"{minute} {hour} {ending.split()[0]} * { {'sunday': 0, 'monday': 1, 'tuesday': 2, 'wednesday': 3, 'thursday': 4, 'friday': 5, 'saturday': 6}.get(ending.split()[1], '*') }"
    config_path = f"report_configs/{config.path.name}"
    workflow = f"# Handoff only; not installed. GitHub Actions cron uses UTC.\nname: Agent Loop Factory report - {config.name}\non:\n  schedule:\n    - cron: {json.dumps(cron)}\n  workflow_dispatch:\n\njobs:\n  report:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - name: Run report\n        run: python3 scripts/run_scheduled_reports.py --config {shlex.quote(config_path)}\n"
    return {"github_actions_workflow.yml.txt": workflow}


def _timezone_notice(target: str) -> str:
    if target == "github-actions":
        return "GitHub Actions cron uses UTC."
    if target in {"cron", "systemd-user"}:
        return "Time is local to the machine or user timer environment running the trigger."
    return "Manual execution has no scheduled timezone semantics."


def _markdown(config: ReportConfig, result: dict[str, object], snippets: dict[str, str]) -> str:
    hints = "\n".join(f"- {key}: {value}" for key, value in config.trigger_hints.items()) or "- None"
    artifacts = "\n".join(f"- {name}" for name in result["artifact_paths"])
    snippet = "\n\n".join(f"### {name}\n\n```\n{body.rstrip()}\n```" for name, body in snippets.items()) or "No active target-specific snippet was generated."
    disabled = "\n- Installing this trigger is not recommended.\n- Enable the report config first if the human wants an active trigger." if not config.enabled else ""
    return f"""# Report Trigger Handoff: {config.name}

Status: handoff only; not installed

## Config Summary

- config enabled: {str(config.enabled).lower()}
- active trigger generated: {str(result['active_trigger_generated']).lower()}
- Target: {result['target']}
- Cadence: {config.cadence} (metadata unless a human installs an external trigger){disabled}

## Trigger Hints Used

{hints}

## Timezone Notice

{result['timezone_notice']}

## Exact Report Command

```sh
{result['report_command']}
```

## Target-Specific Snippet

{snippet}

## Artifacts

{artifacts}

## Installation Checklist

- Review the config, command, timing, timezone, and target snippet.
- Manually copy and install the snippet only if it is appropriate.
- Confirm the external trigger environment can access this repository.

## Disable / Uninstall Notes

Disable or remove the externally installed trigger using that platform's normal manual process. This handoff does not manage installed triggers.

## Safety Notice

This output is report-only and creates no code, git, GitHub, Codex, worktree, or memory writes.

## Non-authority Notice

- This handoff is instructions only.
- Nothing was installed.
- Nothing was scheduled by Agent Loop Factory.
- No report was run by this command.
- No code was modified.
- No memory was modified.
- No GitHub writes occurred.
- A human must review and install any external trigger manually.
"""
