import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.reviewer_rubric import load_reviewer_rubric, load_reviewer_rubrics


class ReviewerRubricTests(unittest.TestCase):
    def test_valid_rubric_passes(self) -> None:
        with repo() as root:
            rubric = load_reviewer_rubric(root, "reviewers/test.md")
            self.assertEqual(rubric.source_path, "reviewers/test.md")
            self.assertIn("## Review Focus", rubric.contents)

    def test_invalid_rubrics_fail(self) -> None:
        cases = [
            ("missing.md", None, "does not exist"),
            ("outside.md", valid_text(), "inside reviewers"),
            ("test.txt", valid_text(), ".md extension"),
            ("bad.md", b"\xff", "valid UTF-8"),
            ("big.md", valid_text() + ("x" * (25 * 1024)), "exceeds 25 KB"),
            ("README.md", valid_text(), "README.md is not"),
            ("RUBRIC_TEMPLATE.md", valid_text(), "RUBRIC_TEMPLATE.md is not"),
            ("secret.md", valid_text() + "\nGITHUB_TOKEN=abc\n", "secret-like"),
            ("no-status.md", valid_text().replace("* status: active\n", ""), "status"),
            ("no-category.md", valid_text().replace("* category: tests\n", ""), "category"),
            ("no-advisory.md", valid_text().replace("* advisory_only: true\n", ""), "advisory_only"),
            ("bad-status.md", valid_text().replace("status: active", "status: draft"), "status must"),
            ("deprecated.md", valid_text().replace("status: active", "status: deprecated"), "deprecated"),
            ("bad-category.md", valid_text().replace("category: tests", "category: nope"), "category is invalid"),
            ("false-advisory.md", valid_text().replace("advisory_only: true", "advisory_only: false"), "advisory_only must be true"),
            ("no-focus.md", valid_text().replace("## Review Focus\n", ""), "## Review Focus"),
            ("no-questions.md", valid_text().replace("## Questions To Ask\n", ""), "## Questions To Ask"),
            ("no-red.md", valid_text().replace("## Red Flags\n", ""), "## Red Flags"),
            ("no-evidence.md", valid_text().replace("## Evidence To Cite\n", ""), "## Evidence To Cite"),
            ("no-actions.md", valid_text().replace("## Suggested Human Actions\n", ""), "## Suggested Human Actions"),
            ("no-reminder.md", valid_text().replace("## Non-Authority Reminder\n", ""), "## Non-Authority Reminder"),
        ]
        for name, content, error in cases:
            with self.subTest(name=name):
                with repo() as root:
                    path = root / ("outside.md" if name == "outside.md" else f"reviewers/{name}")
                    if content is not None:
                        if isinstance(content, bytes):
                            path.write_bytes(content)
                        else:
                            path.write_text(content)
                    with self.assertRaisesRegex(ValueError, error):
                        load_reviewer_rubric(root, name if name == "outside.md" else f"reviewers/{name}")

    def test_duplicate_resolved_paths_fail(self) -> None:
        with repo() as root:
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_reviewer_rubrics(root, ["reviewers/test.md", root / "reviewers" / "test.md"])


def valid_text() -> str:
    return """# Test

* status: active
* category: tests
* advisory_only: true

## Review Focus

Focus.

## Questions To Ask

Ask.

## Red Flags

Flags.

## Evidence To Cite

Evidence.

## Suggested Human Actions

Act.

## Non-Authority Reminder

* This rubric guides advisory review only.
* It does not override gates.
* It does not override verifier_result.json.
* It does not override task scope, constraints, memory hygiene, or human approval boundaries.
"""


class repo:
    def __enter__(self) -> Path:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.__enter__())
        (root / "reviewers").mkdir()
        (root / "reviewers" / "test.md").write_text(valid_text())
        return root

    def __exit__(self, *exc) -> None:
        self.tmp.__exit__(*exc)


if __name__ == "__main__":
    unittest.main()
