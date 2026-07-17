import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.config import Config
from agent_loop_factory.task_spec import TaskSpec
from agent_loop_factory.verifier import matches_human_required_path, run_verifier


class VerifierTests(unittest.TestCase):
    def test_matches_human_required_directory_path(self) -> None:
        self.assertTrue(matches_human_required_path("auth/login.py", "auth/"))
        self.assertTrue(matches_human_required_path("auth\\login.py", "auth/"))
        self.assertFalse(matches_human_required_path("authentication_notes.md", "auth/"))

    def test_matches_human_required_exact_file(self) -> None:
        self.assertTrue(matches_human_required_path("Dockerfile", "Dockerfile"))
        self.assertFalse(matches_human_required_path("docs/Dockerfile", "Dockerfile"))

    def test_matches_human_required_fnmatch_pattern(self) -> None:
        self.assertTrue(matches_human_required_path("migrations/001_init.sql", "*.sql"))
        self.assertFalse(matches_human_required_path("migrations/001_init.py", "*.sql"))

    def test_matches_human_required_unrelated_path(self) -> None:
        self.assertFalse(matches_human_required_path("src/app.py", "auth/"))
        self.assertFalse(matches_human_required_path("src/app.py", "Dockerfile"))

    def test_passes_on_small_safe_diff_with_passing_gates(self) -> None:
        with repo() as tmp:
            (tmp / "app.py").write_text("print('hello')\n")
            result = verify(tmp)
            self.assertTrue(result["ok"], result["reasons"])
            self.assertEqual(result["changed_file_count"], 1)
            self.assertFalse(result["tests_weakened_or_deleted"])

    def test_fails_when_gates_fail(self) -> None:
        with repo() as tmp:
            (tmp / "app.py").write_text("print('hello')\n")
            result = verify(tmp, gates=[{"name": "test", "command": "test", "required": True, "ok": False}])
            self.assertFalse(result["ok"])
            self.assertIn("one or more gates failed", result["reasons"])

    def test_optional_gate_failure_warns_without_failing(self) -> None:
        with repo() as tmp:
            (tmp / "app.py").write_text("print('hello')\n")
            result = verify(tmp, gates=[{"name": "lint", "command": "lint", "required": False, "ok": False}])
            self.assertTrue(result["ok"], result["reasons"])
            self.assertIn("optional gate failed: lint", result["warnings"])

    def test_fails_when_changed_file_count_exceeds_max_changed_files(self) -> None:
        with repo() as tmp:
            (tmp / "a.py").write_text("a = 1\n")
            (tmp / "b.py").write_text("b = 1\n")
            result = verify(tmp, Config(max_changed_files=1))
            self.assertFalse(result["ok"])
            self.assertIn("changed_file_count exceeds max_changed_files: 2 > 1", result["reasons"])

    def test_changed_files_ignore_run_artifacts(self) -> None:
        with repo({"sample_math/__init__.py": "def add(a, b):\n    return 0\n"}) as tmp:
            (tmp / "sample_math" / "__init__.py").write_text("def add(a, b):\n    return a + b\n")
            run_artifacts = [
                "run_report.md",
                "gate_results.json",
                "diff_summary.md",
                "verifier_result.json",
            ]
            artifact_dir = tmp / "run-1"
            artifact_dir.mkdir()
            for artifact in run_artifacts:
                (artifact_dir / artifact).write_text("artifact\n")

            result = verify(tmp, run_dir=artifact_dir)

            self.assertEqual(result["changed_files"], ["sample_math/__init__.py"])
            self.assertEqual(result["changed_file_count"], 1)
            self.assertEqual(result["diff_line_count"], 2)

    def test_fails_when_run_report_is_created_in_target_repo(self) -> None:
        with repo() as tmp:
            (tmp / "run_report.md").write_text("artifact\n")
            result = verify(tmp)
            self.assertFalse(result["ok"])
            self.assertEqual(result["reserved_artifacts_touched"], ["run_report.md"])
            self.assertIn("reserved run artifact file changed in target repo: run_report.md", result["reasons"])

    def test_fails_when_json_artifacts_are_created_in_target_repo(self) -> None:
        with repo() as tmp:
            (tmp / "gate_results.json").write_text("{}\n")
            (tmp / "verifier_result.json").write_text("{}\n")
            result = verify(tmp)
            self.assertFalse(result["ok"])
            self.assertEqual(result["reserved_artifacts_touched"], ["gate_results.json", "verifier_result.json"])
            self.assertIn("reserved run artifact file changed in target repo: gate_results.json", result["reasons"])
            self.assertIn("reserved run artifact file changed in target repo: verifier_result.json", result["reasons"])

    def test_fails_when_pr_handoff_artifacts_are_created_in_target_repo(self) -> None:
        with repo() as tmp:
            (tmp / "pr_body.md").write_text("body\n")
            (tmp / "pr_commands.md").write_text("commands\n")
            (tmp / "pr_handoff_check.md").write_text("check\n")
            (tmp / "pr_handoff_check.json").write_text("{}\n")
            result = verify(tmp)
            self.assertFalse(result["ok"])
            self.assertEqual(result["reserved_artifacts_touched"], ["pr_body.md", "pr_commands.md", "pr_handoff_check.json", "pr_handoff_check.md"])
            self.assertIn("reserved run artifact file changed in target repo: pr_body.md", result["reasons"])
            self.assertIn("reserved run artifact file changed in target repo: pr_commands.md", result["reasons"])
            self.assertIn("reserved run artifact file changed in target repo: pr_handoff_check.md", result["reasons"])
            self.assertIn("reserved run artifact file changed in target repo: pr_handoff_check.json", result["reasons"])

    def test_fails_when_context_artifacts_are_created_in_target_repo(self) -> None:
        for artifact in ["issue_context.md", "ci_context.log", "context_summary.json"]:
            with self.subTest(artifact=artifact):
                with repo() as tmp:
                    (tmp / artifact).write_text("artifact\n")
                    result = verify(tmp)
                    self.assertFalse(result["ok"])
                    self.assertEqual(result["reserved_artifacts_touched"], [artifact])
                    self.assertIn(f"reserved run artifact file changed in target repo: {artifact}", result["reasons"])

    def test_fails_when_github_context_artifacts_are_created_in_target_repo(self) -> None:
        for artifact in ["github_issue_context.md", "github_issue_context.json", "github_ci_context.log", "github_ci_context.json", "github_context_summary.json"]:
            with self.subTest(artifact=artifact):
                with repo() as tmp:
                    (tmp / artifact).write_text("artifact\n")
                    result = verify(tmp)
                    self.assertFalse(result["ok"])
                    self.assertEqual(result["reserved_artifacts_touched"], [artifact])
                    self.assertIn(f"reserved run artifact file changed in target repo: {artifact}", result["reasons"])

    def test_fails_when_memory_proposal_artifacts_are_created_in_target_repo(self) -> None:
        with repo() as tmp:
            (tmp / "memory_proposal.md").write_text("proposal\n")
            (tmp / "memory_proposal.json").write_text("{}\n")
            result = verify(tmp)
            self.assertFalse(result["ok"])
            self.assertEqual(result["reserved_artifacts_touched"], ["memory_proposal.json", "memory_proposal.md"])
            self.assertIn("reserved run artifact file changed in target repo: memory_proposal.md", result["reasons"])
            self.assertIn("reserved run artifact file changed in target repo: memory_proposal.json", result["reasons"])

    def test_fails_when_memory_context_artifacts_are_created_in_target_repo(self) -> None:
        with repo() as tmp:
            (tmp / "memory_context.md").write_text("context\n")
            (tmp / "memory_context.json").write_text("{}\n")
            result = verify(tmp)
            self.assertFalse(result["ok"])
            self.assertEqual(result["reserved_artifacts_touched"], ["memory_context.json", "memory_context.md"])
            self.assertIn("reserved run artifact file changed in target repo: memory_context.md", result["reasons"])
            self.assertIn("reserved run artifact file changed in target repo: memory_context.json", result["reasons"])

    def test_fails_when_advisory_review_artifacts_are_created_in_target_repo(self) -> None:
        for artifact in [
            "advisory_review.md",
            "advisory_review.json",
            "advisory_review_result.json",
            "advisory_review_prompt.md",
            "advisory_review_stdout.log",
            "advisory_review_stderr.log",
            "advisory_review_rubric.md",
            "advisory_review_rubric.json",
        ]:
            with self.subTest(artifact=artifact):
                with repo() as tmp:
                    (tmp / artifact).write_text("artifact\n")
                    result = verify(tmp)
                    self.assertFalse(result["ok"])
                    self.assertEqual(result["reserved_artifacts_touched"], [artifact])
                    self.assertIn(f"reserved run artifact file changed in target repo: {artifact}", result["reasons"])

    def test_fails_when_human_required_paths_are_touched(self) -> None:
        with repo() as tmp:
            (tmp / "auth").mkdir()
            (tmp / "auth" / "login.py").write_text("pass\n")
            result = verify(tmp, Config(human_required_paths=["auth/"]))
            self.assertFalse(result["ok"])
            self.assertEqual(result["human_required_touched"], ["auth/login.py"])

    def test_fails_when_test_assertions_are_removed(self) -> None:
        with repo({"tests/test_app.py": "import unittest\n\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n"}) as tmp:
            (tmp / "tests" / "test_app.py").write_text("import unittest\n\nclass T(unittest.TestCase):\n    def test_x(self):\n        pass\n")
            result = verify(tmp)
            self.assertFalse(result["ok"])
            self.assertTrue(result["tests_weakened_or_deleted"])

    def test_fails_when_skip_markers_are_added(self) -> None:
        with repo({"tests/test_app.py": "import unittest\n\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n"}) as tmp:
            (tmp / "tests" / "test_app.py").write_text(
                "import unittest\n\nclass T(unittest.TestCase):\n    @unittest.skip('later')\n    def test_x(self):\n        self.assertTrue(True)\n"
            )
            result = verify(tmp)
            self.assertFalse(result["ok"])
            self.assertTrue(result["tests_weakened_or_deleted"])

    def test_passes_when_changed_file_is_inside_allowed_files(self) -> None:
        with repo({"sample_math/__init__.py": "def add(a, b):\n    return 0\n"}) as tmp:
            (tmp / "sample_math" / "__init__.py").write_text("def add(a, b):\n    return a + b\n")
            result = verify(tmp, task_spec=task_spec(allowed_files=["sample_math/__init__.py"]))
            self.assertTrue(result["ok"], result["reasons"])
            self.assertEqual(result["task_allowed_violations"], [])

    def test_fails_when_changed_file_is_outside_allowed_files(self) -> None:
        with repo({"sample_math/__init__.py": "def add(a, b):\n    return 0\n", "tests/test_sample_math.py": "pass\n"}) as tmp:
            (tmp / "tests" / "test_sample_math.py").write_text("def test_add():\n    assert True\n")
            result = verify(tmp, task_spec=task_spec(allowed_files=["sample_math/__init__.py"]))
            self.assertFalse(result["ok"])
            self.assertEqual(result["task_allowed_violations"], ["tests/test_sample_math.py"])
            self.assertIn("changed file outside task allowed files: tests/test_sample_math.py", result["reasons"])

    def test_fails_when_changed_file_is_under_forbidden_directory(self) -> None:
        with repo({"tests/test_sample_math.py": "pass\n"}) as tmp:
            (tmp / "tests" / "test_sample_math.py").write_text("def test_add():\n    assert True\n")
            result = verify(tmp, task_spec=task_spec(forbidden_files=["tests/"]))
            self.assertFalse(result["ok"])
            self.assertEqual(result["task_forbidden_touched"], ["tests/test_sample_math.py"])
            self.assertIn("task forbidden file touched: tests/test_sample_math.py", result["reasons"])

    def test_fails_when_changed_file_exactly_matches_forbidden_file(self) -> None:
        with repo({"pyproject.toml": "[project]\nname='x'\n"}) as tmp:
            (tmp / "pyproject.toml").write_text("[project]\nname='y'\n")
            result = verify(tmp, task_spec=task_spec(forbidden_files=["pyproject.toml"]))
            self.assertFalse(result["ok"])
            self.assertEqual(result["task_forbidden_touched"], ["pyproject.toml"])
            self.assertIn("task forbidden file touched: pyproject.toml", result["reasons"])

    def test_passes_when_no_task_file_lists_are_provided(self) -> None:
        with repo() as tmp:
            (tmp / "app.py").write_text("print('hello')\n")
            result = verify(tmp, task_spec=task_spec())
            self.assertTrue(result["ok"], result["reasons"])
            self.assertEqual(result["task_allowed_files"], [])
            self.assertEqual(result["task_forbidden_files"], [])


def verify(
    tmp: Path,
    config: Config | None = None,
    gates: list[dict[str, object]] | None = None,
    run_dir: Path | None = None,
    task_spec: TaskSpec | None = None,
) -> dict[str, object]:
    run_dir = run_dir or tmp / "run"
    run_dir.mkdir(exist_ok=True)
    return run_verifier(config or Config(), tmp, run_dir, gates or [{"command": "test", "ok": True}], task_spec)


def task_spec(allowed_files: list[str] | None = None, forbidden_files: list[str] | None = None) -> TaskSpec:
    return TaskSpec("Task", "# Task\n", allowed_files=allowed_files or [], forbidden_files=forbidden_files or [])


class repo:
    def __init__(self, files: dict[str, str] | None = None):
        self.files = files or {"app.py": "print('hi')\n"}
        self.tmp = tempfile.TemporaryDirectory()

    def __enter__(self) -> Path:
        path = Path(self.tmp.__enter__())
        git(path, "init")
        for name, text in self.files.items():
            file_path = path / name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(text)
        git(path, "add", ".")
        git(path, "-c", "user.email=a@example.com", "-c", "user.name=A", "commit", "-m", "init")
        return path

    def __exit__(self, *exc) -> None:
        self.tmp.__exit__(*exc)


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
