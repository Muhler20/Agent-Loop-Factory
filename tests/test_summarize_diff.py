import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.config import Config
from agent_loop_factory.create_worktree import WorktreeResult
from agent_loop_factory.orchestrator import _report
from agent_loop_factory.summarize_diff import write_diff_summary
from agent_loop_factory.task_spec import inline_task_spec


class SummarizeDiffTests(unittest.TestCase):
    def test_no_changes_says_no_diff(self) -> None:
        with repo() as tmp:
            summary = write_diff_summary(tmp, tmp / "diff_summary.md", 500)
            self.assertEqual(summary, "No diff.\n")

    def test_tracked_change_appears(self) -> None:
        with repo() as tmp:
            (tmp / "app.py").write_text("print('hello')\n")
            summary = write_diff_summary(tmp, tmp / "diff_summary.md", 500)
            self.assertIn("Tracked diff:", summary)
            self.assertIn("app.py", summary)

    def test_untracked_file_appears(self) -> None:
        with repo() as tmp:
            (tmp / "new_file.py").write_text("print('new')\n")
            summary = write_diff_summary(tmp, tmp / "diff_summary.md", 500)
            self.assertIn("Untracked files:", summary)
            self.assertIn("- new_file.py", summary)

    def test_untracked_only_change_does_not_say_no_diff(self) -> None:
        with repo() as tmp:
            (tmp / "new_file.py").write_text("print('new')\n")
            summary = write_diff_summary(tmp, tmp / "diff_summary.md", 500)
            self.assertNotIn("No diff.", summary)

    def test_run_report_includes_untracked_summary(self) -> None:
        diff_summary = "Untracked files:\n- new_file.py\n"
        report = _report(
            inline_task_spec("test task"),
            None,
            "run-1",
            False,
            "none",
            None,
            Config(),
            WorktreeResult(True, "agent/run-1", Path("/tmp/worktree"), "ok"),
            [],
            {
                "ok": True,
                "reasons": [],
                "warnings": [],
                "changed_file_count": 1,
                "diff_line_count": 1,
                "tests_weakened_or_deleted": False,
                "human_required_touched": [],
                "task_allowed_files": [],
                "task_forbidden_files": [],
                "task_allowed_violations": [],
                "task_forbidden_touched": [],
            },
            diff_summary,
            True,
        )

        self.assertIn("Untracked files:\n- new_file.py", report)


class repo:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()

    def __enter__(self) -> Path:
        path = Path(self.tmp.__enter__())
        git(path, "init")
        (path / "app.py").write_text("print('hi')\n")
        git(path, "add", ".")
        git(path, "-c", "user.email=a@example.com", "-c", "user.name=A", "commit", "-m", "init")
        return path

    def __exit__(self, *exc) -> None:
        self.tmp.__exit__(*exc)


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
