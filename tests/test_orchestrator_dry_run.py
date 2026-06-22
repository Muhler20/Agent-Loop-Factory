import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.orchestrator import run


class OrchestratorDryRunTests(unittest.TestCase):
    def test_orchestrator_dry_run_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
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

            result = run("test task description", tmp_path, dry_run=True)
            run_dir = Path(result["run_dir"])

            self.assertTrue(result["dry_run"])
            self.assertTrue((run_dir / "run_report.md").exists())
            self.assertTrue((run_dir / "gate_results.json").exists())
            self.assertTrue((run_dir / "verifier_result.json").exists())
            self.assertTrue((run_dir / "stdout.log").exists())
            self.assertTrue((run_dir / "stderr.log").exists())
            self.assertTrue((run_dir / "diff_summary.md").exists())
            self.assertFalse((run_dir / "codex_result.json").exists())
            self.assertIn("## Current Goal", (tmp_path / "PROGRESS.md").read_text())


if __name__ == "__main__":
    unittest.main()
