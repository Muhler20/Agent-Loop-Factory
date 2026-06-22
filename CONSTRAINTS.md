# Project Constraints

- Keep diffs small and scoped.
- Do not weaken, delete, skip, or bypass tests to make gates pass.
- Do not touch auth, billing, payments, migrations, infra, deployment, Docker, docker-compose, or CI config without human approval.
- Do not push, merge, deploy, publish, open PRs, or create releases.
- Stop and escalate if the task requires secrets, credentials, production systems, or unclear business judgment.
- Prefer deterministic checks over model self-review.
- Every run should leave inspectable artifacts.
- Human review is required before any irreversible action.
