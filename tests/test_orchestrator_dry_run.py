import tempfile
import unittest
import sys
import json
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.orchestrator import run
from agent_loop_factory.skill import Skill


def write_agent_config(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='target'\n")
    agent = tmp_path / ".agent"
    (agent / "runs").mkdir(parents=True)
    (agent / "config.yaml").write_text(
        'target_repo_path: "."\n'
        'worktree_base_path: "../agent-worktrees"\n'
        "max_iterations: 3\n"
        "max_changed_files: 8\n"
        "max_diff_lines: 500\n"
        "allowed_commands:\n"
        '  - "pytest"\n'
        "gates:\n"
        '  - "pytest"\n'
        "human_required_paths:\n"
        '  - "auth/"\n'
        'output_mode: "draft_pr_only"\n'
        "auto_merge: false\n"
        "auto_deploy: false\n"
    )


def write_normal_config(tmp_path: Path) -> None:
    agent = tmp_path / ".agent"
    (agent / "runs").mkdir(parents=True)
    (agent / "config.yaml").write_text(
        'target_repo_path: "target"\n'
        'worktree_base_path: "worktrees"\n'
        "max_iterations: 3\n"
        "max_changed_files: 8\n"
        "max_diff_lines: 500\n"
        "allowed_commands:\n"
        '  - "python3 -c pass"\n'
        "gates:\n"
        '  - "python3 -c pass"\n'
        "human_required_paths:\n"
        '  - "auth/"\n'
        'output_mode: "draft_pr_only"\n'
        "auto_merge: false\n"
        "auto_deploy: false\n"
    )


def init_target_repo(path: Path) -> None:
    path.mkdir()
    (path / "app.py").write_text("print('hello')\n")
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=path, check=True, capture_output=True, text=True)


class OrchestratorDryRunTests(unittest.TestCase):
    def test_orchestrator_dry_run_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_agent_config(tmp_path)

            result = run("test task description", tmp_path, dry_run=True)
            run_dir = Path(result["run_dir"])

            self.assertTrue(result["dry_run"])
            self.assertTrue((run_dir / "run_report.md").exists())
            self.assertTrue((run_dir / "gate_results.json").exists())
            self.assertTrue((run_dir / "verifier_result.json").exists())
            self.assertTrue((run_dir / "stdout.log").exists())
            self.assertTrue((run_dir / "stderr.log").exists())
            self.assertTrue((run_dir / "diff_summary.md").exists())
            self.assertTrue((run_dir / "review_bundle.md").exists())
            self.assertTrue((run_dir / "pr_title.txt").exists())
            self.assertTrue((run_dir / "pr_body.md").exists())
            self.assertTrue((run_dir / "pr_commands.md").exists())
            self.assertTrue((run_dir / "pr_handoff.md").exists())
            self.assertTrue((run_dir / "pr_handoff_check.md").exists())
            self.assertTrue((run_dir / "pr_handoff_check.json").exists())
            self.assertEqual((run_dir / "task_spec.md").read_text(), "# test task description\n\ntest task description\n")
            report = (run_dir / "run_report.md").read_text()
            self.assertIn("task_source: inline", report)
            self.assertIn(f"path: .agent/runs/{result['run_id']}/review_bundle.md", report)
            self.assertIn(f"pr_title: .agent/runs/{result['run_id']}/pr_title.txt", report)
            self.assertIn(f"pr_body: .agent/runs/{result['run_id']}/pr_body.md", report)
            self.assertIn(f"pr_commands: .agent/runs/{result['run_id']}/pr_commands.md", report)
            self.assertIn(f"pr_handoff_check: .agent/runs/{result['run_id']}/pr_handoff_check.md", report)
            self.assertIn(f"pr_handoff_check_json: .agent/runs/{result['run_id']}/pr_handoff_check.json", report)
            self.assertIn("handoff_check_status: needs_attention", report)
            self.assertIn("no commands executed: true", report)
            self.assertIn("## Draft PR Handoff", (run_dir / "review_bundle.md").read_text())
            self.assertIn("- handoff check status: needs_attention", (run_dir / "review_bundle.md").read_text())
            self.assertIn("* handoff check status: needs_attention", (run_dir / "pr_handoff.md").read_text())
            self.assertIn("No push or PR creation was performed.", (run_dir / "review_bundle.md").read_text())
            self.assertIn("recommendation: reject_or_rework", report)
            self.assertFalse((run_dir / "codex_result.json").exists())
            self.assertIn("## Current Goal", (tmp_path / "PROGRESS.md").read_text())

    def test_orchestrator_dry_run_accepts_task_file_body(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_agent_config(tmp_path)
            task_file = tmp_path / "task.md"
            body = "# Fix sample add\n\n## Goal\n\nFix add.\n\n## Allowed files\n\n- `sample_math/__init__.py`\n\n## Forbidden files\n\n- `tests/`\n"
            task_file.write_text(body)

            result = run(body, tmp_path, dry_run=True, task_file_path=str(task_file))
            run_dir = Path(result["run_dir"])
            report = (run_dir / "run_report.md").read_text()
            verifier = json.loads((run_dir / "verifier_result.json").read_text())

            self.assertEqual((run_dir / "task_spec.md").read_text(), body)
            self.assertIn("task_title: Fix sample add", report)
            self.assertIn("task_source: file", report)
            self.assertIn(f"task_file_path: {task_file}", report)
            self.assertIn("Task allowed files:\n- sample_math/__init__.py", report)
            self.assertIn("Task forbidden files:\n- tests/", report)
            self.assertIn("- task source: file", (run_dir / "review_bundle.md").read_text())
            self.assertEqual(verifier["task_allowed_files"], ["sample_math/__init__.py"])
            self.assertEqual(verifier["task_forbidden_files"], ["tests/"])

    def test_skill_artifact_is_written_when_skill_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_agent_config(tmp_path)
            skill = Skill("failing-test-fix", "Keep tests strong.\n", str(tmp_path / "skills/failing-test-fix/SKILL.md"))

            result = run("test task description", tmp_path, dry_run=True, skill=skill)
            run_dir = Path(result["run_dir"])
            report = (run_dir / "run_report.md").read_text()

            self.assertEqual((run_dir / "skill.md").read_text(), "Keep tests strong.\n")
            self.assertIn("## Skill", report)
            self.assertIn("skill_name: failing-test-fix", report)
            self.assertIn("skill_source: file", report)
            self.assertIn(f"skill_file_path: {skill.skill_file_path}", report)
            self.assertIn("- skill name: failing-test-fix", (run_dir / "review_bundle.md").read_text())

    def test_skill_artifact_is_not_written_without_skill(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_agent_config(tmp_path)

            result = run("test task description", tmp_path, dry_run=True)
            run_dir = Path(result["run_dir"])
            report = (run_dir / "run_report.md").read_text()

            self.assertFalse((run_dir / "skill.md").exists())
            self.assertIn("## Skill", report)
            self.assertIn("skill_name: none", report)
            self.assertIn("skill_source: none", report)
            self.assertIn("- skill name: None", (run_dir / "review_bundle.md").read_text())

    def test_orchestrator_normal_run_writes_review_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_normal_config(tmp_path)
            init_target_repo(tmp_path / "target")

            result = run("inspect only", tmp_path, dry_run=False)
            run_dir = Path(result["run_dir"])
            report = (run_dir / "run_report.md").read_text()

            self.assertTrue(result["ok"])
            self.assertTrue((run_dir / "review_bundle.md").exists())
            self.assertIn("recommendation: ready_for_human_review", report)


if __name__ == "__main__":
    unittest.main()
