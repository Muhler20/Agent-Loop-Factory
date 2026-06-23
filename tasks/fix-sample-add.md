# Fix Sample Add

## Goal

Fix the failing `sample_math.add` test.

## Scope

`sample_math` implementation only.

## Out of scope

- Tests
- Dependencies
- Config

## Allowed files

- `sample_math.py`

## Forbidden files

- `tests/`
- Dependency files
- Config files

## Gates

```bash
python3 -m unittest discover -s tests
```

## Stop condition

Gates and verifier pass.

## Human approval required if

Any out-of-scope file needs to change.

## Expected artifacts

- `run_report.md`
- `gate_results.json`
- `verifier_result.json`
- `diff_summary.md`
