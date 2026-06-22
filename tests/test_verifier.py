import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.config import Config
from agent_loop_factory.verifier import run_verifier


class VerifierTests(unittest.TestCase):
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
            result = verify(tmp, gates=[{"command": "test", "ok": False}])
            self.assertFalse(result["ok"])
            self.assertIn("one or more gates failed", result["reasons"])

    def test_fails_when_changed_file_count_exceeds_max_changed_files(self) -> None:
        with repo() as tmp:
            (tmp / "a.py").write_text("a = 1\n")
            (tmp / "b.py").write_text("b = 1\n")
            result = verify(tmp, Config(max_changed_files=1))
            self.assertFalse(result["ok"])
            self.assertIn("changed_file_count exceeds max_changed_files: 2 > 1", result["reasons"])

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


def verify(tmp: Path, config: Config | None = None, gates: list[dict[str, object]] | None = None) -> dict[str, object]:
    run_dir = tmp / "run"
    run_dir.mkdir()
    return run_verifier(config or Config(), tmp, run_dir, gates or [{"command": "test", "ok": True}])


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
