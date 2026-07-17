import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.memory_proposal import CONFIDENCE, ORDER, build_memory_proposal, write_memory_proposal
from agent_loop_factory.memory_context import MemoryContext, MemoryFile
from agent_loop_factory.skill import Skill
from agent_loop_factory.task_spec import TaskSpec


class MemoryProposalTests(unittest.TestCase):
    def test_clean_passing_run_produces_no_proposal(self) -> None:
        proposal = build_memory_proposal("run-1", task(), None, [gate()], verifier(), "ready_for_human_review", "ready", False)

        self.assertEqual(proposal["proposal_status"], "no_proposal")
        self.assertEqual(proposal["candidate_lessons"], [])
        self.assertTrue(proposal["requires_human_approval"])
        self.assertTrue(proposal["no_files_modified"])
        self.assertFalse(proposal["memory_context_included"])
        self.assertEqual(proposal["memory_files_included"], [])
        self.assertFalse(proposal["advisory_review_included"])
        self.assertIsNone(proposal["advisory_review_recommendation"])

    def test_records_included_memory_context(self) -> None:
        memory = MemoryContext([MemoryFile("memory/prompt-guidance/small-diffs.md", "Small.\n", 7)], 7)

        proposal = build_memory_proposal("run-1", task(), None, [gate()], verifier(), "ready_for_human_review", "ready", False, memory)

        self.assertTrue(proposal["memory_context_included"])
        self.assertEqual(proposal["memory_files_included"], ["memory/prompt-guidance/small-diffs.md"])

    def test_records_advisory_review_metadata_without_creating_lessons(self) -> None:
        proposal = build_memory_proposal("run-1", task(), None, [gate()], verifier(), "ready_for_human_review", "ready", False, advisory_review={"recommendation": "review_suggested"})

        self.assertTrue(proposal["advisory_review_included"])
        self.assertEqual(proposal["advisory_review_recommendation"], "review_suggested")
        self.assertEqual(proposal["candidate_lessons"], [])

    def test_dry_run_produces_no_proposal(self) -> None:
        proposal = build_memory_proposal("run-1", task(), None, [gate(ok=False)], verifier(ok=False, reasons=["worktree unavailable"]), "reject_or_rework", "needs_attention", True)

        self.assertEqual(proposal["proposal_status"], "no_proposal")
        self.assertEqual(proposal["candidate_lessons"], [])
        self.assertTrue(proposal["dry_run"])
        self.assertIn("Dry run only", proposal["summary"])

    def test_dry_run_worktree_unavailable_does_not_create_verifier_lesson(self) -> None:
        proposal = build_memory_proposal("run-1", task(), None, [], verifier(ok=False, reasons=["worktree unavailable"]), "reject_or_rework", "ready", True)

        self.assertEqual([lesson["trigger"] for lesson in proposal["candidate_lessons"]], [])

    def test_verifier_failure_produces_lesson(self) -> None:
        self.assert_trigger("verifier_failed", verifier(ok=False, reasons=["diff_line_count exceeds max_diff_lines: 9 > 8"]))

    def test_required_gate_failure_produces_lesson(self) -> None:
        self.assert_trigger("required_gate_failed", verifier(), gates=[gate(ok=False, required=True)])

    def test_optional_gate_warning_produces_lesson(self) -> None:
        self.assert_trigger("optional_gate_warning", verifier(), gates=[gate(ok=True, required=False, warning="slow")])

    def test_human_required_touched_produces_lesson(self) -> None:
        self.assert_trigger("human_required_touched", verifier(human_required_touched=["auth/login.py"]))

    def test_task_allowed_violations_produces_lesson(self) -> None:
        self.assert_trigger("task_scope_violation", verifier(task_allowed_violations=["tests/test_app.py"]))

    def test_task_forbidden_touched_produces_lesson(self) -> None:
        self.assert_trigger("task_scope_violation", verifier(task_forbidden_touched=["tests/test_app.py"]))

    def test_reserved_artifacts_touched_produces_lesson(self) -> None:
        self.assert_trigger("reserved_artifact_touched", verifier(reserved_artifacts_touched=["memory_proposal.md"]))

    def test_tests_weakened_or_deleted_produces_lesson(self) -> None:
        self.assert_trigger("tests_weakened_or_deleted", verifier(tests_weakened_or_deleted=True))

    def test_pr_handoff_needs_attention_produces_lesson(self) -> None:
        self.assert_trigger("pr_handoff_needs_attention", verifier(), pr_handoff_status="needs_attention")

    def test_pr_handoff_informational_warnings_produces_lesson(self) -> None:
        self.assert_trigger("pr_handoff_informational_warnings", verifier(), pr_handoff_status="informational_warnings")

    def test_multiple_triggers_are_ordered_and_confidence_is_fixed(self) -> None:
        proposal = build_memory_proposal(
            "run-1",
            task(),
            Skill("failing-test-fix", "body", "skills/failing-test-fix/SKILL.md"),
            [gate(ok=False), gate(ok=False, required=False)],
            verifier(
                ok=False,
                reasons=["bad"],
                tests_weakened_or_deleted=True,
                reserved_artifacts_touched=["run_report.md"],
                task_allowed_violations=["outside.py"],
                human_required_touched=["auth/login.py"],
            ),
            "reject_or_rework",
            "needs_attention",
            False,
        )

        triggers = [lesson["trigger"] for lesson in proposal["candidate_lessons"]]
        self.assertEqual(triggers, ORDER[:-1])
        self.assertEqual([lesson["confidence"] for lesson in proposal["candidate_lessons"]], [CONFIDENCE[trigger] for trigger in triggers])

    def test_writes_markdown_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            proposal = write_memory_proposal(run_dir, "run-1", task(), None, [], verifier(), "ready_for_human_review", "ready", False)

            self.assertTrue((run_dir / "memory_proposal.md").exists())
            self.assertTrue((run_dir / "memory_proposal.json").exists())
            self.assertEqual(json.loads((run_dir / "memory_proposal.json").read_text()), proposal)
            markdown = (run_dir / "memory_proposal.md").read_text()
            self.assertIn("# Memory Proposal", markdown)
            self.assertIn("* None. No reusable memory proposed for this run.", markdown)

    def assert_trigger(self, trigger: str, verifier_result: dict[str, object], gates: list[dict[str, object]] | None = None, pr_handoff_status: str = "ready") -> None:
        proposal = build_memory_proposal("run-1", task(), None, gates or [gate()], verifier_result, "manual_review_required", pr_handoff_status, False)

        self.assertEqual(proposal["proposal_status"], "proposed")
        self.assertIn(trigger, [lesson["trigger"] for lesson in proposal["candidate_lessons"]])


def task() -> TaskSpec:
    return TaskSpec("Fix add", "# Fix add\n", "tasks/fix.md")


def gate(ok: bool = True, required: bool = True, warning: str | None = None) -> dict[str, object]:
    return {"name": "unit", "command": "python3 -m unittest", "required": required, "ok": ok, "warning": warning}


def verifier(**overrides) -> dict[str, object]:
    result = {
        "ok": True,
        "reasons": [],
        "warnings": [],
        "changed_files": ["sample_math/__init__.py"],
        "changed_file_count": 1,
        "diff_line_count": 2,
        "human_required_touched": [],
        "reserved_artifacts_touched": [],
        "task_allowed_violations": [],
        "task_forbidden_touched": [],
        "tests_weakened_or_deleted": False,
    }
    result.update(overrides)
    return result


if __name__ == "__main__":
    unittest.main()
