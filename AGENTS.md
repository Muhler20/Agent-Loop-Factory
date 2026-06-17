# Agent Rules

- Prefer small changes.
- Never weaken tests to make gates pass.
- Never touch auth, billing, payments, migrations, infra, deployment config, Dockerfiles, docker-compose files, or CI config without human approval.
- Run gates before claiming success.
- Write concise summaries of changes.
- Do not push, merge, deploy, or open PRs from this repo unless a future version explicitly implements that behavior with human approval.
