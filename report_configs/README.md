# Report Definitions

These human-authored JSON files define manually invoked, read-only reports. Run one with
`python3 scripts/run_scheduled_reports.py --config report_configs/daily-health.json`.

`cadence` is descriptive metadata only. Nothing here installs or manages a scheduler.
Generated artifacts are written under `.agent/reports/`.
