# Safety Reviewer

* status: active
* category: safety
* advisory_only: true

## Review Focus

Check whether the diff touches auth, billing, payments, migrations, infra, deployment, Docker, CI config, `.github`, `human_required_paths`, secrets, credentials, unsafe GitHub writes, or risky side effects.

## Questions To Ask

Did any touched path require explicit human approval?
Did the run preserve no-push, no-PR, no-deploy, and no-GitHub-write boundaries?
Could the change expose credentials or trigger irreversible behavior?

## Red Flags

New credentials, token-like strings, background jobs, deployment hooks, workflow edits, migrations, or changes under human-required paths without clear approval.

## Evidence To Cite

Changed files, verifier `human_required_touched`, reserved artifact warnings, task constraints, Codex prompt limits, and gate output.

## Suggested Human Actions

Block or request rework until a human explicitly approves sensitive paths and confirms no unsafe side effects.

## Non-Authority Reminder

* This rubric guides advisory review only.
* It does not override gates.
* It does not override verifier_result.json.
* It does not override task scope, constraints, memory hygiene, or human approval boundaries.
