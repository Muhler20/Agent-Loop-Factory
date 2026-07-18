import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.report_config import load_report_config
from agent_loop_factory.scheduled_report import run_scheduled_report, write_github_ci_report, write_stale_runs_report


SAFETY = {key: True for key in ("report_only", "no_code_changes", "no_git_writes", "no_github_writes", "no_codex_implementer", "requires_human_action")}


def config(root, **changes):
    data = {"name": "test", "description": "Test report.", "cadence": "manual", "enabled": True, "report_types": ["stale_runs"], "safety": SAFETY}
    data.update(changes)
    path = root / "report_configs" / "test.json"
    path.parent.mkdir()
    path.write_text(json.dumps(data))
    return path


class ReportTests(unittest.TestCase):
    def test_validation_and_dry_run_are_bounded(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); path = config(root)
            self.assertEqual(load_report_config(root, path).stale_runs_max, 25)
            calls = []
            result = run_scheduled_report(root, path, dry_run=True, clock=lambda: datetime(2026, 7, 18, 8, tzinfo=timezone.utc), runner=lambda *a, **k: calls.append(a))
            self.assertEqual(result["report_id"], "20260718T080000Z-test")
            receipt = json.loads((Path(result["report_dir"]) / "scheduled_report.json").read_text())
            self.assertTrue(receipt["report_sections_skipped"])
            self.assertTrue(receipt["no_github_writes"])
            self.assertEqual(calls, [])

    def test_invalid_config_fails_before_artifact(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); path = config(root, safety={})
            with self.assertRaises(ValueError):
                run_scheduled_report(root, path)
            self.assertFalse((root / ".agent").exists())

    def test_disabled_writes_receipt(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); path = config(root, enabled=False)
            result = run_scheduled_report(root, path, clock=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
            self.assertEqual(result["status"], "disabled")
            self.assertTrue((Path(result["report_dir"]) / "scheduled_report.md").is_file())

    def test_stale_runs_is_limited_and_tolerates_bad_json(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); report = root / "out"; report.mkdir()
            for name in ("a", "b", "c"):
                (root / ".agent" / "runs" / name).mkdir(parents=True)
            (root / ".agent" / "runs" / "c" / "verifier_result.json").write_text("{")
            result = write_stale_runs_report(root, report, 2)
            data = json.loads((report / "stale_runs_report.json").read_text())
            self.assertEqual((data["latest_run_id"], data["scanned_run_count"]), ("c", 2))
            self.assertTrue(data["human_attention_items"])
            self.assertIn("stale_runs_report.json", result["artifacts"])

    def test_github_ci_uses_read_only_argv_and_truncates(self):
        calls = []
        def runner(argv, **kwargs):
            calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, b"x" * 60000, b"")
        with tempfile.TemporaryDirectory() as raw:
            report = Path(raw)
            write_github_ci_report(report, "owner/repo", 3, runner)
            data = json.loads((report / "github_ci_report.json").read_text())
            self.assertEqual(calls[0][0], ["gh", "run", "list", "--repo", "owner/repo", "--limit", "3"])
            self.assertFalse(calls[0][1]["shell"])
            self.assertTrue(data["stdout_truncated"])
            self.assertEqual(data["stdout_included_bytes"], 51200)


if __name__ == "__main__":
    unittest.main()
