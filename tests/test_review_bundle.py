import tempfile
import unittest
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.review_bundle import build_review_bundle, recommendation, write_review_bundle
from agent_loop_factory.skill import Skill
from agent_loop_factory.task_spec import TaskSpec


class ReviewBundleTests(unittest.TestCase):
    def test_writes_passing_review_bundle_with_run_context(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            task = TaskSpec(
                task_title="Fix add",
                task_body="# Fix add\n",
                task_file_path="tasks/fix.md",
                allowed_files=["sample_math/__init__.py"],
                forbidden_files=["tests/"],
            )
            skill = Skill("failing-test-fix", "Keep tests strong.\n", "skills/failing-test-fix/SKILL.md")
            gates = [{"name": "unit tests", "command": "python3 -m unittest", "required": True, "ok": True, "warning": None}]
            verifier = verifier_result(warnings=["note"])

            decision, reason = write_review_bundle(
                run_dir,
                "run-1",
                task,
                skill,
                "none",
                SimpleNamespace(path=Path("/tmp/worktree"), branch="agent/run-1"),
                gates,
                verifier,
                "diff --git a/sample_math/__init__.py b/sample_math/__init__.py\n",
                True,
            )

            bundle = (run_dir / "review_bundle.md").read_text()
            self.assertEqual(decision, "manual_review_required")
            self.assertEqual(reason, "warnings present")
            self.assertIn("# Human Review Bundle", bundle)
            self.assertIn("- run_id: run-1", bundle)
            self.assertIn("- task source: file", bundle)
            self.assertIn("- task file path: tasks/fix.md", bundle)
            self.assertIn("- task title: Fix add", bundle)
            self.assertIn("  - sample_math/__init__.py", bundle)
            self.assertIn("  - tests/", bundle)
            self.assertIn("- skill name: failing-test-fix", bundle)
            self.assertIn("- skill file path: skills/failing-test-fix/SKILL.md", bundle)
            self.assertIn("  - sample_math/__init__.py", bundle)
            self.assertIn("- changed_file_count: 1", bundle)
            self.assertIn("- diff_line_count: 2", bundle)
            self.assertIn("- name: unit tests", bundle)
            self.assertIn("command: python3 -m unittest", bundle)
            self.assertIn("- reasons:\n  - None", bundle)
            self.assertIn("- warnings:\n  - note", bundle)
            self.assertIn("diff --git", bundle)
            self.assertIn("- Confirm the changed files match the task.", bundle)
            self.assertIn("- recommendation: manual_review_required", bundle)

    def test_bundle_says_none_without_skill(self) -> None:
        bundle = build_review_bundle(
            "run-1",
            TaskSpec("Inline task", "Inline task"),
            None,
            "none",
            SimpleNamespace(path=None, branch=None),
            [],
            verifier_result(),
            "",
            True,
        )

        self.assertIn("- skill name: None", bundle)
        self.assertIn("- skill file path: None", bundle)

    def test_recommendation_verifier_failure_rejects(self) -> None:
        self.assertEqual(recommendation(verifier_result(ok=False, reasons=["bad"]), []), ("reject_or_rework", "verifier failed"))

    def test_recommendation_required_gate_failure_rejects(self) -> None:
        gates = [{"required": True, "ok": False}]
        self.assertEqual(recommendation(verifier_result(), gates), ("reject_or_rework", "required gate failed"))

    def test_recommendation_human_required_needs_manual_review(self) -> None:
        result = verifier_result(human_required_touched=["auth/login.py"])
        self.assertEqual(recommendation(result, []), ("manual_review_required", "human-required paths touched"))

    def test_recommendation_verifier_warnings_need_manual_review(self) -> None:
        self.assertEqual(recommendation(verifier_result(warnings=["warn"]), []), ("manual_review_required", "warnings present"))

    def test_recommendation_optional_gate_warning_needs_manual_review(self) -> None:
        gates = [{"required": False, "ok": True, "warning": "slow"}]
        self.assertEqual(recommendation(verifier_result(), gates), ("manual_review_required", "warnings present"))

    def test_recommendation_clean_run_is_ready_for_human_review(self) -> None:
        self.assertEqual(recommendation(verifier_result(), []), ("ready_for_human_review", "gates and verifier passed"))


def verifier_result(**overrides):
    result = {
        "ok": True,
        "reasons": [],
        "warnings": [],
        "changed_files": ["sample_math/__init__.py"],
        "changed_file_count": 1,
        "diff_line_count": 2,
        "human_required_touched": [],
        "reserved_artifacts_touched": [],
        "task_allowed_violations": [],
        "task_forbidden_touched": [],
        "tests_weakened_or_deleted": False,
    }
    result.update(overrides)
    return result


if __name__ == "__main__":
    unittest.main()
