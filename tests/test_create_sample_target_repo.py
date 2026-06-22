import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CreateSampleTargetRepoTests(unittest.TestCase):
    def test_script_creates_git_repo_with_passing_unittest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "sample"

            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "create_sample_target_repo.py"), "--path", str(target)],
                check=True,
                capture_output=True,
                text=True,
            )

            subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=target, check=True, capture_output=True)
            self.assertEqual((target / ".gitignore").read_text(), "__pycache__/\n*.py[cod]\n")
            self.assertIn("Keep the sample change small", (target / "CONSTRAINTS.md").read_text())
            subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                cwd=target,
                check=True,
                capture_output=True,
                text=True,
            )

    def test_script_can_create_failing_sample(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "sample"

            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "create_sample_target_repo.py"), "--path", str(target), "--failing"],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn(str(target), result.stdout)
            gate = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                cwd=target,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(gate.returncode, 0)


if __name__ == "__main__":
    unittest.main()
