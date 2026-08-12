# ILAIOS Repository Governance

## Purpose

This document defines repository change discipline. It does not replace the canonical ILAIOS architecture, implementation specification, milestone manifest or release evidence.

## Authority hierarchy

When sources disagree, use the following order for decisions within their respective scope:

1. governed canonical architecture;
2. canonical implementation-order specification;
3. machine-readable milestone/dependency definitions;
4. current repository code, tests, CI/runtime and deployment evidence for implementation state;
5. bounded execution package;
6. human-readable status and planning documents.

A lower authority cannot silently override a higher authority.

## Implementation-state rule

Capability maturity is evidence-based. Use the lifecycle:

`PLANNED -> SPECIFIED -> IMPLEMENTED -> VERIFIED -> PRODUCTION`

A capability is not promoted because a document says it is complete. Missing or contradictory evidence means use the lower proven state.

## Change classes

### Class A — documentation/governance only

Examples: status synchronization, audit reports, non-normative planning and security guidance.

Requirements:
- no product-runtime semantic change;
- branch/PR preferred when multiple files change;
- verify links, paths and factual claims against repository evidence.

### Class B — bounded implementation

Examples: code, tests, service behavior, schemas, workflows with no production promotion.

Requirements:
- explicit scope and allowed paths;
- dependency evidence;
- tests/static checks appropriate to the component;
- no unrelated changes;
- atomic commit/PR;
- rollback plan where material.

### Class C — production/release/security-sensitive

Examples: AWS resource mutation, production promotion, DNS, secrets, signing, billing, destructive migrations or identity changes.

Requirements:
- explicit human authorization;
- validated prerequisites;
- least privilege;
- independent verification appropriate to risk;
- rollback/recovery evidence;
- no autonomous promotion.

## Branch and PR policy

- Do not use force-push for routine development or recovery.
- Prefer one bounded purpose per branch/PR.
- Do not merge code changes with failing required checks.
- Do not hide failures by disabling tests or checks.
- Stale PRs that are proven superseded should be closed with the superseding PR/commit recorded.
- Canonical authority changes require a dedicated governed change, never incidental edits in an unrelated PR.

## Product-surface boundaries

Website and Desktop may be developed as separate bounded workstreams. A repository-governance package must not alter either implementation unless its declared scope explicitly includes that surface.

Post-v1 planning also must not assume Mobile, billing, RAG, factories or any other architecture target is already implemented merely because the architecture defines it.

## Release policy

`VERIFIED` does not imply `PRODUCTION`.

Production state is established only by the governed release path and deployment evidence. Repository automation may prepare release inputs, run checks and collect evidence, but production promotion requires the declared approval model.

Formal version, tag and GitHub Release semantics are governed by `docs/governance/RELEASE_VERSION_POLICY.md`. That policy is additive to this repository governance and cannot be used to bypass Class C approval requirements.

## Automation policy

Automation must be deterministic-first and fail closed. It may continue independent ready work after a blocked package only when dependencies prove that the work is independent.

Automation must never:
- invent requirements to avoid a stop;
- bypass dependency or approval gates;
- redefine architecture;
- create/rotate secrets without authorization;
- perform paid actions without authorization;
- modify production merely because tests pass;
- fabricate evidence.

## Post-v1 planning

`docs/governance/POST_V1_ROADMAP.md` and related audit files are proposals until a governed post-v1 execution graph is formally adopted. They are intentionally separated from current canonical authority files so planning cannot accidentally change the released v1 governance contract.
