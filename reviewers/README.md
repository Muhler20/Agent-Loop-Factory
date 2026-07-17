# Reviewer Rubrics

Reviewer rubrics are durable, human-authored Markdown guidance files for the optional advisory reviewer.

They guide `--advisory-reviewer codex` only. They are advisory receipts, not gates, verifier rules, memory files, or human approval. A rubric does not affect `verifier_result.json` and does not replace human review.

Rubrics must be explicitly selected by a human:

```bash
--reviewer-rubric reviewers/safety-reviewer.md
--reviewer-rubric reviewers/test-reviewer.md
--reviewer-rubric reviewers/scope-reviewer.md
--reviewer-rubric reviewers/handoff-reviewer.md
```

The loop does not auto-select, rank, retrieve, or apply rubrics.

Use `safety-reviewer.md` for auth, billing, payments, migrations, infra, deployment, Docker, CI config, `.github`, secrets, unsafe GitHub writes, or other risky side effects.

Use `test-reviewer.md` when test adequacy is the main risk: missing tests, weakened tests, skipped tests, suspicious gates, or coverage gaps.

Use `scope-reviewer.md` when the task has tight allowed/forbidden files, doc-only or code-only boundaries, or risk of unrelated cleanup.

Use `handoff-reviewer.md` when PR handoff quality matters: title/body accuracy, risk notes, test notes, changed-file summaries, and validation warnings.
