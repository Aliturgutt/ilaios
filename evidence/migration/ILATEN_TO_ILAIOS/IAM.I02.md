# IAM.I02 — Standards-Based Identity and Tenant Authorization

## Pre-state

- Baseline HEAD: `ff74d5b98834c456c11728eaed9007ccffcbbcd9`
- Worktree: clean and equal to `origin/master`
- Dependencies: `AUDIT.C02` PASS
- Package state: READY

## Bounded implementation

`services/identity.py` defines a replaceable OIDC/OAuth token-verification
boundary, validated issuer/audience/lifetime/tenant claims, separate human and
service principals, deterministic tenant-scoped RBAC/ABAC, default denial,
privileged MFA checks, exact independent approval for high-risk work,
short-lived tenant-bound sessions, revocation, and independently verified,
time-bounded recovery and break-glass records.

Cryptographic token verification remains the responsibility of the replaceable
OIDC adapter. The implementation does not provide an identity provider, issue
real credentials, or claim deployed federation. No LLM participates in an
authorization decision.

## Exact proof boundary

The canonical identity rows generally combine this package with deployed IdP,
device, audit, evidence, credential, monitoring, and operational requirements.
They therefore receive row-specific `PARTIAL` evidence unless their complete
assertion is independently proven; this package does not promote a composite
row merely because a related control exists.

## Validation

Status: `PASS`

- `python -m pytest -q tests/test_identity_access.py tests/test_migration_audit.py`: 12 passed
- `ruff check .`: PASS
- `python -m pytest -q`: 903 passed
- `mypy --strict src tests`: PASS, 151 source files
- `pre-commit run --all-files`: PASS
- `git diff --check`: PASS

The regenerated matrix contains 8,346 requirements: 0 `IMPLEMENTED`, 1,220
`PARTIAL`, 1,967 `MIGRATED`, and 5,159 `MISSING_IMPLEMENTATION`. IAM.I02
provides row-specific evidence for 137 requirements. No composite requirement
was promoted beyond the proof boundary.
