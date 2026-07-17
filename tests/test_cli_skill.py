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

    def test_github_flags_are_validated_and_passed_to_run(self) -> None:
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
            "--github-issue",
            "owner/repo#1",
            "--github-repo",
            "owner/repo",
            "--github-ci-run",
            "123",
            "--dry-run",
        ]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                code = module.main()
        finally:
            sys.argv = old_argv

        self.assertEqual(code, 0)
        self.assertEqual(calls[0][1]["github_issue"], "owner/repo#1")
        self.assertEqual(calls[0][1]["github_repo"], "owner/repo")
        self.assertEqual(calls[0][1]["github_ci_run"], "123")

    def test_github_conflicts_fail_before_run(self) -> None:
        module = load_cli_module()

        def fake_run(*args, **kwargs):
            raise AssertionError("run should not be called")

        cases = [
            (["--task", "x", "--issue-file", "examples/issues/fix-sample-add.md", "--github-issue", "owner/repo#1"], "--issue-file cannot be used"),
            (["--task", "x", "--ci-log-file", "examples/ci/failing-unit-test.log", "--github-repo", "owner/repo", "--github-ci-run", "123"], "--ci-log-file cannot be used"),
            (["--task", "x", "--github-ci-run", "123"], "--github-repo is required"),
            (["--check-memory", "--github-issue", "owner/repo#1"], "--check-memory cannot be combined"),
            (["--task", "x", "--github-issue", "owner/repo#abc"], "--github-issue must be exactly"),
        ]
        old_argv = sys.argv
        module.run = fake_run
        try:
            for argv, error in cases:
                with self.subTest(argv=argv):
                    sys.argv = ["run_agent_loop.py", *argv]
                    stderr = io.StringIO()
                    with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as exc:
                        module.main()
                    self.assertEqual(exc.exception.code, 2)
                    self.assertIn(error, stderr.getvalue())
        finally:
            sys.argv = old_argv

    def test_memory_file_flag_is_passed_to_run(self) -> None:
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
            "--memory-file",
            "memory/INDEX.md",
            "--dry-run",
        ]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                code = module.main()
        finally:
            sys.argv = old_argv

        self.assertEqual(code, 0)
        self.assertEqual(calls[0][1]["memory_context"].paths, ["memory/INDEX.md"])

    def test_advisory_reviewer_flag_is_passed_to_run(self) -> None:
        module = load_cli_module()
        calls = []

        def fake_run(*args, **kwargs):
            calls.append((args, kwargs))
            return {"run_id": "test-run", "run_dir": "/tmp/test-run", "ok": False, "dry_run": True}

        old_argv = sys.argv
        module.run = fake_run
        sys.argv = ["run_agent_loop.py", "--task", "fix add", "--advisory-reviewer", "codex", "--dry-run"]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                code = module.main()
        finally:
            sys.argv = old_argv

        self.assertEqual(code, 0)
        self.assertEqual(calls[0][1]["advisory_reviewer"], "codex")

    def test_reviewer_rubric_flag_is_validated_and_passed_to_run(self) -> None:
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
            "--advisory-reviewer",
            "codex",
            "--reviewer-rubric",
            "reviewers/test-reviewer.md",
            "--dry-run",
        ]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                code = module.main()
        finally:
            sys.argv = old_argv

        self.assertEqual(code, 0)
        self.assertEqual(calls[0][1]["reviewer_rubric"].source_path, "reviewers/test-reviewer.md")

    def test_reviewer_rubric_without_advisory_reviewer_fails_before_run(self) -> None:
        module = load_cli_module()

        def fake_run(*args, **kwargs):
            raise AssertionError("run should not be called")

        old_argv = sys.argv
        module.run = fake_run
        sys.argv = ["run_agent_loop.py", "--task", "x", "--reviewer-rubric", "reviewers/test-reviewer.md"]
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as exc:
                module.main()
        finally:
            sys.argv = old_argv

        self.assertEqual(exc.exception.code, 2)
        self.assertIn("--reviewer-rubric requires --advisory-reviewer codex", stderr.getvalue())

    def test_invalid_reviewer_rubric_fails_before_run(self) -> None:
        module = load_cli_module()

        def fake_run(*args, **kwargs):
            raise AssertionError("run should not be called")

        old_argv = sys.argv
        module.run = fake_run
        sys.argv = ["run_agent_loop.py", "--task", "x", "--advisory-reviewer", "codex", "--reviewer-rubric", "reviewers/README.md"]
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as exc:
                module.main()
        finally:
            sys.argv = old_argv

        self.assertEqual(exc.exception.code, 2)
        self.assertIn("README.md is not an includable reviewer rubric", stderr.getvalue())

    def test_unsupported_advisory_reviewer_fails_before_run(self) -> None:
        module = load_cli_module()

        def fake_run(*args, **kwargs):
            raise AssertionError("run should not be called")

        old_argv = sys.argv
        module.run = fake_run
        sys.argv = ["run_agent_loop.py", "--task", "x", "--advisory-reviewer", "other"]
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as exc:
                module.main()
        finally:
            sys.argv = old_argv

        self.assertEqual(exc.exception.code, 2)
        self.assertIn("invalid choice", stderr.getvalue())

    def test_check_memory_rejects_advisory_reviewer(self) -> None:
        module = load_cli_module()

        def fake_run(*args, **kwargs):
            raise AssertionError("run should not be called")

        old_argv = sys.argv
        module.run = fake_run
        sys.argv = ["run_agent_loop.py", "--check-memory", "--advisory-reviewer", "codex"]
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as exc:
                module.main()
        finally:
            sys.argv = old_argv

        self.assertEqual(exc.exception.code, 2)
        self.assertIn("--check-memory cannot be combined with --advisory-reviewer", stderr.getvalue())

    def test_check_memory_rejects_reviewer_rubric(self) -> None:
        module = load_cli_module()

        def fake_run(*args, **kwargs):
            raise AssertionError("run should not be called")

        old_argv = sys.argv
        module.run = fake_run
        sys.argv = ["run_agent_loop.py", "--check-memory", "--reviewer-rubric", "reviewers/test-reviewer.md"]
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as exc:
                module.main()
        finally:
            sys.argv = old_argv

        self.assertEqual(exc.exception.code, 2)
        self.assertIn("--check-memory cannot be combined with --reviewer-rubric", stderr.getvalue())

    def test_failed_memory_validation_does_not_call_run(self) -> None:
        module = load_cli_module()
        state_before = (ROOT / ".agent" / "state.json").read_text()
        progress_before = (ROOT / "PROGRESS.md").read_text()

        def fake_run(*args, **kwargs):
            raise AssertionError("run should not be called")

        old_argv = sys.argv
        module.run = fake_run
        sys.argv = ["run_agent_loop.py", "--task", "x", "--memory-file", "memory/missing.md"]
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as exc:
                module.main()
        finally:
            sys.argv = old_argv

        self.assertEqual(exc.exception.code, 2)
        self.assertIn("memory file does not exist", stderr.getvalue())
        self.assertEqual((ROOT / ".agent" / "state.json").read_text(), state_before)
        self.assertEqual((ROOT / "PROGRESS.md").read_text(), progress_before)

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
