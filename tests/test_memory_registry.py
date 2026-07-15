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


def valid_memory(category: str = "prompt-guidance", title: str = "Keep Diffs Small", reviewed: str = "2099-01-01", extra: str = "") -> str:
    return f"""# {title}
status: active
category: {category}
source_run_id: run-1
created: 2099-01-01
last_reviewed: {reviewed}
confidence: high
{extra}
## Lesson

Keep the diff small.

## Evidence

Observed in run-1.

## When To Apply

Use for small tasks.

## When Not To Apply

Do not use when a larger redesign is requested.

## Suggested Enforcement

Review the diff.
"""


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
            self.assertEqual(result.warnings, [])

    def test_valid_active_memory_file_passes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_valid_registry(root)
            (root / "memory" / "prompt-guidance" / "small-diffs.md").write_text(valid_memory())

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

    def test_missing_required_metadata_fails(self) -> None:
        for field in ("status", "category", "source_run_id", "created", "last_reviewed", "confidence"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                write_valid_registry(root)
                lines = [line for line in valid_memory().splitlines() if not line.startswith(f"{field}:")]
                (root / "memory" / "prompt-guidance" / "bad.md").write_text("\n".join(lines) + "\n")

                result = validate_memory_registry(root)

                self.assertFalse(result.ok)
                self.assertIn(f"missing metadata {field}: memory/prompt-guidance/bad.md", result.errors)

    def test_invalid_metadata_values_fail(self) -> None:
        cases = (
            ("status: nope", "invalid status"),
            ("category: nope", "invalid category"),
            ("confidence: nope", "invalid confidence"),
        )
        for replacement, message in cases:
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                write_valid_registry(root)
                text = valid_memory().replace(replacement.split(":")[0] + ": " + {"status": "active", "category": "prompt-guidance", "confidence": "high"}[replacement.split(":")[0]], replacement)
                (root / "memory" / "prompt-guidance" / "bad.md").write_text(text)

                result = validate_memory_registry(root)

                self.assertFalse(result.ok)
                self.assertTrue(any(message in error for error in result.errors))

    def test_category_mismatch_with_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_valid_registry(root)
            (root / "memory" / "failure-patterns" / "bad.md").write_text(valid_memory(category="prompt-guidance"))

            result = validate_memory_registry(root)

            self.assertFalse(result.ok)
            self.assertIn("category mismatch in memory/failure-patterns/bad.md: expected failure-pattern, got prompt-guidance", result.errors)

    def test_missing_required_sections_fail(self) -> None:
        for section in ("## Lesson", "## Evidence", "## When To Apply", "## When Not To Apply", "## Suggested Enforcement"):
            with self.subTest(section=section), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                write_valid_registry(root)
                (root / "memory" / "prompt-guidance" / "bad.md").write_text(valid_memory().replace(section, "## Missing"))

                result = validate_memory_registry(root)

                self.assertFalse(result.ok)
                self.assertIn(f"missing section {section}: memory/prompt-guidance/bad.md", result.errors)

    def test_warning_only_hygiene_cases_pass(self) -> None:
        cases = (
            ("deprecated.md", valid_memory().replace("status: active", "status: deprecated"), "deprecated status outside memory/deprecated/"),
            ("superseded.md", valid_memory().replace("status: active", "status: superseded"), "superseded memory missing superseded-by"),
            ("stale.md", valid_memory(reviewed="2000-01-01"), "last_reviewed older than 180 days"),
            ("bad-date.md", valid_memory(reviewed="not-a-date"), "last_reviewed is not YYYY-MM-DD"),
        )
        for filename, text, warning in cases:
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                write_valid_registry(root)
                (root / "memory" / "prompt-guidance" / filename).write_text(text)

                result = validate_memory_registry(root)

                self.assertTrue(result.ok)
                self.assertTrue(any(warning in item for item in result.warnings))

    def test_duplicate_active_h1_title_warns(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_valid_registry(root)
            (root / "memory" / "prompt-guidance" / "a.md").write_text(valid_memory(title="Same"))
            (root / "memory" / "reviewer-guidance" / "b.md").write_text(valid_memory(category="reviewer-guidance", title="Same"))

            result = validate_memory_registry(root)

            self.assertTrue(result.ok)
            self.assertTrue(any("duplicate active memory title: Same" in warning for warning in result.warnings))

    def test_same_h1_title_in_active_and_deprecated_warns(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_valid_registry(root)
            (root / "memory" / "prompt-guidance" / "a.md").write_text(valid_memory(title="Old Lesson"))
            (root / "memory" / "deprecated" / "old.md").write_text("# Old Lesson\n")

            result = validate_memory_registry(root)

            self.assertTrue(result.ok)
            self.assertTrue(any("active memory title also exists in deprecated memory: Old Lesson" in warning for warning in result.warnings))

    def test_never_always_same_title_warns(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_valid_registry(root)
            (root / "memory" / "prompt-guidance" / "a.md").write_text(valid_memory(title="Rule").replace("Keep the diff small.", "Never weaken tests."))
            (root / "memory" / "reviewer-guidance" / "b.md").write_text(valid_memory(category="reviewer-guidance", title="Rule").replace("Keep the diff small.", "Always weaken tests."))

            result = validate_memory_registry(root)

            self.assertTrue(result.ok)
            self.assertTrue(any("possible always/never conflict for active memory title: Rule" in warning for warning in result.warnings))

    def test_check_memory_exits_zero_for_valid_registry(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_valid_registry(root)

            code, stdout = self.run_check_memory(root)

            self.assertEqual(code, 0)
            self.assertIn("memory registry ok", stdout)

    def test_check_memory_prints_warnings_and_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_valid_registry(root)
            (root / "memory" / "prompt-guidance" / "stale.md").write_text(valid_memory(reviewed="2000-01-01"))

            code, stdout = self.run_check_memory(root)

            self.assertEqual(code, 0)
            self.assertIn("memory registry ok with warnings", stdout)
            self.assertIn("last_reviewed older than 180 days", stdout)

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
