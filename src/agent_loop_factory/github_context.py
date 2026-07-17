from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


MAX_CI_LOG_BYTES = 51_200
OWNER_REPO_RE = re.compile(r"^([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)$")
ISSUE_RE = re.compile(r"^([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)#([0-9]+)$")
Runner = Callable[..., subprocess.CompletedProcess[bytes]]


@dataclass(frozen=True)
class GitHubIssueContext:
    owner: str
    repo: str
    issue_number: str
    issue_ref: str
    body: str
    stderr: str
    return_code: int


@dataclass(frozen=True)
class GitHubCIContext:
    owner: str
    repo: str
    run_id: str
    metadata: str
    log: str
    metadata_stderr: str
    log_stderr: str
    metadata_return_code: int
    log_return_code: int
    log_truncated: bool
    original_log_bytes: int
    included_log_bytes: int


@dataclass(frozen=True)
class GitHubContext:
    issue: GitHubIssueContext | None = None
    ci: GitHubCIContext | None = None

    @property
    def included(self) -> bool:
        return self.issue is not None or self.ci is not None


def parse_issue_ref(value: str) -> tuple[str, str, str]:
    match = ISSUE_RE.fullmatch(value)
    if not match or match.group(1) in {".", ".."} or match.group(2) in {".", ".."}:
        raise ValueError("--github-issue must be exactly owner/repo#number")
    return match.group(1), match.group(2), match.group(3)


def parse_repo(value: str) -> tuple[str, str]:
    match = OWNER_REPO_RE.fullmatch(value)
    if not match or match.group(1) in {".", ".."} or match.group(2) in {".", ".."}:
        raise ValueError("--github-repo must be exactly owner/repo")
    return match.group(1), match.group(2)


def parse_run_id(value: str) -> str:
    if not value.isdecimal():
        raise ValueError("--github-ci-run must be numeric")
    return value


def validate_github_flags(issue_ref: str | None, repo_ref: str | None, ci_run: str | None) -> None:
    if issue_ref:
        parse_issue_ref(issue_ref)
    if repo_ref:
        parse_repo(repo_ref)
    if ci_run:
        parse_run_id(ci_run)
        if not repo_ref:
            raise ValueError("--github-repo is required when --github-ci-run is provided")


def fetch_github_context(
    run_dir: Path,
    run_id: str,
    issue_ref: str | None = None,
    repo_ref: str | None = None,
    ci_run: str | None = None,
    runner: Runner = subprocess.run,
) -> tuple[GitHubContext, dict[str, object] | None]:
    validate_github_flags(issue_ref, repo_ref, ci_run)
    issue = _fetch_issue(issue_ref, runner) if issue_ref else None
    ci = _fetch_ci(repo_ref, ci_run, runner) if repo_ref and ci_run else None
    context = GitHubContext(issue, ci)
    if not context.included:
        return context, None
    artifacts = _write_artifacts(run_dir, run_id, context)
    return context, artifacts


def _fetch_issue(issue_ref: str, runner: Runner) -> GitHubIssueContext:
    owner, repo, number = parse_issue_ref(issue_ref)
    result = _run(["gh", "issue", "view", issue_ref], runner, "GitHub issue fetch failed")
    return GitHubIssueContext(owner, repo, number, issue_ref, _text(result.stdout), _text(result.stderr), result.returncode)


def _fetch_ci(repo_ref: str, run_id: str, runner: Runner) -> GitHubCIContext:
    owner, repo = parse_repo(repo_ref)
    run_id = parse_run_id(run_id)
    metadata = _run(["gh", "run", "view", run_id, "--repo", repo_ref], runner, "GitHub CI metadata fetch failed")
    log = _run(["gh", "run", "view", run_id, "--repo", repo_ref, "--log"], runner, "GitHub CI log fetch failed")
    included, truncated, original = _tail_bytes(_bytes(log.stdout))
    return GitHubCIContext(
        owner,
        repo,
        run_id,
        _text(metadata.stdout),
        included.decode("utf-8", errors="replace"),
        _text(metadata.stderr),
        _text(log.stderr),
        metadata.returncode,
        log.returncode,
        truncated,
        original,
        len(included),
    )


