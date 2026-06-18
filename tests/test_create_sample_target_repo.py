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
            subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                cwd=target,
                check=True,
                capture_output=True,
                text=True,
            )


if __name__ == "__main__":
    unittest.main()
