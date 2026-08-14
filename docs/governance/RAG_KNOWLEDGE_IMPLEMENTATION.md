# RAG / Knowledge — Authorization-Aware Retrieval Foundation

## Status

This document records **current implementation scope**, not target-architecture completion or production readiness.

The canonical rationale remains `docs/adr/ADR-0008-AUTHORIZATION-AWARE-RAG.md`. This implementation adds a bounded first-party retrieval foundation under the existing shared Knowledge plane. It does not create a second Core, router, policy engine, Knowledge Graph, provider selector, or factory.

## Implemented in this slice

- tenant- and project-scoped knowledge chunks;
- principal and declared-purpose authorization before context return;
- classification and residency filtering before context return;
- source revocation reconciliation;
- exact authorization-epoch matching so stale authorization cannot be reused;
- retention-validity enforcement;
- immutable SHA-256 content identity and required provenance metadata;
- deterministic bounded lexical retrieval with a hard maximum result count;
- deterministic retrieval evidence bound to tenant, project, principal, purpose, query digest, authorization epoch, result IDs, result content digests, and provenance;
- ILAIOS-native Knowledge/RAG skill manifests;
- binding of those manifests to the existing canonical `services.runtime.routing.SkillRegistry`;
- adversarial tests for cross-tenant/project access, principal/purpose mismatch, classification/residency mismatch, revocation, stale authorization, invalid retention, unbounded result requests, skill tampering, and authority expansion.

## Security boundary

Authorization is evaluated before a chunk can become returned context. A relevance score can never override tenant, project, principal, purpose, classification, residency, source-revocation, authorization-epoch, retention, integrity, or provenance requirements.

Unauthorized records are excluded without exposing their content or identity to the requester. A content-integrity mismatch fails the retrieval operation closed because the local evidence base can no longer be trusted.

The registration API is an internal bounded foundation. It is not a public ingestion endpoint and does not itself prove that upstream identity, DLP, classification, residency, retention, source authorization, or deletion workflows are complete. Production ingestion must obtain those fields from canonical policy/identity/data authorities rather than from untrusted clients.

## Explicit non-claims

This slice does **not** claim:

- vector database or embedding implementation;
- semantic reranking;
- external model/provider execution;
- production ingestion/connectors;
- OCR or document parsing;
- durable Knowledge/RAG persistence;
- encryption-at-rest deployment evidence;
- completed deletion/retention jobs;
- production DLP integration;
- production identity-provider integration;
- general autonomous research;
- DEPLOYED / PRODUCTION maturity.

Deterministic lexical retrieval is intentionally a bounded validation foundation. Later semantic/vector retrieval must preserve the same pre-return authorization contract and must not weaken it through provider fallback.

## Red-team acceptance gates

The implementation must fail CI if any tested path permits cross-tenant or cross-project context, stale/revoked context reuse, classification/residency bypass, unrestricted result expansion, skill digest tampering, or skill authority escalation.

A passing test suite is implementation/test evidence only. Promotion beyond TESTED/VERIFIED remains governed by the repository maturity model and independent runtime/deployment evidence.
