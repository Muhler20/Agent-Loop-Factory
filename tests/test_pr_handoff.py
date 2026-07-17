import tempfile
import unittest
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.pr_handoff import build_pr_handoff, pr_title, write_pr_handoff
from agent_loop_factory.skill import Skill
from agent_loop_factory.task_spec import TaskSpec


class PrHandoffTests(unittest.TestCase):
    def test_pr_title_uses_task_title(self) -> None:
        self.assertEqual(pr_title("run-1", TaskSpec("Fix Sample Add", "body")), "Fix Sample Add")

    def test_pr_title_falls_back_to_inline_task(self) -> None:
        self.assertEqual(pr_title("run-1", TaskSpec("", "Fix failing unit test")), "Fix failing unit test")

    def test_pr_title_falls_back_to_run_id(self) -> None:
        self.assertEqual(pr_title("run-1", TaskSpec("", "")), "Agent Loop Factory run run-1")

    def test_pr_title_is_one_line_and_length_limited(self) -> None:
        title = pr_title("run-1", TaskSpec("  Fix\n" + ("x" * 120), "body"))

        self.assertNotIn("\n", title)
        self.assertLessEqual(len(title), 100)

    def test_writes_pr_handoff_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            task = TaskSpec("Fix add", "# Fix add\n", "tasks/fix.md", ["sample_math/__init__.py"], ["tests/"])
            skill = Skill("failing-test-fix", "Keep tests strong.\n", "skills/failing-test-fix/SKILL.md")
            gates = [{"name": "unit tests", "command": "python3 -m unittest", "required": True, "ok": True, "warning": None}]

            write_pr_handoff(
                run_dir,
                "run-1",
                task,
                skill,
                SimpleNamespace(path=Path("/tmp/worktree"), branch="agent/run-1"),
                gates,
                verifier_result(),
                "ready_for_human_review",
                "ready",
            )

            self.assertEqual((run_dir / "pr_title.txt").read_text(), "Fix add\n")
            body = (run_dir / "pr_body.md").read_text()
            commands = (run_dir / "pr_commands.md").read_text()
            handoff = (run_dir / "pr_handoff.md").read_text()
            for heading in ["# Summary", "# Task", "# Skill", "# Changed Files", "# Gates", "# Verifier", "# Review", "# Memory Proposal", "# Safety"]:
                self.assertIn(heading, body)
            self.assertIn("* task source: file", body)
            self.assertIn("* skill name: failing-test-fix", body)
            self.assertIn("  * sample_math/__init__.py", body)
            self.assertIn("* changed_file_count: 1", body)
            self.assertIn("* diff_line_count: 2", body)
            self.assertIn("* name: unit tests", body)
            self.assertIn("* recommendation: ready_for_human_review", body)
            self.assertIn("* handoff check status: ready", body)
            self.assertIn("* memory proposal: memory_proposal.md", body)
            self.assertIn("Agent Loop Factory did not push, open a PR, merge, or deploy.", body)
            self.assertIn("Review before running.", commands)
            self.assertIn("Do not run if verifier failed.", commands)
            self.assertIn("cd /tmp/worktree", commands)
            self.assertIn("git status", commands)
            self.assertIn("git diff", commands)
            self.assertIn("git add sample_math/__init__.py", commands)
            self.assertIn('git commit -m "Fix add"', commands)
            self.assertIn("git push -u origin agent/run-1", commands)
            self.assertIn("gh pr create \\", commands)
            self.assertIn("--draft \\", commands)
            self.assertIn("--body-file", commands)
            self.assertIn("* pr_handoff_check.md:", handoff)
            self.assertIn("* pr_handoff_check.json:", handoff)
            self.assertIn("* memory_proposal.md:", handoff)
            self.assertIn("* memory_proposal.json:", handoff)
            self.assertIn("* handoff check status: ready", handoff)
            self.assertIn("* no commands were executed: true", handoff)

    def test_no_changed_files_case_is_handled(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            write_pr_handoff(
                run_dir,
                "run-1",
                TaskSpec("Inspect only", "Inspect only"),
                None,
                SimpleNamespace(path=Path("/tmp/worktree"), branch="agent/run-1"),
                [],
                verifier_result(changed_files=[], changed_file_count=0, diff_line_count=0),
                "ready_for_human_review",
            )

            self.assertIn("# No changed files to add.", (run_dir / "pr_commands.md").read_text())

    def test_unavailable_worktree_or_branch_case_is_handled(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            write_pr_handoff(
                run_dir,
                "run-1",
                TaskSpec("Inspect only", "Inspect only"),
                None,
                SimpleNamespace(path=None, branch=None),
                [],
                verifier_result(),
                "reject_or_rework",
            )

            commands = (run_dir / "pr_commands.md").read_text()
            self.assertIn("cd Unavailable", commands)
            self.assertIn("git push -u origin Unavailable", commands)
            self.assertIn("adjust these commands manually", commands)

    def test_advisory_rubric_handoff_paths_include_run_dir_separator(self) -> None:
        handoff = build_pr_handoff(
            Path(".agent/runs/run-1"),
            "ready_for_human_review",
            advisory_review={"reviewer_rubric_included": True},
        )

        self.assertIn("* advisory_review_rubric.md: .agent/runs/run-1/advisory_review_rubric.md", handoff)
        self.assertIn("* advisory_review_rubric.json: .agent/runs/run-1/advisory_review_rubric.json", handoff)
        self.assertNotIn(".agent/runs/run-1advisory_review_rubric.md", handoff)


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
