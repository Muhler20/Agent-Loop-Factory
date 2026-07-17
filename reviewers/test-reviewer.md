# Test Reviewer

* status: active
* category: tests
* advisory_only: true

## Review Focus

Look for missing tests, weakened tests, deleted tests, skip markers, shallow coverage, tests that only prove implementation details, failing gates, or suspiciously narrow checks.

## Questions To Ask

Would a real regression fail a test?
Were assertions removed or weakened?
Do gates cover the changed behavior?

## Red Flags

Deleted test files, added skips, removed assertions, tests that mirror implementation internals, or required gates that failed or did not run.

## Evidence To Cite

Changed test files, diff summary, gate results, verifier `tests_weakened_or_deleted`, and task expectations.

## Suggested Human Actions

Request focused tests or gate fixes when behavior changed without credible coverage.

## Non-Authority Reminder

* This rubric guides advisory review only.
* It does not override gates.
* It does not override verifier_result.json.
* It does not override task scope, constraints, memory hygiene, or human approval boundaries.
