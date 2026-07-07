import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.pr_handoff_check import build_pr_handoff_check, write_pr_handoff_check


class PrHandoffCheckTests(unittest.TestCase):
    def test_ready_status_when_all_critical_checks_pass(self) -> None:
        result = check()

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["blocking_reasons"], [])
        self.assertEqual(result["warnings"], [])

    def test_needs_attention_when_verifier_failed(self) -> None:
        self.assert_blocked(check(verifier={"ok": False}), "Verifier did not pass.")

    def test_needs_attention_when_required_gate_failed(self) -> None:
        self.assert_blocked(check(gates=[{"required": True, "ok": False}]), "One or more required gates failed.")

    def test_needs_attention_when_review_recommendation_is_not_ready(self) -> None:
        self.assert_blocked(check(review_recommendation="manual_review_required"), "Review recommendation is manual_review_required.")

    def test_needs_attention_when_changed_files_are_empty(self) -> None:
        self.assert_blocked(check(verifier={"changed_files": []}), "No changed files were reported.")

    def test_needs_attention_when_human_required_paths_were_touched(self) -> None:
        self.assert_blocked(check(verifier={"human_required_touched": ["auth/login.py"]}), "Human-required paths were touched.")

    def test_needs_attention_when_task_scope_violations_exist(self) -> None:
        self.assert_blocked(check(verifier={"task_allowed_violations": ["x.py"]}), "Task scope violations were reported.")
        self.assert_blocked(check(verifier={"task_forbidden_touched": ["x.py"]}), "Task scope violations were reported.")

    def test_needs_attention_when_reserved_artifacts_touched(self) -> None:
        self.assert_blocked(check(verifier={"reserved_artifacts_touched": ["pr_body.md"]}), "Reserved run artifacts were touched in the target repo.")

    def test_needs_attention_when_worktree_path_is_missing(self) -> None:
        self.assert_blocked(check(worktree=SimpleNamespace(path=None, branch="agent/run-1")), "Worktree path is missing.")

    def test_needs_attention_when_worktree_path_does_not_exist(self) -> None:
        self.assert_blocked(check(worktree=SimpleNamespace(path=Path("/missing/nope"), branch="agent/run-1")), "Worktree path does not exist.")

    def test_needs_attention_when_worktree_is_not_a_git_repo(self) -> None:
        self.assert_blocked(check(runner=runner(git_repo=False)), "Worktree is not inside a git repo.")

    def test_needs_attention_when_branch_is_missing(self) -> None:
        self.assert_blocked(check(worktree=SimpleNamespace(path=Path(tempfile.gettempdir()), branch=None)), "Branch is missing.")

    def test_informational_warnings_when_only_origin_remote_is_missing(self) -> None:
        result = check(runner=runner(origin=False))

        self.assertEqual(result["status"], "informational_warnings")
        self.assertEqual(result["blocking_reasons"], [])
        self.assertEqual(result["warnings"], ["Origin remote is missing."])

    def test_informational_warnings_when_only_gh_is_missing(self) -> None:
        result = check(which=lambda _: None)

        self.assertEqual(result["status"], "informational_warnings")
        self.assertEqual(result["blocking_reasons"], [])
        self.assertEqual(result["warnings"], ["GitHub CLI is missing; this only affects the optional gh pr create command."])

    def test_artifacts_are_written(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            result = write_pr_handoff_check(run_dir, default_worktree(), default_gates(), verifier_result(), "ready_for_human_review", runner(), lambda _: "/usr/bin/gh")

            self.assertEqual(json.loads((run_dir / "pr_handoff_check.json").read_text()), result)
            markdown = (run_dir / "pr_handoff_check.md").read_text()
            self.assertIn("# PR Handoff Check", markdown)
            self.assertIn("- status: ready", markdown)
            self.assertIn("Review pr_commands.md manually before running any command.", markdown)

    def assert_blocked(self, result: dict[str, object], reason: str) -> None:
        self.assertEqual(result["status"], "needs_attention")
        self.assertIn(reason, result["blocking_reasons"])


def check(
    worktree=None,
    gates=None,
    verifier=None,
    review_recommendation="ready_for_human_review",
    runner=None,
    which=None,
) -> dict[str, object]:
    data = verifier_result()
    if verifier:
        data.update(verifier)
    return build_pr_handoff_check(
        worktree or default_worktree(),
        gates if gates is not None else default_gates(),
        data,
        review_recommendation,
        runner or globals()["runner"](),
        which or (lambda _: "/usr/bin/gh"),
    )


def default_worktree():
    return SimpleNamespace(path=Path(tempfile.gettempdir()), branch="agent/run-1")


def default_gates():
    return [{"required": True, "ok": True}]


def verifier_result():
    return {
        "ok": True,
        "changed_files": ["app.py"],
        "human_required_touched": [],
        "task_allowed_violations": [],
        "task_forbidden_touched": [],
        "reserved_artifacts_touched": [],
    }


def runner(git_repo=True, origin=True):
    def run(command, **_kwargs):
        ok = git_repo if command[-2:] == ["rev-parse", "--is-inside-work-tree"] else origin
        return subprocess.CompletedProcess(command, 0 if ok else 1, stdout="", stderr="")

    return run


if __name__ == "__main__":
    unittest.main()
