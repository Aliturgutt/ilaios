# ILAIOS Post-v1 Roadmap Proposal

Status: **DRAFT / NON-CANONICAL**

This document proposes the next dependency order after the completed v1 release chain. It does not amend the canonical architecture, implementation specification, milestone manifest, OpenClaw controller or current release state.

## Governing principle

The existing canonical graph ends at `RELEASE.R03`. Post-v1 work must not invent an implicit `PLATFORM.P21` or `RELEASE.R04`.

Before implementation, every active post-v1 package must define:

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

### Stage 0 — Governance baseline

Dependencies: proven v1 production baseline.

Deliverables:
- repository truth synchronization;
- security/governance policies;
- stale PR cleanup;
- CI/workflow inventory;
- capability maturity matrix;
- branch-protection and release-versioning owner decisions recorded.

Exit: repository planning state no longer contradicts current evidence.

### Stage 1 — Capability revalidation

Dependencies: Stage 0.

Revalidate existing implementation before rewriting it:

1. Code Intelligence;
2. Knowledge Graph;
3. Project Manager;
4. Web/Software Factory foundations;
5. privacy/cryptography service boundaries.

Each capability is promoted only by fresh targeted + integration/regression evidence. Existing code that passes the new gates is preserved.

Exit: capability matrix is evidence-backed enough to choose the first net-new product package.

### Stage 2 — Post-v1 product selection gate

Dependencies: Stage 1.

Owner/product decision required. Candidate workstreams are ranked by architectural fit and repository gap, not by novelty.

Current strongest candidates:

1. Mobile enablement — explicitly post-v1 in the architecture and no Android/iOS implementation path was found in the audit.
2. Commercial account/billing/entitlement layer — no obvious implementation path was found in repository search.
3. RAG/embedding/vector retrieval — architecture target, but no obvious current implementation was found in audit search.
4. Existing factory capability promotion — implementation exists and should be revalidated before expansion.

Only one primary workstream should become active unless independence is explicitly proven.

### Stage 3A — Mobile enablement candidate

Dependencies: Stage 2 selection = Mobile; stable control-plane contracts; identity/tenant boundary verified.

Proposed order:

1. shared Flutter/Dart client architecture audit;
2. Android project enablement without moving backend authority to client;
3. authentication/control-plane connectivity;
4. read-only operational projection;
5. governed interactions using existing backend contracts;
6. Android test/build/signing readiness;
7. Play Store external-account readiness;
8. iOS project enablement;
9. TestFlight/App Store readiness.

Signing, developer-account verification, payments, store declarations and final submissions remain explicit external actions.

### Stage 3B — Commercial SaaS candidate

Dependencies: Stage 2 selection = Commercial; identity/tenant behavior verified.

Proposed order:

1. product-plan/entitlement model;
2. usage/quota metering;
3. rate-limit policy integration;
4. subscription/billing provider adapter;
5. webhook/event reconciliation;
6. invoice/payment-state projection;
7. failure/refund/cancellation rules;
8. security/privacy/FinOps verification;
9. limited rollout before production.

Provider-specific logic must remain replaceable behind ILAIOS-owned contracts.

### Stage 3C — RAG / Knowledge candidate

Dependencies: Stage 2 selection = RAG; privacy/data-classification requirements approved.

Proposed order:

1. data/source contract;
2. tenant isolation model;
3. ingestion and provenance;
4. chunk/index lifecycle;
5. embedding/provider adapter;
6. retrieval/reranking;
7. authorization-aware query path;
8. evaluation and privacy leakage tests;
9. bounded production rollout.

### Stage 4 — Enterprise hardening

Dependencies: first selected post-v1 capability VERIFIED.

Cross-cutting gates:
- backup/restore evidence where stateful data is introduced;
- recovery drills;
- tenant isolation regression;
- security negative tests;
- SBOM/build provenance where applicable;
- observability/SLOs;
- cost limits;
- runbooks;
- independent release verification.

### Stage 5 — Further capability promotion

Only after Stage 4, select the next candidate from the capability matrix. Do not open several speculative implementation tracks merely because they appear in the architecture.

## Recommended immediate order

1. merge governance baseline;
2. owner enables appropriate `master` protection and decides repository metadata/license policy;
3. run Stage 1 revalidation packages;
4. select Mobile vs Commercial as the first net-new post-v1 track;
5. formalize the selected track into a dedicated canonical amendment/package set;
6. then execute automatically within bounded rules.

## Definition of done for this roadmap

This proposal is complete when it gives a safe dependency order. It is **not executable authority** until the selected post-v1 graph is explicitly adopted through the governed canonical process.
