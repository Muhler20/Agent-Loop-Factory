# Report Definitions

These human-authored JSON files define manually invoked, read-only reports. Run one with
`python3 scripts/run_scheduled_reports.py --config report_configs/daily-health.json`.

`report_configs/` is the only durable definition directory. `cadence` and optional `trigger_hints` are metadata only. Nothing here installs or manages a scheduler. Use explicit `local_time` for cron/systemd-user handoffs and `utc_time` for GitHub Actions handoffs; no 08:00 default is assumed.

Generated reports go under `.agent/reports/`. Generate instructions with `python3 scripts/generate_report_trigger_handoff.py --config report_configs/daily-health.json --target cron`; handoffs go under `.agent/report_handoffs/` and require human review and manual installation.
