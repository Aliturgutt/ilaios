# ILAIOS Post-v1 Roadmap Proposal

Status: **DRAFT / NON-CANONICAL / NOT EXECUTABLE**

This document proposes a dependency order for work after the existing v1 namespace. It does not amend the canonical architecture, implementation specification, milestone manifest, OpenClaw controller or current release state.

## Governing principle

The existing canonical namespace ends at `RELEASE.R03`. Namespace presence and historical evidence do not prove current readiness.

The active `dev/openclaw/execution_plan.yaml` recovery package begins at `PLATFORM.P05`, rejects historical PASS as sufficient for affected current readiness, and records `release_state: NOT_DEPLOYED`. `infra/deployment/ext-e01-prerequisites.yaml` records `deployment_performed: false` and `PREPARED_AWAITING_APPROVALS`.

Accordingly, post-v1 implementation is blocked until the current v1 lifecycle state is reconciled through the existing recovery/evidence rules. This proposal must not be used to bypass that dependency.

Before any future post-v1 package becomes executable it must define:

- exact objective and exit criteria;
- dependencies;
- allowed and forbidden paths;
- validations and tests;
- evidence requirements;
- approvals;
- budget policy where relevant;
- rollback/recovery;
- stop conditions;
- commit/promotion policy.

## Proposed dependency flow

### Stage -1 — Current v1 recovery/revalidation gate

Dependencies: current canonical authorities and active recovery controller.

Deliverables:
- resolve `PLATFORM.P05.RECOVERY.v1` and every downstream affected dependency using accepted current evidence;
- keep historical PASS as provenance but do not use it as a current dependency substitute where the controller forbids that;
- reconcile release/deployment state with `infra/deployment/ext-e01-prerequisites.yaml`;
- require explicit approvals for any external spend or release promotion;
- update human-readable lifecycle projections only after evidence changes.

Exit: current v1 lifecycle state is internally coherent and no human-readable PRODUCTION claim conflicts with active recovery/deployment evidence.

### Stage 0 — Governance baseline

Dependencies: Stage -1.

Deliverables:
- repository truth synchronization;
- security/governance policies;
- stale PR cleanup;
- CI/workflow inventory;
- capability maturity matrix refreshed against the resolved lifecycle state;
- branch-protection, license and release-versioning owner decisions recorded when appropriate.

Exit: repository planning state no longer contradicts current evidence.

### Stage 1 — Capability revalidation

Dependencies: Stage 0.

Revalidate existing implementation before rewriting it:

1. Code Intelligence;
2. Knowledge Graph;
3. Project Manager;
4. Web/Software Factory foundations, excluding Website implementation changes from this governance track;
5. privacy/cryptography service boundaries.

Each capability is promoted only by fresh targeted + integration/regression evidence. Existing code that passes the new gates is preserved.

Exit: capability matrix is evidence-backed enough to choose the first net-new product package.

### Stage 2 — Post-v1 product selection gate

Dependencies: Stage 1.

Owner/product decision required. Candidate workstreams are ranked by architectural fit and repository gap, not by novelty.

Candidate areas identified by the repository audit include Mobile enablement, commercial account/billing/entitlement, RAG/embedding/vector retrieval, and further promotion of existing factory capabilities. Candidate presence in this document does not authorize implementation.

Only one primary workstream should become active unless independence is explicitly proven.

### Stage 3 — Selected workstream specification

Dependencies: Stage 2 selection.

For the selected workstream only:

1. freeze authority boundaries and acceptance criteria;
2. define exact dependency graph;
3. define allowed/forbidden paths;
4. define validation and negative-test gates;
5. define evidence and rollback/recovery requirements;
6. define external approvals, spend and promotion boundaries;
7. adopt the package through the governed canonical process where required.

Website and Desktop implementation remain excluded from this repository-governance automation unless separately authorized in their own workstreams.

### Stage 4 — Bounded implementation and enterprise hardening

Dependencies: Stage 3 package formally adopted and READY.

Cross-cutting gates include, as applicable:
- backup/restore evidence where stateful data is introduced;
- recovery drills;
- tenant isolation regression;
- security negative tests;
- SBOM/build provenance;
- observability/SLOs;
- cost limits;
- runbooks;
- independent release verification.

No production promotion follows automatically from implementation or verification.

### Stage 5 — Further capability promotion

Only after the selected Stage 4 capability has accepted evidence, select the next candidate from the refreshed capability matrix. Do not open speculative implementation tracks merely because they appear in architecture or planning prose.

## Recommended immediate order

1. merge the repository truth correction after diff/CI review;
2. resolve the active v1 recovery/revalidation gate without bypassing dependencies;
3. reconcile deployment/release evidence and required human approvals;
4. refresh capability maturity classification;
5. complete owner-level governance decisions that are safe and explicitly authorized;
6. only then select and formalize the first post-v1 workstream.

## Definition of done for this roadmap

This proposal is complete when it gives a safe dependency order. It is **not executable authority** and does not become one until current v1 recovery is resolved and the selected post-v1 graph is explicitly adopted through the governed process.
