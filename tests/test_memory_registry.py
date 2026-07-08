import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.memory_registry import validate_memory_registry


ROOT = Path(__file__).resolve().parents[1]


def write_valid_registry(root: Path) -> None:
    memory = root / "memory"
    for dirname in ("failure-patterns", "prompt-guidance", "reviewer-guidance", "deprecated"):
        (memory / dirname).mkdir(parents=True, exist_ok=True)
        (memory / dirname / ".gitkeep").write_text("")
    (memory / "INDEX.md").write_text("# Memory Registry\n")
    (memory / "MEMORY_TEMPLATE.md").write_text("# <Memory Title>\n")


def load_cli_module():
    spec = importlib.util.spec_from_file_location("run_agent_loop_cli_memory", ROOT / "scripts" / "run_agent_loop.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MemoryRegistryTests(unittest.TestCase):
    def test_valid_registry_passes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_valid_registry(root)

            result = validate_memory_registry(root)

            self.assertTrue(result.ok)
            self.assertEqual(result.errors, [])

    def test_missing_index_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_valid_registry(root)
            (root / "memory" / "INDEX.md").unlink()

            result = validate_memory_registry(root)

            self.assertFalse(result.ok)
            self.assertIn("missing file: memory/INDEX.md", result.errors)

    def test_missing_template_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_valid_registry(root)
            (root / "memory" / "MEMORY_TEMPLATE.md").unlink()

            result = validate_memory_registry(root)

            self.assertFalse(result.ok)
            self.assertIn("missing file: memory/MEMORY_TEMPLATE.md", result.errors)

    def test_missing_category_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_valid_registry(root)
            (root / "memory" / "failure-patterns" / ".gitkeep").unlink()
            (root / "memory" / "failure-patterns").rmdir()

            result = validate_memory_registry(root)

            self.assertFalse(result.ok)
            self.assertIn("missing directory: memory/failure-patterns", result.errors)

    def test_secret_like_string_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_valid_registry(root)
            (root / "memory" / "prompt-guidance" / "bad.md").write_text("OPENAI_API_KEY=abc\n")

            result = validate_memory_registry(root)

            self.assertFalse(result.ok)
            self.assertIn("secret-like marker in memory/prompt-guidance/bad.md: OPENAI_API_KEY", result.errors)

    def test_oversized_memory_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_valid_registry(root)
            (root / "memory" / "reviewer-guidance" / "large.md").write_text("x" * (101 * 1024))

            result = validate_memory_registry(root)

            self.assertFalse(result.ok)
            self.assertTrue(any(error.startswith("file too large: memory/reviewer-guidance/large.md") for error in result.errors))

    def test_check_memory_exits_zero_for_valid_registry(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_valid_registry(root)

            code, stdout = self.run_check_memory(root)

            self.assertEqual(code, 0)
            self.assertIn("memory registry ok", stdout)

    def test_check_memory_exits_nonzero_for_invalid_registry(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_valid_registry(root)
            (root / "memory" / "INDEX.md").unlink()

            code, stdout = self.run_check_memory(root)

            self.assertEqual(code, 1)
            self.assertIn("memory registry invalid", stdout)
            self.assertIn("missing file: memory/INDEX.md", stdout)

    def test_check_memory_does_not_create_run_or_update_state_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_valid_registry(root)
            agent = root / ".agent"
            agent.mkdir()
            (agent / "state.json").write_text('{"last_run_id": null, "runs": []}\n')
            (root / "PROGRESS.md").write_text("original progress\n")

            code, _ = self.run_check_memory(root)

            self.assertEqual(code, 0)
            self.assertFalse((agent / "runs").exists())
            self.assertEqual((agent / "state.json").read_text(), '{"last_run_id": null, "runs": []}\n')
            self.assertEqual((root / "PROGRESS.md").read_text(), "original progress\n")

    def run_check_memory(self, root: Path) -> tuple[int, str]:
        module = load_cli_module()

        def fake_run(*args, **kwargs):
            raise AssertionError("run should not be called")

        old_argv = sys.argv
        old_root = module.ROOT
        module.ROOT = root
        module.run = fake_run
        sys.argv = ["run_agent_loop.py", "--check-memory"]
        stdout = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout):
                code = module.main()
        finally:
            sys.argv = old_argv
            module.ROOT = old_root
        return code, stdout.getvalue()


if __name__ == "__main__":
    unittest.main()
