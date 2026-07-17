import tempfile
import unittest
import sys
import json
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.orchestrator import run
from agent_loop_factory.context_intake import ContextData
from agent_loop_factory.memory_context import MemoryContext, MemoryFile
from agent_loop_factory.reviewer_rubric import ReviewerRubric
from agent_loop_factory.skill import Skill


def write_agent_config(tmp_path: Path) -> None:
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


def write_normal_config(tmp_path: Path) -> None:
    agent = tmp_path / ".agent"
    (agent / "runs").mkdir(parents=True)
    (agent / "config.yaml").write_text(
        'target_repo_path: "target"\n'
        'worktree_base_path: "worktrees"\n'
        "max_iterations: 3\n"
        "max_changed_files: 8\n"
        "max_diff_lines: 500\n"
        "allowed_commands:\n"
        '  - "python3 -c pass"\n'
        "gates:\n"
        '  - "python3 -c pass"\n'
        "human_required_paths:\n"
        '  - "auth/"\n'
        'output_mode: "draft_pr_only"\n'
        "auto_merge: false\n"
        "auto_deploy: false\n"
    )


def init_target_repo(path: Path) -> None:
    path.mkdir()
    (path / "app.py").write_text("print('hello')\n")
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=path, check=True, capture_output=True, text=True)


def advisory_stdout(recommendation: str = "no_concerns") -> dict[str, object]:
    return {
        "included": True,
        "advisory_only": True,
        "does_not_affect_verifier": True,
        "reviewer": "codex",
        "recommendation": recommendation,
        "summary": "No deterministic authority claimed.",
        "findings": [],
        "requires_human_approval": True,
        "no_files_modified": True,
    }


