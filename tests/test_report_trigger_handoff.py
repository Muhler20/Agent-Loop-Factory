import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_loop_factory.report_config import load_report_config
from agent_loop_factory.report_trigger_handoff import generate_report_trigger_handoff

SAFETY = {key: True for key in ("report_only", "no_code_changes", "no_git_writes", "no_github_writes", "no_codex_implementer", "requires_human_action")}
CLOCK = lambda: datetime(2026, 7, 18, 8, tzinfo=timezone.utc)


def config(root, **changes):
    data = {"name": "test", "description": "Test.", "cadence": "daily", "enabled": True, "report_types": ["stale_runs"], "trigger_hints": {"local_time": "08:00", "utc_time": "13:00"}, "safety": SAFETY}
    data.update(changes)
    path = root / "report_configs" / "test.json"
    path.parent.mkdir()
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class TriggerHintValidationTests(unittest.TestCase):
    def test_optional_and_valid_hints(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.assertEqual(load_report_config(root, config(root, trigger_hints={})).trigger_hints, {})

    def test_invalid_hints(self):
        cases = [
            ({"local_time": "8:00"}, "local_time"),
            ({"utc_time": "24:00"}, "utc_time"),
            ({"weekday": "Mon"}, "weekday"),
            ({"day_of_month": 29}, "day_of_month"),
            ({"timezone": "UTC"}, "unknown"),
        ]
        for hints, message in cases:
            with self.subTest(hints=hints), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                with self.assertRaisesRegex(ValueError, message):
                    load_report_config(root, config(root, trigger_hints=hints))

    def test_documented_configs_validate(self):
        for path in (ROOT / "report_configs").glob("*.json"):
            load_report_config(ROOT, path)


class HandoffTests(unittest.TestCase):
    def test_targets_write_only_expected_files(self):
        expected = {
            "manual": set(),
            "cron": {"cron_entry.txt"},
            "systemd-user": {"systemd_user_service.txt", "systemd_user_timer.txt"},
            "github-actions": {"github_actions_workflow.yml.txt"},
        }
        for target, target_files in expected.items():
            with self.subTest(target=target), tempfile.TemporaryDirectory() as raw:
                root = Path(raw); path = config(root)
                result = generate_report_trigger_handoff(root, path, target, clock=CLOCK)
                directory = Path(result["handoff_dir"])
                self.assertEqual({p.name for p in directory.iterdir()}, {"trigger_handoff.md", "trigger_handoff.json", "manual_command.txt", *target_files})
                self.assertEqual(result["handoff_id"], f"20260718T080000Z-test-{target}")
                markdown = (directory / "trigger_handoff.md").read_text()
                self.assertIn("Nothing was installed", markdown)
                self.assertIn("human must review and install", markdown)
                receipt = json.loads((directory / "trigger_handoff.json").read_text())
                self.assertTrue(all(receipt[key] for key in ("handoff_only", "not_installed", "external_trigger_only", "no_github_writes", "no_worktrees", "no_memory_mutation")))
                if target in {"cron", "systemd-user"}:
                    self.assertIn("local", markdown.lower())
                if target == "github-actions":
                    self.assertIn("UTC", markdown)
                    self.assertFalse((root / ".github" / "workflows").exists())

    def test_disabled_and_manual_cadence_have_no_scheduled_snippet(self):
        for changes in ({"enabled": False}, {"cadence": "manual", "trigger_hints": {}}):
            with tempfile.TemporaryDirectory() as raw:
                root = Path(raw); path = config(root, **changes)
                result = generate_report_trigger_handoff(root, path, "cron", clock=CLOCK)
                self.assertFalse(result["active_trigger_generated"])
                self.assertFalse((Path(result["handoff_dir"]) / "cron_entry.txt").exists())

    def test_required_timing_fails_before_artifacts(self):
        cases = [
            ("cron", "daily", {}, "local_time"),
            ("github-actions", "daily", {}, "utc_time"),
            ("cron", "weekly", {"local_time": "08:00"}, "weekday"),
            ("cron", "monthly", {"local_time": "08:00"}, "day_of_month"),
        ]
        for target, cadence, hints, message in cases:
            with self.subTest(target=target, cadence=cadence), tempfile.TemporaryDirectory() as raw:
                root = Path(raw); path = config(root, cadence=cadence, trigger_hints=hints)
                with self.assertRaisesRegex(ValueError, message):
                    generate_report_trigger_handoff(root, path, target, clock=CLOCK)
                self.assertFalse((root / ".agent").exists())

    def test_command_quotes_repo_root(self):
        with tempfile.TemporaryDirectory(prefix="repo with space ") as raw:
            root = Path(raw); path = config(root)
            result = generate_report_trigger_handoff(root, path, "manual", clock=CLOCK)
            self.assertIn("cd '", result["report_command"])

    def test_cli_list_and_errors(self):
        script = ROOT / "scripts" / "generate_report_trigger_handoff.py"
        listed = subprocess.run([sys.executable, script, "--list-targets"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(listed.returncode, 0)
        self.assertIn("github-actions", listed.stdout)
        invalid = subprocess.run([sys.executable, script, "--config", "outside.json", "--target", "manual"], cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(invalid.returncode, 0)


if __name__ == "__main__":
    unittest.main()
