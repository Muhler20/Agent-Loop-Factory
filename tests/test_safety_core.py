import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.safety_core import find_safety_core_references, safety_core_patterns


class SafetyCoreTests(unittest.TestCase):
    def test_exact_text_and_glob_context_matches_are_deterministic(self) -> None:
        result = find_safety_core_references(
            "Change src/agent_loop_factory/verifier.py and src/agent_loop_factory/config.py.",
            ["reviewers/safety-reviewer.md"],
        )
        self.assertEqual(result["matches"], (
            "src/agent_loop_factory/verifier.py",
            "src/agent_loop_factory/config.py",
            "reviewers/safety-reviewer.md",
        ))
        self.assertTrue(result["references_detected"])
        self.assertEqual(result["matched_patterns"], (
            "src/agent_loop_factory/verifier.py",
            "src/agent_loop_factory/config.py",
            "reviewers/*",
        ))

    def test_normal_text_does_not_scan_or_discover_repo_files(self) -> None:
        self.assertEqual(find_safety_core_references("Update docs/README.md.")["matches"], ())
        self.assertIsInstance(safety_core_patterns(), tuple)


if __name__ == "__main__":
    unittest.main()
