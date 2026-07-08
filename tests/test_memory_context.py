import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.memory_context import MAX_MEMORY_FILE_BYTES, MAX_TOTAL_MEMORY_BYTES, load_memory_context, write_memory_context


class MemoryContextTests(unittest.TestCase):
    def test_one_valid_memory_file_is_accepted(self) -> None:
        with repo() as root:
            path = root / "memory" / "prompt-guidance" / "small-diffs.md"
            path.write_text("Keep diffs small.\n")

            context = load_memory_context(root, [Path("memory/prompt-guidance/small-diffs.md")])

            self.assertIsNotNone(context)
            self.assertEqual(context.paths, ["memory/prompt-guidance/small-diffs.md"])
            self.assertEqual(context.files[0].content, "Keep diffs small.\n")

    def test_multiple_valid_memory_files_are_accepted(self) -> None:
        with repo() as root:
            first = root / "memory" / "prompt-guidance" / "small-diffs.md"
            second = root / "memory" / "failure-patterns" / "test-weakening.md"
            first.write_text("Small diffs.\n")
            second.write_text("Never weaken tests.\n")

            context = load_memory_context(root, [first, second])

            self.assertEqual(context.paths, ["memory/prompt-guidance/small-diffs.md", "memory/failure-patterns/test-weakening.md"])

    def test_missing_memory_file_fails(self) -> None:
        with repo() as root:
            with self.assertRaisesRegex(ValueError, "memory file does not exist"):
                load_memory_context(root, [Path("memory/prompt-guidance/missing.md")])

    def test_memory_file_outside_memory_fails(self) -> None:
        with repo() as root:
            outside = root / "notes.md"
            outside.write_text("Nope.\n")
            with self.assertRaisesRegex(ValueError, "inside memory"):
                load_memory_context(root, [outside])

    def test_deprecated_memory_file_fails(self) -> None:
        with repo() as root:
            deprecated = root / "memory" / "deprecated" / "old.md"
            deprecated.write_text("Old.\n")
            with self.assertRaisesRegex(ValueError, "deprecated"):
                load_memory_context(root, [deprecated])

    def test_non_md_memory_file_fails(self) -> None:
        with repo() as root:
            path = root / "memory" / "prompt-guidance" / "bad.txt"
            path.write_text("Nope.\n")
            with self.assertRaisesRegex(ValueError, ".md extension"):
                load_memory_context(root, [path])

    def test_invalid_utf8_memory_file_fails(self) -> None:
        with repo() as root:
            path = root / "memory" / "prompt-guidance" / "bad.md"
            path.write_bytes(b"\xff")
            with self.assertRaisesRegex(ValueError, "valid UTF-8"):
                load_memory_context(root, [path])

    def test_oversized_memory_file_fails(self) -> None:
        with repo() as root:
            path = root / "memory" / "prompt-guidance" / "large.md"
            path.write_text("x" * (MAX_MEMORY_FILE_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "too large"):
                load_memory_context(root, [path])

    def test_total_memory_content_over_limit_fails(self) -> None:
        with repo() as root:
            first = root / "memory" / "prompt-guidance" / "first.md"
            second = root / "memory" / "prompt-guidance" / "second.md"
            third = root / "memory" / "prompt-guidance" / "third.md"
            first.write_text("x" * 20_000)
            second.write_text("x" * 20_000)
            third.write_text("x" * 20_001)
            with self.assertRaisesRegex(ValueError, "total memory context too large"):
                load_memory_context(root, [first, second, third])

    def test_duplicate_memory_file_fails(self) -> None:
        with repo() as root:
            path = root / "memory" / "prompt-guidance" / "small-diffs.md"
            path.write_text("Small.\n")
            with self.assertRaisesRegex(ValueError, "duplicate memory file"):
                load_memory_context(root, [path, path])

    def test_secret_like_string_fails(self) -> None:
        with repo() as root:
            path = root / "memory" / "prompt-guidance" / "bad.md"
            path.write_text("OPENAI_API_KEY=abc\n")
            with self.assertRaisesRegex(ValueError, "secret-like marker"):
                load_memory_context(root, [path])

    def test_writes_memory_context_artifacts(self) -> None:
        with repo() as root:
            run_dir = root / ".agent" / "runs" / "run-1"
            run_dir.mkdir(parents=True)
            path = root / "memory" / "prompt-guidance" / "small-diffs.md"
            path.write_text("Small diffs.\n")
            context = load_memory_context(root, [path])

            summary = write_memory_context(run_dir, "run-1", context)

            data = json.loads((run_dir / "memory_context.json").read_text())
            markdown = (run_dir / "memory_context.md").read_text()
            self.assertTrue(data["included"])
            self.assertEqual(data["files"], ["memory/prompt-guidance/small-diffs.md"])
            self.assertFalse(data["automatic_selection"])
            self.assertFalse(data["automatic_retrieval"])
            self.assertTrue(data["no_files_modified"])
            self.assertEqual(summary["memory_context_path"], ".agent/runs/run-1/memory_context.md")
            self.assertIn("# Memory Context", markdown)
            self.assertIn("### memory/prompt-guidance/small-diffs.md", markdown)
            self.assertIn("Small diffs.", markdown)


class repo:
    def __enter__(self) -> Path:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for dirname in ("failure-patterns", "prompt-guidance", "reviewer-guidance", "deprecated"):
            (root / "memory" / dirname).mkdir(parents=True, exist_ok=True)
        return root

    def __exit__(self, *args) -> None:
        self.tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
