import subprocess
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.codex_implementer import build_prompt, run_codex_implementer
from agent_loop_factory.config import Config
from agent_loop_factory.skill import Skill


class CodexImplementerTests(unittest.TestCase):
    def test_codex_implementer_writes_artifacts_with_fake_runner(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            worktree = tmp_path / "worktree"
            run_dir = tmp_path / "run"
            worktree.mkdir()
            run_dir.mkdir()
            (worktree / "AGENTS.md").write_text("Never weaken tests.\n")
            (worktree / "CONSTRAINTS.md").write_text("Keep diffs small.\n")
            calls = []

            def fake_runner(*args, **kwargs):
                calls.append((args, kwargs))
                return subprocess.CompletedProcess(args[0], 0, "done\n", "")

            result = run_codex_implementer(
                "fix the tiny failure",
                worktree,
                run_dir,
                Config(codex_exec_args=["--ephemeral"]),
                runner=fake_runner,
            )

            self.assertTrue(result.ok)
            self.assertEqual(
                calls[0][0][0],
                ["codex", "exec", "--cd", str(worktree), "--sandbox", "workspace-write", "--ephemeral", "-"],
            )
            self.assertIn("fix the tiny failure", (run_dir / "codex_prompt.md").read_text())
            self.assertIn("# Task Spec", (run_dir / "codex_prompt.md").read_text())
            self.assertIn("# Skill", (run_dir / "codex_prompt.md").read_text())
            self.assertIn("Never weaken tests.", (run_dir / "codex_prompt.md").read_text())
            self.assertIn("Keep diffs small.", (run_dir / "codex_prompt.md").read_text())
            self.assertIn("Never weaken tests.", calls[0][1]["input"])
            self.assertIn("Keep diffs small.", calls[0][1]["input"])
            self.assertEqual((run_dir / "codex_stdout.log").read_text(), "done\n")
            self.assertTrue((run_dir / "codex_result.json").exists())

    def test_prompt_includes_optional_context_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            worktree = Path(raw)
            (worktree / "AGENTS.md").write_text("Agent rule.\n")
            (worktree / "CONSTRAINTS.md").write_text("Project constraint.\n")

            prompt = build_prompt("do the task", worktree, Config())

            self.assertIn("# Task Spec\n\ndo the task", prompt)
            self.assertIn("# AGENTS.md\n\nAgent rule.", prompt)
            self.assertIn("# CONSTRAINTS.md\n\nProject constraint.", prompt)

    def test_prompt_handles_missing_optional_context(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            prompt = build_prompt("do the task", Path(raw), Config())

            self.assertIn("# Skill\n\nNo skill selected.", prompt)
            self.assertIn("No AGENTS.md found.", prompt)
            self.assertIn("No CONSTRAINTS.md found.", prompt)

    def test_prompt_includes_skill_content_when_skill_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            skill = Skill("failing-test-fix", "Inspect the failing test.\n", "skills/failing-test-fix/SKILL.md")

            prompt = build_prompt("do the task", Path(raw), Config(), skill)

            self.assertIn("# Skill\n\nInspect the failing test.", prompt)
            self.assertIn("# Task Spec\n\ndo the task", prompt)

    def test_prompt_tells_codex_not_to_create_run_artifacts_in_target_repo(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            prompt = build_prompt("do the task", Path(raw), Config())

            self.assertIn("Agent Loop Factory writes run artifacts under `.agent/runs/<run_id>/`.", prompt)
            self.assertIn("Do not create `run_report.md`, `gate_results.json`, `verifier_result.json`, `diff_summary.md`, `review_bundle.md`, `pr_title.txt`, `pr_body.md`, `pr_commands.md`, `pr_handoff.md`, `pr_handoff_check.md`, `pr_handoff_check.json`, `task_spec.md`", prompt)
            self.assertIn("inside the target repo", prompt)
            self.assertIn("Only change files needed for the task.", prompt)


if __name__ == "__main__":
    unittest.main()
