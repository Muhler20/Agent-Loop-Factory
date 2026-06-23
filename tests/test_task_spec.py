import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.task_spec import inline_task_spec, load_task_spec


ROOT = Path(__file__).resolve().parents[1]


class TaskSpecTests(unittest.TestCase):
    def test_load_task_spec_reads_markdown_title_body_and_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "task.md"
            path.write_text("# Fix sample add\n\n## Goal\n\nFix it.\n")

            spec = load_task_spec(path)

            self.assertEqual(spec.task_title, "Fix sample add")
            self.assertEqual(spec.task_body, path.read_text())
            self.assertEqual(spec.task_file_path, str(path))

    def test_load_task_spec_uses_first_non_empty_line_without_heading(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "task.md"
            path.write_text("\nFix sample add\n\nMore detail.\n")

            self.assertEqual(load_task_spec(path).task_title, "Fix sample add")

    def test_missing_task_file_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "missing.md"

            with self.assertRaisesRegex(ValueError, "task file does not exist"):
                load_task_spec(path)

    def test_empty_task_file_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "task.md"
            path.write_text("\n\n")

            with self.assertRaisesRegex(ValueError, "task spec is empty"):
                load_task_spec(path)

    def test_parses_allowed_files_from_markdown_bullets(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "task.md"
            path.write_text("# Task\n\n## Allowed files\n\n* sample_math/__init__.py\n* tests/\n\n## Gates\n\nRun tests.\n")

            self.assertEqual(load_task_spec(path).allowed_files, ["sample_math/__init__.py", "tests/"])

    def test_parses_forbidden_files_from_markdown_bullets(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "task.md"
            path.write_text("# Task\n\n## Forbidden files\n\n* tests/\n* pyproject.toml\n")

            self.assertEqual(load_task_spec(path).forbidden_files, ["tests/", "pyproject.toml"])

    def test_strips_backticks_around_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "task.md"
            path.write_text("# Task\n\n## Allowed files\n\n* `sample_math/__init__.py`\n\n## Forbidden files\n\n* `tests/`\n")

            spec = load_task_spec(path)

            self.assertEqual(spec.allowed_files, ["sample_math/__init__.py"])
            self.assertEqual(spec.forbidden_files, ["tests/"])

    def test_missing_sections_return_empty_lists(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "task.md"
            path.write_text("# Task\n\n## Goal\n\nFix it.\n")

            spec = load_task_spec(path)

            self.assertEqual(spec.allowed_files, [])
            self.assertEqual(spec.forbidden_files, [])

    def test_inline_task_has_empty_allowed_and_forbidden_lists(self) -> None:
        spec = inline_task_spec("Fix it")

        self.assertEqual(spec.allowed_files, [])
        self.assertEqual(spec.forbidden_files, [])

    def test_cli_rejects_both_task_inputs(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/run_agent_loop.py", "--task", "x", "--task-file", "tasks/fix-sample-add.md"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not allowed with argument", result.stderr)

    def test_cli_rejects_missing_task_input(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/run_agent_loop.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("one of the arguments --task --task-file is required", result.stderr)

    def test_cli_rejects_missing_task_file(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/run_agent_loop.py", "--task-file", "does-not-exist.md"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("task file does not exist", result.stderr)


if __name__ == "__main__":
    unittest.main()
