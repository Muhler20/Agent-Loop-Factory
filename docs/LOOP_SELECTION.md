# Loop Selection

Use a loop only when the task is repetitive, local, and verifiable.

## Checklist

- The task repeats.
- Automated verification exists.
- The agent can run or reproduce the code.
- The loop has a hard stop.
- A human reviews before merge, deploy, dependency, or security-sensitive changes.

## Good First Loops

- CI failure triage
- Failing test repair
- Lint/typecheck fixes
- Small dependency compatibility checks
- Small issue-to-draft-fix tasks with strong tests

## Bad First Loops

- Architecture rewrites
- Auth/payment/security-sensitive changes
- Production deploys
- Vague product work
- Tasks where done is subjective
