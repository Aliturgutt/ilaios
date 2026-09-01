# AGENT.I07 — Governed Agent Identity, Permission Firewall, and AI Security

## Pre-state

- Baseline HEAD: `5b47f7ca5be10ce5c5578ebf6c7f3d4a2eb3cedd`
- Worktree: clean and equal to `origin/master`
- Dependencies: `GOV.I01`, `IAM.I02`, and `DATA.I04` PASS
- Package state: READY

## Bounded implementation

`services/agent_governance.py` requires complete stable machine manifests with
separate aliases, roles, teams, capabilities, permissions, input/output
classes, dependencies, callers, targets, escalation, independent verifier,
version, and lifecycle status. Its deterministic permission firewall enforces
manifest scope, time-bound ExecutionGrants, injection markers, secret
exclusion, DLP before egress, independent security-scan result, and verifier
evidence. No wildcard or unrestricted agent authority exists.

The bounded injection detector is defense-in-depth, not a claim of complete
prompt-injection prevention. Deployed scanners, DLP providers, incident
responders, and verifier services remain external/reference integrations.

## Validation

Status: `PASS`

- `python -m pytest -q tests/test_agent_governance.py tests/test_migration_audit.py`: 11 passed
- `ruff check .`: PASS
- `python -m pytest -q`: 921 passed
- `mypy --strict src tests`: PASS, 156 source files
- `pre-commit run --all-files`: PASS
- `git diff --check`: PASS

The regenerated matrix contains 8,346 requirements: 0 `IMPLEMENTED`, 2,971
`PARTIAL`, 1,967 `MIGRATED`, and 3,408 `MISSING_IMPLEMENTATION`. AGENT.I07
provides row-specific evidence for 134 requirements without claiming complete
adversarial prevention or deployed verifier services.
