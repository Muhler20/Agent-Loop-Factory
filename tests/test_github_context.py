import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.github_context import (
    MAX_CI_LOG_BYTES,
    fetch_github_context,
    parse_issue_ref,
    parse_repo,
    parse_run_id,
    validate_github_flags,
)


class GitHubContextTests(unittest.TestCase):
    def test_identifier_validation_accepts_valid_values(self) -> None:
        self.assertEqual(parse_issue_ref("Muhler20/Agent-Loop-Factory#12"), ("Muhler20", "Agent-Loop-Factory", "12"))
        self.assertEqual(parse_repo("Muhler20/Agent-Loop_Factory"), ("Muhler20", "Agent-Loop_Factory"))
        self.assertEqual(parse_run_id("123456789"), "123456789")

    def test_identifier_validation_rejects_invalid_values(self) -> None:
        invalid_issues = [
            "Muhler20/Agent-Loop-Factory",
            "Muhler20/Agent-Loop-Factory/issues/12",
            "https://github.com/Muhler20/Agent-Loop-Factory/issues/12",
            "Muhler20/Agent-Loop-Factory#abc",
            "owner/repo#1;rm -rf .",
            "../repo#1",
        ]
        for value in invalid_issues:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_issue_ref(value)
        for value in ["owner", "owner/repo/extra", "../repo"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_repo(value)
        for value in ["abc", "123abc", "1;rm"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_run_id(value)

    def test_ci_run_requires_repo(self) -> None:
        with self.assertRaisesRegex(ValueError, "--github-repo is required"):
            validate_github_flags(None, None, "123")

    def test_issue_fetch_uses_only_allowed_command_and_writes_artifacts(self) -> None:
        calls = []

        def fake_runner(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, b"Issue body\n", b"")

        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            context, summary = fetch_github_context(run_dir, "run-1", issue_ref="owner/repo#1", runner=fake_runner)

            self.assertEqual(calls, [["gh", "issue", "view", "owner/repo#1"]])
            self.assertTrue(context.included)
            self.assertEqual((run_dir / "github_issue_context.md").read_text().count("Issue body"), 1)
            issue_json = json.loads((run_dir / "github_issue_context.json").read_text())
            summary_json = json.loads((run_dir / "github_context_summary.json").read_text())
            self.assertTrue(issue_json["read_only"])
            self.assertTrue(issue_json["no_github_writes"])
            self.assertTrue(summary_json["read_only"])
            self.assertTrue(summary_json["no_github_writes"])
            self.assertIn("github_issue_context.md", summary["artifacts"])

    def test_ci_fetch_uses_only_allowed_commands_and_writes_artifacts(self) -> None:
        calls = []

        def fake_runner(command, **kwargs):
            calls.append(command)
            stdout = b"metadata\n" if "--log" not in command else b"log\n"
            return subprocess.CompletedProcess(command, 0, stdout, b"")

        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            fetch_github_context(run_dir, "run-1", repo_ref="owner/repo", ci_run="123", runner=fake_runner)

            self.assertEqual(calls, [
                ["gh", "run", "view", "123", "--repo", "owner/repo"],
                ["gh", "run", "view", "123", "--repo", "owner/repo", "--log"],
            ])
            self.assertEqual((run_dir / "github_ci_context.log").read_text(), "log\n")
            ci_json = json.loads((run_dir / "github_ci_context.json").read_text())
            self.assertTrue(ci_json["read_only"])
            self.assertTrue(ci_json["no_github_writes"])
            self.assertFalse(ci_json["log_truncated"])

    def test_ci_log_is_tail_truncated(self) -> None:
        head = b"h" * 100
        tail = b"t" * MAX_CI_LOG_BYTES
        log = head + tail

        def fake_runner(command, **kwargs):
            stdout = b"metadata\n" if "--log" not in command else log
            return subprocess.CompletedProcess(command, 0, stdout, b"")

        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            fetch_github_context(run_dir, "run-1", repo_ref="owner/repo", ci_run="123", runner=fake_runner)
            ci_log = (run_dir / "github_ci_context.log").read_bytes()
            ci_json = json.loads((run_dir / "github_ci_context.json").read_text())

            self.assertEqual(ci_log, tail)
            self.assertTrue(ci_json["log_truncated"])
            self.assertEqual(ci_json["truncation_strategy"], "tail")
            self.assertEqual(ci_json["original_log_bytes"], len(log))
            self.assertEqual(ci_json["included_log_bytes"], MAX_CI_LOG_BYTES)

    def test_gh_failure_fails_clearly(self) -> None:
        def fake_runner(command, **kwargs):
            return subprocess.CompletedProcess(command, 1, b"", b"auth failed\n")

        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "gh returned 1: auth failed"):
                fetch_github_context(Path(raw), "run-1", issue_ref="owner/repo#1", runner=fake_runner)


if __name__ == "__main__":
    unittest.main()
