# Handoff Reviewer

* status: active
* category: handoff
* advisory_only: true

## Review Focus

Review PR title/body accuracy, risk notes, test notes, changed-file summaries, PR handoff validation warnings, and artifacts a human should inspect before acting.

## Questions To Ask

Would the PR body help a human review the real change?
Are risks, tests, and warnings visible?
Do handoff commands stay manual and advisory?

## Red Flags

Misleading title, missing test notes, missing risk notes, missing changed-file summary, ignored handoff warnings, or commands presented as already executed.

## Evidence To Cite

`pr_title.txt`, `pr_body.md`, `pr_handoff.md`, `pr_handoff_check.md/json`, review recommendation, gates, and verifier result.

## Suggested Human Actions

Edit the handoff before any commit, push, or PR creation if the artifacts understate risk or overstate certainty.

## Non-Authority Reminder

* This rubric guides advisory review only.
* It does not override gates.
* It does not override verifier_result.json.
* It does not override task scope, constraints, memory hygiene, or human approval boundaries.