def _run(command: list[str], runner: Runner, label: str) -> subprocess.CompletedProcess[bytes]:
    try:
        result = runner(command, capture_output=True, check=False)
    except OSError as exc:
        raise ValueError(f"{label}: gh unavailable: {exc}") from exc
    if result.returncode != 0:
        stderr = _text(result.stderr).strip() or "no stderr"
        raise ValueError(f"{label}: gh returned {result.returncode}: {stderr}")
    return result


def _write_artifacts(run_dir: Path, run_id: str, context: GitHubContext) -> dict[str, object]:
    fetched_at = datetime.now(timezone.utc).isoformat()
    artifacts: list[str] = []
    if context.issue:
        issue = context.issue
        (run_dir / "github_issue_context.md").write_text(
            f"""# GitHub Issue Context

## Source

* source_type: github
* read_only: true
* fetched_with: gh
* command_kind: issue_view
* issue: {issue.issue_ref}

## Content

{issue.body}

## Notes

* This context was fetched read-only.
* GitHub is an input source only in v11.
* The loop did not comment, label, edit, close, or otherwise modify the issue.
"""
        )
        (run_dir / "github_issue_context.json").write_text(json.dumps({
            "source_type": "github",
            "read_only": True,
            "fetched_with": "gh",
            "command_kind": "issue_view",
            "owner": issue.owner,
            "repo": issue.repo,
            "issue_number": issue.issue_number,
            "issue_ref": issue.issue_ref,
            "return_code": issue.return_code,
            "stderr": issue.stderr,
            "fetched_at": fetched_at,
            "included_in_prompt": True,
            "no_github_writes": True,
        }, indent=2) + "\n")
        artifacts += ["github_issue_context.md", "github_issue_context.json"]
    if context.ci:
        ci = context.ci
        (run_dir / "github_ci_context.log").write_text(ci.log)
        (run_dir / "github_ci_context.json").write_text(json.dumps({
            "source_type": "github",
            "read_only": True,
            "fetched_with": "gh",
            "command_kind": "run_view_and_log",
            "owner": ci.owner,
            "repo": ci.repo,
            "run_id": ci.run_id,
            "metadata_return_code": ci.metadata_return_code,
            "log_return_code": ci.log_return_code,
            "metadata_stderr": ci.metadata_stderr,
            "log_stderr": ci.log_stderr,
            "fetched_at": fetched_at,
            "included_in_prompt": True,
            "log_truncated": ci.log_truncated,
            "truncation_strategy": "tail",
            "max_log_bytes": MAX_CI_LOG_BYTES,
            "original_log_bytes": ci.original_log_bytes,
            "included_log_bytes": ci.included_log_bytes,
            "no_github_writes": True,
        }, indent=2) + "\n")
        artifacts += ["github_ci_context.log", "github_ci_context.json"]
    summary = {
        "included": True,
        "issue_context_included": context.issue is not None,
        "ci_context_included": context.ci is not None,
        "issue_ref": context.issue.issue_ref if context.issue else None,
        "repo": f"{context.ci.owner}/{context.ci.repo}" if context.ci else None,
        "ci_run_id": context.ci.run_id if context.ci else None,
        "read_only": True,
        "fetched_with": "gh",
        "no_github_writes": True,
        "artifacts": artifacts,
    }
    (run_dir / "github_context_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary | {"summary_path": f".agent/runs/{run_id}/github_context_summary.json"}


def _tail_bytes(value: bytes) -> tuple[bytes, bool, int]:
    original = len(value)
    if original <= MAX_CI_LOG_BYTES:
        return value, False, original
    return value[-MAX_CI_LOG_BYTES:], True, original


def _bytes(value: bytes | str | None) -> bytes:
    if value is None:
        return b""
    return value.encode("utf-8") if isinstance(value, str) else value


def _text(value: bytes | str | None) -> str:
    if value is None:
        return ""
    return value if isinstance(value, str) else value.decode("utf-8", errors="replace")
