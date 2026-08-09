# ORG.I08 — Governance Records, RACI, Risk, Exception, and Lifecycle

## Pre-state

- Baseline HEAD: `743eae228229e8ffa029441905b2cff526b99b31`
- Worktree: clean and equal to `origin/master`
- Dependencies: `IAM.I02` and `OPS.I05` PASS
- Package state: READY

## Bounded implementation

`services/governance/records.py` enforces unique control accountability,
complete RACI and independent verification, risk ownership/treatment and
separate acceptance authority, independently approved time-bounded exceptions
with compensating controls and review, evidence-backed deprecation and
retirement, and scoped assurance claims that cannot claim certification
without independent assessment.

These are durable reference record contracts, not named organizational
appointments, an audit engagement, legal opinion, assessor finding, or actual
certification. Those remain external dependencies.

## Validation

Status: `PASS`

- `python -m pytest -q tests/test_governance_records.py tests/test_migration_audit.py`: 10 passed
- `ruff check .`: PASS
- `python -m pytest -q`: 924 passed
- `mypy --strict src tests`: PASS, 157 source files
- `pre-commit run --all-files`: PASS
- `git diff --check`: PASS

The regenerated matrix contains 8,346 requirements: 0 `IMPLEMENTED`, 2,992
`PARTIAL`, 1,967 `MIGRATED`, and 3,387 `MISSING_IMPLEMENTATION`. ORG.I08
provides row-specific evidence for 36 requirements without fabricating named
appointments or independent assurance.
