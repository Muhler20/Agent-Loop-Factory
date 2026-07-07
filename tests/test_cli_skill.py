import contextlib
import importlib.util
import io
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_cli_module():
    spec = importlib.util.spec_from_file_location("run_agent_loop_cli", ROOT / "scripts" / "run_agent_loop.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CliSkillTests(unittest.TestCase):
    def test_skill_works_with_task_file(self) -> None:
        module = load_cli_module()
        calls = []

        def fake_run(*args, **kwargs):
            calls.append((args, kwargs))
            return {"run_id": "test-run", "run_dir": "/tmp/test-run", "ok": False, "dry_run": True}

        old_argv = sys.argv
        module.run = fake_run
        sys.argv = [
            "run_agent_loop.py",
            "--task-file",
            "tasks/fix-sample-add.md",
            "--skill",
            "failing-test-fix",
            "--implementer",
            "codex",
            "--dry-run",
        ]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                code = module.main()
        finally:
            sys.argv = old_argv

        self.assertEqual(code, 0)
        self.assertEqual(calls[0][1]["implementer"], "codex")
        self.assertEqual(calls[0][1]["skill"].skill_name, "failing-test-fix")
        self.assertEqual(calls[0][1]["task_file_path"], "tasks/fix-sample-add.md")

    def test_context_flags_are_passed_to_run(self) -> None:
        module = load_cli_module()
        calls = []

        def fake_run(*args, **kwargs):
            calls.append((args, kwargs))
            return {"run_id": "test-run", "run_dir": "/tmp/test-run", "ok": False, "dry_run": True}

        old_argv = sys.argv
        module.run = fake_run
        sys.argv = [
            "run_agent_loop.py",
            "--task",
            "fix add",
            "--issue-file",
            "examples/issues/fix-sample-add.md",
            "--ci-log-file",
            "examples/ci/failing-unit-test.log",
            "--dry-run",
        ]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                code = module.main()
        finally:
            sys.argv = old_argv

        self.assertEqual(code, 0)
        self.assertIn("sample_math.add", calls[0][1]["context"].issue_body)
        self.assertIn("AssertionError", calls[0][1]["context"].ci_log_body)

    def test_missing_skill_exits_clearly(self) -> None:
        module = load_cli_module()

        def fake_run(*args, **kwargs):
            raise AssertionError("run should not be called")

        old_argv = sys.argv
        module.run = fake_run
        sys.argv = ["run_agent_loop.py", "--task", "x", "--skill", "missing"]
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as exc:
                module.main()
        finally:
            sys.argv = old_argv

        self.assertEqual(exc.exception.code, 2)
        self.assertIn("skill file does not exist", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
