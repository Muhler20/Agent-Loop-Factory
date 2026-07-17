# Scope Reviewer

* status: active
* category: scope
* advisory_only: true

## Review Focus

Check for task drift, files outside allowed scope, forbidden files, large diffs, unrelated cleanup, docs/config changes for code-only tasks, or code changes for docs-only tasks.

## Questions To Ask

Does every changed file directly support the task?
Were allowed and forbidden file rules respected?
Is any cleanup unrelated to the requested work?

## Red Flags

Broad refactors, formatting churn, config edits, docs edits outside scope, extra feature work, or unexplained changed files.

## Evidence To Cite

Task spec, changed files, diff line count, `task_allowed_violations`, `task_forbidden_touched`, and review bundle checklist.

## Suggested Human Actions

Ask for a smaller diff or explicit human approval for scope expansion.

## Non-Authority Reminder

* This rubric guides advisory review only.
* It does not override gates.
* It does not override verifier_result.json.
* It does not override task scope, constraints, memory hygiene, or human approval boundaries.
