import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.context_intake import MAX_CONTEXT_BYTES, load_context


class ContextIntakeTests(unittest.TestCase):
    def test_loads_issue_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            issue = Path(raw) / "issue.md"
            issue.write_text("Issue body\n")

            context = load_context(issue_file=issue)

            self.assertEqual(context.issue_file_path, str(issue))
            self.assertEqual(context.issue_body, "Issue body\n")
            self.assertEqual(context.issue_size_bytes, len("Issue body\n"))
            self.assertIsNone(context.ci_log_body)

    def test_loads_ci_log_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            ci = Path(raw) / "ci.log"
            ci.write_text("FAILED test_add\n")

            context = load_context(ci_log_file=ci)

            self.assertEqual(context.ci_log_file_path, str(ci))
            self.assertEqual(context.ci_log_body, "FAILED test_add\n")
            self.assertEqual(context.ci_log_size_bytes, len("FAILED test_add\n"))
            self.assertIsNone(context.issue_body)

    def test_loads_both_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            issue = Path(raw) / "issue.md"
            ci = Path(raw) / "ci.log"
            issue.write_text("Issue\n")
            ci.write_text("CI\n")

            context = load_context(issue, ci)

            self.assertEqual(context.issue_body, "Issue\n")
            self.assertEqual(context.ci_log_body, "CI\n")

    def test_missing_file_fails_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not exist"):
            load_context(issue_file=Path("/tmp/no-such-agent-loop-context-file"))

    def test_directory_path_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "is not a file"):
                load_context(issue_file=Path(raw))

    def test_empty_file_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            issue = Path(raw) / "issue.md"
            issue.write_text("")
            with self.assertRaisesRegex(ValueError, "is empty"):
                load_context(issue_file=issue)

    def test_too_large_file_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            issue = Path(raw) / "issue.md"
            issue.write_bytes(b"x" * (MAX_CONTEXT_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "is too large"):
                load_context(issue_file=issue)

    def test_invalid_utf8_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            issue = Path(raw) / "issue.md"
            issue.write_bytes(b"\xff")
            with self.assertRaisesRegex(ValueError, "valid UTF-8"):
                load_context(issue_file=issue)

    def test_no_context_files_works(self) -> None:
        context = load_context()

        self.assertIsNone(context.issue_file_path)
        self.assertIsNone(context.issue_body)
        self.assertIsNone(context.ci_log_file_path)
        self.assertIsNone(context.ci_log_body)


if __name__ == "__main__":
    unittest.main()
