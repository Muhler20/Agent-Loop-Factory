# Smoke Test Walkthrough

This walkthrough documents the proven sample target repo smoke test for Agent Loop Factory v6. It uses a tiny local Python repo with one failing unittest, a task spec, a local skill, a named required gate, the Codex implementer, and deterministic verifier artifacts.

## Paths

```text
~/coding-projects/agent-loop-factory
~/coding-projects/sample-target-repo
~/coding-projects/agent-worktrees
```

## Create The Failing Sample Target Repo

```bash
cd ~/coding-projects/agent-loop-factory
python3 scripts/create_sample_target_repo.py --failing
```

The script creates `~/coding-projects/sample-target-repo`, initializes git, and commits a small package where `sample_math.add(2, 3)` currently returns the wrong value.

## Temporarily Point Config At The Sample Repo

Edit `.agent/config.yaml` temporarily:

```yaml
target_repo_path: "../sample-target-repo"
worktree_base_path: "../agent-worktrees"
max_iterations: 3
max_changed_files: 8
max_diff_lines: 500
allowed_commands:
  - "python3 -m unittest discover -s tests"
gates:
  - name: unit tests
    command: "python3 -m unittest discover -s tests"
    required: true
implementer: "none"
codex_command: "codex"
codex_exec_args: []
human_required_paths:
  - "auth/"
  - "billing/"
  - "payments/"
  - "migrations/"
  - "infra/"
  - ".github/"
  - "Dockerfile"
  - "docker-compose.yml"
output_mode: "draft_pr_only"
auto_merge: false
auto_deploy: false
```

The important smoke-test pieces are `target_repo_path`, `worktree_base_path`, `allowed_commands`, and the named required gate `unit tests`.

## Run The Loop

```bash
python3 scripts/run_agent_loop.py \
  --task-file tasks/fix-sample-add.md \
  --skill failing-test-fix \
  --implementer codex
```

The command prints:

```text
run_id=<run_id>
run_dir=/home/mikestryke/coding-projects/agent-loop-factory/.agent/runs/<run_id>
```

## Inspect Artifacts

```bash
ls .agent/runs/<run_id>
sed -n '1,220p' .agent/runs/<run_id>/run_report.md
sed -n '1,260p' .agent/runs/<run_id>/review_bundle.md
cat .agent/runs/<run_id>/pr_title.txt
sed -n '1,220p' .agent/runs/<run_id>/pr_body.md
sed -n '1,220p' .agent/runs/<run_id>/pr_commands.md
sed -n '1,120p' .agent/runs/<run_id>/pr_handoff.md
sed -n '1,160p' .agent/runs/<run_id>/pr_handoff_check.md
cat .agent/runs/<run_id>/pr_handoff_check.json
cat .agent/runs/<run_id>/gate_results.json
cat .agent/runs/<run_id>/verifier_result.json
sed -n '1,220p' .agent/runs/<run_id>/diff_summary.md
sed -n '1,160p' .agent/runs/<run_id>/skill.md
sed -n '1,220p' .agent/runs/<run_id>/codex_prompt.md
```

Expected artifacts include:

- `run_report.md`
- `review_bundle.md`
- `pr_title.txt`
- `pr_body.md`
- `pr_commands.md`
- `pr_handoff.md`
- `pr_handoff_check.md`
- `pr_handoff_check.json`
- `gate_results.json`
- `verifier_result.json`
- `diff_summary.md`
- `skill.md`
- `codex_prompt.md`
- `codex_stdout.log`
- `codex_stderr.log`
- `codex_result.json`
- `task_spec.md`
- `stdout.log`
- `stderr.log`

## Expected Successful Result

In `run_report.md`:

- the worktree path includes `sample-target-repo`
- the gate named `unit tests` is `ok`
- verifier `ok` is `True`
- the review bundle path and recommendation are listed

In `review_bundle.md`:

- the changed file is `sample_math/__init__.py`
- the gates and verifier sections are present
- the recommendation is `ready_for_human_review`

In `verifier_result.json`:

- `changed_files` contains only `sample_math/__init__.py`
- `task_allowed_violations` is empty
- `task_forbidden_touched` is empty
- `reserved_artifacts_touched` is empty

In `gate_results.json`:

- `name` is `unit tests`
- `required` is `true`
- `ok` is `true`

In `diff_summary.md`:

- the diff shows the sample implementation fixed
- the changed file is `sample_math/__init__.py`

In `skill.md`:

- the copied skill is `Failing Test Fix`

In `codex_prompt.md`:

- the prompt includes the task spec
- the prompt includes the selected skill
- the prompt includes the local constraints from the sample target repo when present

## Cleanup

Restore `.agent/config.yaml` to the normal starter config:

```yaml
target_repo_path: "."
worktree_base_path: "../agent-worktrees"
max_iterations: 3
max_changed_files: 8
max_diff_lines: 500
allowed_commands:
  - "npm test"
  - "npm run lint"
  - "npm run typecheck"
  - "pytest"
  - "ruff check ."
  - "mypy ."
  - "python3 -m unittest discover -s tests"
gates:
  - "python3 -m unittest discover -s tests"
implementer: "none"
codex_command: "codex"
codex_exec_args: []
human_required_paths:
  - "auth/"
  - "billing/"
  - "payments/"
  - "migrations/"
  - "infra/"
  - ".github/"
  - "Dockerfile"
  - "docker-compose.yml"
output_mode: "draft_pr_only"
auto_merge: false
auto_deploy: false
```

Restore `.agent/state.json`:

```json
{
  "last_run_id": null,
  "runs": []
}
```

Restore `PROGRESS.md`:

```markdown
# Progress

## Current Goal

None.

## Last Run

None.

## In Progress

Manual supervised loop skeleton.

## Blockers

None.

## Next Action

Choose the first supervised task.

## Decisions

- v0 is manual and deterministic.
- v1 can call Codex only when explicitly requested.
- The default implementer is none.
- This project does not push, merge, deploy, or open PRs.
```

Optional worktree cleanup after review:

```bash
git -C ~/coding-projects/sample-target-repo worktree list
git -C ~/coding-projects/sample-target-repo worktree remove ~/coding-projects/agent-worktrees/sample-target-repo-<run_id>
git -C ~/coding-projects/sample-target-repo branch -D agent/<run_id>
```