def valid_rubric() -> str:
    return """# Test Reviewer

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


class OrchestratorDryRunTests(unittest.TestCase):
    def test_orchestrator_dry_run_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_agent_config(tmp_path)

            result = run("test task description", tmp_path, dry_run=True)
            run_dir = Path(result["run_dir"])

            self.assertTrue(result["dry_run"])
            self.assertTrue((run_dir / "run_report.md").exists())
            self.assertTrue((run_dir / "gate_results.json").exists())
            self.assertTrue((run_dir / "verifier_result.json").exists())
            self.assertTrue((run_dir / "stdout.log").exists())
            self.assertTrue((run_dir / "stderr.log").exists())
            self.assertTrue((run_dir / "diff_summary.md").exists())
            self.assertTrue((run_dir / "review_bundle.md").exists())
            self.assertTrue((run_dir / "pr_title.txt").exists())
            self.assertTrue((run_dir / "pr_body.md").exists())
            self.assertTrue((run_dir / "pr_commands.md").exists())
            self.assertTrue((run_dir / "pr_handoff.md").exists())
            self.assertTrue((run_dir / "pr_handoff_check.md").exists())
            self.assertTrue((run_dir / "pr_handoff_check.json").exists())
            self.assertTrue((run_dir / "memory_proposal.md").exists())
            self.assertTrue((run_dir / "memory_proposal.json").exists())
            self.assertFalse((run_dir / "memory_context.md").exists())
            self.assertFalse((run_dir / "memory_context.json").exists())
            self.assertEqual((run_dir / "task_spec.md").read_text(), "# test task description\n\ntest task description\n")
            report = (run_dir / "run_report.md").read_text()
            self.assertIn("task_source: inline", report)
            self.assertIn(f"path: .agent/runs/{result['run_id']}/review_bundle.md", report)
            self.assertIn(f"pr_title: .agent/runs/{result['run_id']}/pr_title.txt", report)
            self.assertIn(f"pr_body: .agent/runs/{result['run_id']}/pr_body.md", report)
            self.assertIn(f"pr_commands: .agent/runs/{result['run_id']}/pr_commands.md", report)
            self.assertIn(f"pr_handoff_check: .agent/runs/{result['run_id']}/pr_handoff_check.md", report)
            self.assertIn(f"pr_handoff_check_json: .agent/runs/{result['run_id']}/pr_handoff_check.json", report)
            self.assertIn(f"path: .agent/runs/{result['run_id']}/memory_proposal.md", report)
            self.assertIn(f"json: .agent/runs/{result['run_id']}/memory_proposal.json", report)
            self.assertIn("proposal_status: no_proposal", report)
            self.assertIn("handoff_check_status: needs_attention", report)
            self.assertIn("no commands executed: true", report)
            self.assertIn("## Memory Proposal", (run_dir / "review_bundle.md").read_text())
            self.assertIn("memory_proposal.md", (run_dir / "review_bundle.md").read_text())
            self.assertIn("# Memory Proposal", (run_dir / "pr_body.md").read_text())
            self.assertIn("* memory proposal: memory_proposal.md", (run_dir / "pr_body.md").read_text())
            self.assertIn("* memory_proposal.md:", (run_dir / "pr_handoff.md").read_text())
            self.assertIn("* memory_proposal.json:", (run_dir / "pr_handoff.md").read_text())
            self.assertIn("## Draft PR Handoff", (run_dir / "review_bundle.md").read_text())
            self.assertIn("- handoff check status: needs_attention", (run_dir / "review_bundle.md").read_text())
            self.assertIn("* handoff check status: needs_attention", (run_dir / "pr_handoff.md").read_text())
            self.assertIn("No push or PR creation was performed.", (run_dir / "review_bundle.md").read_text())
            self.assertIn("recommendation: reject_or_rework", report)
            self.assertFalse((run_dir / "codex_result.json").exists())
            self.assertFalse((run_dir / "advisory_review.json").exists())
            self.assertIn("## Current Goal", (tmp_path / "PROGRESS.md").read_text())

    def test_dry_run_with_advisory_reviewer_does_not_call_reviewer(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_agent_config(tmp_path)

            def fake_reviewer(*args, **kwargs):
                raise AssertionError("reviewer should not be called")

            result = run("test task description", tmp_path, dry_run=True, advisory_reviewer="codex", advisory_runner=fake_reviewer)
            run_dir = Path(result["run_dir"])

            self.assertFalse((run_dir / "advisory_review_prompt.md").exists())
            self.assertFalse((run_dir / "advisory_review.json").exists())
            self.assertFalse((run_dir / "advisory_review_rubric.md").exists())
            self.assertIn("## Advisory Review\n\n- included: false", (run_dir / "run_report.md").read_text())

    def test_dry_run_with_reviewer_rubric_validates_but_does_not_call_reviewer(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_agent_config(tmp_path)
            (tmp_path / "reviewers").mkdir()
            (tmp_path / "reviewers" / "test.md").write_text(valid_rubric())

            def fake_reviewer(*args, **kwargs):
                raise AssertionError("reviewer should not be called")

            result = run("test task description", tmp_path, dry_run=True, advisory_reviewer="codex", reviewer_rubric="reviewers/test.md", advisory_runner=fake_reviewer)
            run_dir = Path(result["run_dir"])

            self.assertFalse((run_dir / "advisory_review_rubric.md").exists())
            self.assertFalse((run_dir / "advisory_review.json").exists())

    def test_advisory_reviewer_artifacts_and_references_are_written_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_normal_config(tmp_path)
            init_target_repo(tmp_path / "target")

            def fake_reviewer(command, **kwargs):
                return subprocess.CompletedProcess(command, 0, json.dumps(advisory_stdout("review_suggested")), "")

            result = run("inspect only", tmp_path, dry_run=False, advisory_reviewer="codex", advisory_runner=fake_reviewer)
            run_dir = Path(result["run_dir"])
            proposal = json.loads((run_dir / "memory_proposal.json").read_text())

            for name in [
                "advisory_review_prompt.md",
                "advisory_review_stdout.log",
                "advisory_review_stderr.log",
                "advisory_review_result.json",
                "advisory_review.md",
                "advisory_review.json",
            ]:
                self.assertTrue((run_dir / name).exists(), name)
            self.assertIn("## Advisory Review", (run_dir / "run_report.md").read_text())
            self.assertIn("recommendation: review_suggested", (run_dir / "run_report.md").read_text())
            self.assertIn("prompt: advisory_review_prompt.md", (run_dir / "run_report.md").read_text())
            self.assertIn("stdout: advisory_review_stdout.log", (run_dir / "run_report.md").read_text())
            self.assertIn("stderr: advisory_review_stderr.log", (run_dir / "run_report.md").read_text())
            self.assertIn("## Advisory Review", (run_dir / "review_bundle.md").read_text())
            self.assertIn("See advisory_review.md and advisory_review.json.", (run_dir / "review_bundle.md").read_text())
            self.assertIn("# Advisory Review", (run_dir / "pr_body.md").read_text())
            self.assertIn("advisory_review.md", (run_dir / "pr_body.md").read_text())
            self.assertIn("advisory_review_result.json", (run_dir / "pr_handoff.md").read_text())
            self.assertIn("advisory_review_prompt.md", (run_dir / "pr_handoff.md").read_text())
            self.assertIn("advisory_review_stdout.log", (run_dir / "pr_handoff.md").read_text())
            self.assertIn("advisory_review_stderr.log", (run_dir / "pr_handoff.md").read_text())
            self.assertTrue(proposal["advisory_review_included"])
            self.assertEqual(proposal["advisory_review_recommendation"], "review_suggested")
            self.assertFalse(proposal["reviewer_rubric_included"])
            self.assertFalse(json.loads((run_dir / "advisory_review.json").read_text())["reviewer_rubric_included"])
            self.assertFalse((run_dir / "advisory_review_rubric.md").exists())

    def test_reviewer_rubric_artifacts_and_references_are_written_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_normal_config(tmp_path)
            init_target_repo(tmp_path / "target")
            rubric = ReviewerRubric("reviewers/test-reviewer.md", Path("/tmp/test-reviewer.md"), valid_rubric(), len(valid_rubric()))

            def fake_reviewer(command, **kwargs):
                return subprocess.CompletedProcess(command, 0, json.dumps(advisory_stdout("review_suggested")), "")

            result = run("inspect only", tmp_path, dry_run=False, advisory_reviewer="codex", reviewer_rubric=rubric, advisory_runner=fake_reviewer)
            run_dir = Path(result["run_dir"])
            proposal = json.loads((run_dir / "memory_proposal.json").read_text())
            advisory = json.loads((run_dir / "advisory_review.json").read_text())
            advisory_result = json.loads((run_dir / "advisory_review_result.json").read_text())

            self.assertTrue((run_dir / "advisory_review_rubric.md").exists())
            self.assertTrue((run_dir / "advisory_review_rubric.json").exists())
            self.assertTrue(advisory["reviewer_rubric_included"])
            self.assertEqual(advisory["reviewer_rubric_path"], "reviewers/test-reviewer.md")
            self.assertFalse(advisory["reviewer_rubric_automatic_selection"])
            self.assertTrue(advisory_result["reviewer_rubric_included"])
            self.assertTrue(proposal["reviewer_rubric_included"])
            self.assertEqual(proposal["reviewer_rubric_path"], "reviewers/test-reviewer.md")
            self.assertFalse(proposal["reviewer_rubric_automatic_selection"])
            self.assertIn("reviewer rubric: advisory_review_rubric.md / advisory_review_rubric.json", (run_dir / "run_report.md").read_text())
            self.assertIn("Reviewer rubric was explicitly selected.", (run_dir / "review_bundle.md").read_text())
            self.assertIn("reviewer rubric source: reviewers/test-reviewer.md", (run_dir / "pr_body.md").read_text())
            self.assertIn("advisory_review_rubric.md", (run_dir / "pr_handoff.md").read_text())

    def test_invalid_reviewer_rubric_stops_before_run_directory(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_agent_config(tmp_path)

            with self.assertRaisesRegex(ValueError, "does not exist"):
                run("test task description", tmp_path, dry_run=True, advisory_reviewer="codex", reviewer_rubric="reviewers/missing.md")

            self.assertEqual(list((tmp_path / ".agent" / "runs").iterdir()), [])

    def test_advisory_reviewer_failure_does_not_change_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_normal_config(tmp_path)
            init_target_repo(tmp_path / "target")

            def failing_reviewer(command, **kwargs):
                return subprocess.CompletedProcess(command, 1, "bad\n", "reviewer failed\n")

            result = run("inspect only", tmp_path, dry_run=False, advisory_reviewer="codex", advisory_runner=failing_reviewer)
            run_dir = Path(result["run_dir"])
            verifier = json.loads((run_dir / "verifier_result.json").read_text())
            advisory = json.loads((run_dir / "advisory_review.json").read_text())

            self.assertEqual(advisory["recommendation"], "reviewer_output_unparseable")
            self.assertTrue("reviewer process returned non-zero" in advisory["parse_error"])
            self.assertIn("ok", verifier)

    def test_advisory_reviewer_does_not_change_verifier_result_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_normal_config(tmp_path)
            init_target_repo(tmp_path / "target")

            without = run("inspect only", tmp_path, dry_run=False)

            def fake_reviewer(command, **kwargs):
                return subprocess.CompletedProcess(command, 0, json.dumps(advisory_stdout()), "")

            with_review = run("inspect only", tmp_path, dry_run=False, advisory_reviewer="codex", advisory_runner=fake_reviewer)

            self.assertEqual(
                (Path(without["run_dir"]) / "verifier_result.json").read_bytes(),
                (Path(with_review["run_dir"]) / "verifier_result.json").read_bytes(),
            )

    def test_orchestrator_dry_run_accepts_task_file_body(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_agent_config(tmp_path)
            task_file = tmp_path / "task.md"
            body = "# Fix sample add\n\n## Goal\n\nFix add.\n\n## Allowed files\n\n- `sample_math/__init__.py`\n\n## Forbidden files\n\n- `tests/`\n"
            task_file.write_text(body)

            result = run(body, tmp_path, dry_run=True, task_file_path=str(task_file))
            run_dir = Path(result["run_dir"])
            report = (run_dir / "run_report.md").read_text()
            verifier = json.loads((run_dir / "verifier_result.json").read_text())

            self.assertEqual((run_dir / "task_spec.md").read_text(), body)
            self.assertIn("task_title: Fix sample add", report)
            self.assertIn("task_source: file", report)
            self.assertIn(f"task_file_path: {task_file}", report)
            self.assertIn("Task allowed files:\n- sample_math/__init__.py", report)
            self.assertIn("Task forbidden files:\n- tests/", report)
            self.assertIn("- task source: file", (run_dir / "review_bundle.md").read_text())
            self.assertEqual(verifier["task_allowed_files"], ["sample_math/__init__.py"])
            self.assertEqual(verifier["task_forbidden_files"], ["tests/"])

    def test_skill_artifact_is_written_when_skill_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_agent_config(tmp_path)
            skill = Skill("failing-test-fix", "Keep tests strong.\n", str(tmp_path / "skills/failing-test-fix/SKILL.md"))

            result = run("test task description", tmp_path, dry_run=True, skill=skill)
            run_dir = Path(result["run_dir"])
            report = (run_dir / "run_report.md").read_text()

            self.assertEqual((run_dir / "skill.md").read_text(), "Keep tests strong.\n")
            self.assertIn("## Skill", report)
            self.assertIn("skill_name: failing-test-fix", report)
            self.assertIn("skill_source: file", report)
            self.assertIn(f"skill_file_path: {skill.skill_file_path}", report)
            self.assertIn("- skill name: failing-test-fix", (run_dir / "review_bundle.md").read_text())

    def test_skill_artifact_is_not_written_without_skill(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_agent_config(tmp_path)

            result = run("test task description", tmp_path, dry_run=True)
            run_dir = Path(result["run_dir"])
            report = (run_dir / "run_report.md").read_text()

            self.assertFalse((run_dir / "skill.md").exists())
            self.assertIn("## Skill", report)
            self.assertIn("skill_name: none", report)
            self.assertIn("skill_source: none", report)
            self.assertIn("- skill name: None", (run_dir / "review_bundle.md").read_text())

    def test_context_artifacts_are_written_when_context_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_agent_config(tmp_path)
            context = ContextData("issue.md", "Issue says add is broken.\n", 26, "ci.log", "FAILED test_add\n", 16)

            result = run("test task description", tmp_path, dry_run=True, context=context)
            run_dir = Path(result["run_dir"])
            summary = json.loads((run_dir / "context_summary.json").read_text())
            report = (run_dir / "run_report.md").read_text()
            bundle = (run_dir / "review_bundle.md").read_text()
            pr_body = (run_dir / "pr_body.md").read_text()

            self.assertEqual((run_dir / "issue_context.md").read_text(), "Issue says add is broken.\n")
            self.assertEqual((run_dir / "ci_context.log").read_text(), "FAILED test_add\n")
            self.assertEqual(summary["issue_file_path"], "issue.md")
            self.assertEqual(summary["issue_size_bytes"], 26)
            self.assertEqual(summary["issue_artifact_path"], f".agent/runs/{result['run_id']}/issue_context.md")
            self.assertEqual(summary["ci_log_file_path"], "ci.log")
            self.assertEqual(summary["ci_log_size_bytes"], 16)
            self.assertEqual(summary["ci_log_artifact_path"], f".agent/runs/{result['run_id']}/ci_context.log")
            self.assertIn("## External Context", report)
            self.assertIn(f"issue_context: .agent/runs/{result['run_id']}/issue_context.md", report)
            self.assertIn("## External Context", bundle)
            self.assertIn("issue context artifact path:", bundle)
            self.assertIn("# External Context", pr_body)
            self.assertIn("* issue context: issue_context.md", pr_body)

    def test_context_summary_is_written_without_context_sections(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_agent_config(tmp_path)

            result = run("test task description", tmp_path, dry_run=True)
            run_dir = Path(result["run_dir"])
            summary = json.loads((run_dir / "context_summary.json").read_text())

            self.assertFalse((run_dir / "issue_context.md").exists())
            self.assertFalse((run_dir / "ci_context.log").exists())
            self.assertIsNone(summary["issue_file_path"])
            self.assertIsNone(summary["issue_artifact_path"])
            self.assertIsNone(summary["ci_log_file_path"])
            self.assertIsNone(summary["ci_log_artifact_path"])

    def test_memory_context_artifacts_and_references_are_written_when_included(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_agent_config(tmp_path)
            memory = MemoryContext([MemoryFile("memory/prompt-guidance/small-diffs.md", "Keep diffs small.\n", 18)], 18)

            result = run("test task description", tmp_path, dry_run=True, memory_context=memory)
            run_dir = Path(result["run_dir"])

            memory_json = json.loads((run_dir / "memory_context.json").read_text())
            proposal_json = json.loads((run_dir / "memory_proposal.json").read_text())
            self.assertTrue(memory_json["included"])
            self.assertEqual(memory_json["files"], ["memory/prompt-guidance/small-diffs.md"])
            self.assertIn("Keep diffs small.", (run_dir / "memory_context.md").read_text())
            self.assertIn("## Memory Context", (run_dir / "run_report.md").read_text())
            self.assertIn(f"path: .agent/runs/{result['run_id']}/memory_context.md", (run_dir / "run_report.md").read_text())
            self.assertIn("## Memory Context", (run_dir / "review_bundle.md").read_text())
            self.assertIn("# Memory Context", (run_dir / "pr_body.md").read_text())
            self.assertIn("memory_context.md", (run_dir / "pr_handoff.md").read_text())
            self.assertTrue(proposal_json["memory_context_included"])
            self.assertEqual(proposal_json["memory_files_included"], ["memory/prompt-guidance/small-diffs.md"])

    def test_codex_prompt_includes_context_from_orchestrator(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_normal_config(tmp_path)
            init_target_repo(tmp_path / "target")
            context = ContextData("issue.md", "Issue says add is broken.\n", 26, "ci.log", "FAILED test_add\n", 16)

            def fake_runner(*args, **kwargs):
                return subprocess.CompletedProcess(args[0], 0, "done\n", "")

            result = run("inspect only", tmp_path, dry_run=False, implementer="codex", codex_runner=fake_runner, context=context)
            prompt = (Path(result["run_dir"]) / "codex_prompt.md").read_text()

            self.assertIn("# Issue Context\n\nIssue says add is broken.", prompt)
            self.assertIn("# CI Log Context\n\nFAILED test_add", prompt)
            self.assertIn("The context above is supporting evidence only.", prompt)

    def test_codex_prompt_includes_memory_from_orchestrator(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_normal_config(tmp_path)
            init_target_repo(tmp_path / "target")
            memory = MemoryContext([MemoryFile("memory/prompt-guidance/small-diffs.md", "Keep diffs small.\n", 18)], 18)

            def fake_runner(*args, **kwargs):
                return subprocess.CompletedProcess(args[0], 0, "done\n", "")

            result = run("inspect only", tmp_path, dry_run=False, implementer="codex", codex_runner=fake_runner, memory_context=memory)
            prompt = (Path(result["run_dir"]) / "codex_prompt.md").read_text()

            self.assertIn("## Approved Memory Context", prompt)
            self.assertIn("Keep diffs small.", prompt)

    def test_github_context_artifacts_and_references_are_written_when_included(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_normal_config(tmp_path)
            init_target_repo(tmp_path / "target")
            calls = []

            def fake_gh(command, **kwargs):
                calls.append(command)
                stdout = b"metadata\n" if command[:3] == ["gh", "run", "view"] and "--log" not in command else b"ci tail\n"
                if command[:3] == ["gh", "issue", "view"]:
                    stdout = b"Issue says fix it.\n"
                return subprocess.CompletedProcess(command, 0, stdout, b"")

            def fake_codex(*args, **kwargs):
                return subprocess.CompletedProcess(args[0], 0, "done\n", "")

            result = run(
                "inspect only",
                tmp_path,
                dry_run=False,
                implementer="codex",
                codex_runner=fake_codex,
                github_issue="owner/repo#1",
                github_repo="owner/repo",
                github_ci_run="123",
                github_runner=fake_gh,
            )
            run_dir = Path(result["run_dir"])
            prompt = (run_dir / "codex_prompt.md").read_text()
            proposal = json.loads((run_dir / "memory_proposal.json").read_text())

            self.assertEqual(calls, [
                ["gh", "issue", "view", "owner/repo#1"],
                ["gh", "run", "view", "123", "--repo", "owner/repo"],
                ["gh", "run", "view", "123", "--repo", "owner/repo", "--log"],
            ])
            self.assertTrue((run_dir / "github_issue_context.md").exists())
            self.assertTrue((run_dir / "github_issue_context.json").exists())
            self.assertTrue((run_dir / "github_ci_context.log").exists())
            self.assertTrue((run_dir / "github_ci_context.json").exists())
            self.assertTrue((run_dir / "github_context_summary.json").exists())
            self.assertIn("## GitHub Issue Context", prompt)
            self.assertIn("Issue says fix it.", prompt)
            self.assertIn("## GitHub CI Context", prompt)
            self.assertIn("ci tail", prompt)
            self.assertIn("no GitHub writes: true", (run_dir / "run_report.md").read_text())
            self.assertIn("## GitHub Context", (run_dir / "review_bundle.md").read_text())
            self.assertIn("# GitHub Context", (run_dir / "pr_body.md").read_text())
            self.assertIn("github_context_summary.json", (run_dir / "pr_handoff.md").read_text())
            self.assertTrue(proposal["github_context_included"])
            self.assertTrue(proposal["github_issue_included"])
            self.assertTrue(proposal["github_ci_included"])

    def test_github_dry_run_does_not_call_gh_or_write_github_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_agent_config(tmp_path)

            def fake_gh(*args, **kwargs):
                raise AssertionError("gh should not be called")

            result = run("test task description", tmp_path, dry_run=True, github_issue="owner/repo#1", github_runner=fake_gh)
            run_dir = Path(result["run_dir"])

            self.assertFalse((run_dir / "github_issue_context.md").exists())
            self.assertFalse((run_dir / "github_context_summary.json").exists())
            proposal = json.loads((run_dir / "memory_proposal.json").read_text())
            self.assertFalse(proposal["github_context_included"])

    def test_github_failure_stops_before_state_and_progress(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_normal_config(tmp_path)
            init_target_repo(tmp_path / "target")

            def fake_gh(command, **kwargs):
                return subprocess.CompletedProcess(command, 1, b"", b"auth failed\n")

            with self.assertRaisesRegex(ValueError, "auth failed"):
                run("inspect only", tmp_path, dry_run=False, github_issue="owner/repo#1", github_runner=fake_gh)

            self.assertFalse((tmp_path / ".agent" / "state.json").exists())
            self.assertFalse((tmp_path / "PROGRESS.md").exists())

    def test_invalid_github_identifier_stops_before_run_directory(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_agent_config(tmp_path)

            with self.assertRaisesRegex(ValueError, "--github-issue"):
                run("test task description", tmp_path, dry_run=True, github_issue="owner/repo#abc")

            self.assertEqual(list((tmp_path / ".agent" / "runs").iterdir()), [])
            self.assertFalse((tmp_path / ".agent" / "state.json").exists())
            self.assertFalse((tmp_path / "PROGRESS.md").exists())

    def test_codex_prompt_omits_empty_context_sections_from_orchestrator(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_normal_config(tmp_path)
            init_target_repo(tmp_path / "target")

            def fake_runner(*args, **kwargs):
                return subprocess.CompletedProcess(args[0], 0, "done\n", "")

            result = run("inspect only", tmp_path, dry_run=False, implementer="codex", codex_runner=fake_runner)
            prompt = (Path(result["run_dir"]) / "codex_prompt.md").read_text()

            self.assertNotIn("# Issue Context", prompt)
            self.assertNotIn("# CI Log Context", prompt)

    def test_orchestrator_normal_run_writes_review_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            write_normal_config(tmp_path)
            init_target_repo(tmp_path / "target")

            result = run("inspect only", tmp_path, dry_run=False)
            run_dir = Path(result["run_dir"])
            report = (run_dir / "run_report.md").read_text()

            self.assertTrue(result["ok"])
            self.assertTrue((run_dir / "review_bundle.md").exists())
            self.assertIn("recommendation: ready_for_human_review", report)


if __name__ == "__main__":
    unittest.main()
