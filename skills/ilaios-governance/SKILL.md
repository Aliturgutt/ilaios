---
name: ilaios-governance
description: Review skills, tools, providers, identities, data flows, and releases against ILAIOS governance boundaries including tenant scope, capabilities, policy, approval, side effects, budget, provenance, evidence, rollback, and fail-closed behavior.
---

# ILAIOS Governance Review

Canonical ID: `ilaios.skill.governance.review.v1`
Methodology contract: `ILAIOS-METHODOLOGY-GOVERNANCE-V1`

## Authority boundary

This skill is advisory review methodology. Deterministic ILAIOS Policy, Approval, authorization/fencing, Tool Gateway, tenant isolation, budget controls, Validation, Audit, Evidence Chain, and release controls remain authoritative. A governance document or reviewer opinion cannot grant execution.

## Review workflow

1. Inventory affected skill/tool/provider identities, data flows, tenant boundaries, external egress, credentials, capabilities, and runtime ownership.
2. Classify operations by read/write, destructive impact, idempotency, reversibility, open-world reach, cost, and risk.
3. Verify least privilege, explicit capability contracts, tenant isolation, authentication source, authorization/fencing, DLP/egress, budget, and approval requirements.
4. Verify supply-chain provenance and whether a new dependency or provider creates hidden lock-in or unsupported authority.
5. Verify evidence expectations for implementation, testing, independent review, deployment, production verification, rollback, and recovery.
6. Trace bypass paths: UI-only gates, direct provider calls, alternate tool paths, stale grants, missing actor/tenant context, self-certification, and failure-open fallbacks.
7. Return evidence-backed findings with severity, affected boundary, remediation, and unresolved blockers. Missing mandatory evidence fails closed.

## Release discipline

Documentation is not implementation; implementation is not testing; CI is not production verification. Release readiness may recommend promotion only to the highest maturity directly supported by exact-head evidence.

See `references/acceptance-criteria.md`.
