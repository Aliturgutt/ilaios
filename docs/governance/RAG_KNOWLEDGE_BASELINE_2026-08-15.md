# ILAIOS Knowledge / RAG — RAG.00 Baseline & Gap Confirmation

**Snapshot date:** 2026-08-15
**Repository:** `Aliturgutt/ilaios`
**Base branch:** `master`
**Base revision:** `c90c9c696c6cb42653f61262f248c5c1a9c0301b`
**Workstream:** `RAG_KNOWLEDGE`
**Milestone:** `RAG.00 — Baseline & Gap Confirmation`

## Decision

RAG.00 confirms that ILAIOS already has reusable Knowledge/RAG prerequisites, but the repository did not contain a canonical end-to-end RAG implementation at this snapshot.

The implementation therefore MUST extend the existing Knowledge authority in place. It MUST NOT create:

- a second Core;
- a second router;
- a second policy authority;
- a second tenant/identity authority;
- a parallel Knowledge product identity;
- a factory-local private RAG runtime.

`ilaios.capability.knowledge` remains the canonical capability identity.

## Existing reusable implementation

Observed repository evidence before net-new RAG code:

- `src/knowledge_graph` — bounded Knowledge Graph node/edge models including Fact, Evidence and Memory concepts;
- `src/project_manager` — project/workspace context foundation;
- `services/research_data_factory.py` — deterministic source registration, SHA-256 provenance, trusted-source claim verification and Fact/Evidence projection;
- `services/privacy.py` — tenant boundary, residency, purpose/minimization and DLP-oriented controls;
- `services/evidence` and Core evidence foundations — existing audit/provenance authority;
- `services/runtime/routing.py` and `services/ai_governance.py` — existing provider/routing authority;
- `services/observability.py`, `services/operations.py`, `services/operational_drills.py` — existing operations/recovery authority;
- `services/capability_registry.py` — single canonical capability identity registry;
- accepted ADR `docs/adr/ADR-0008-AUTHORIZATION-AWARE-RAG.md` — authorization must occur before retrieved context is returned.

The repository capability matrix at the snapshot still described `RAG / embeddings / vector retrieval` as PLANNED. That is the correct pre-change current reality.

## Verified gaps at RAG.00

The following net-new implementation surfaces were missing or incomplete at the base revision:

1. canonical source/version/knowledge-unit lifecycle;
2. deterministic chunking tied to immutable source-version hashes;
3. embedding provider protocol and vector-index protocol;
4. canonical retrieval/reranking path;
5. authorization-before-scoring enforcement;
6. exact RetrievalRequest → RetrievalResult → AuthorizedContext implementation;
7. citation binding to source/version/unit hashes;
8. update/revoke/delete index reconciliation;
9. RAG-specific prompt-injection and high-confidence credential quarantine as defense in depth;
10. bounded retrieval budgets and RAG metrics;
11. RAG snapshot/restore integrity evidence;
12. leakage-focused retrieval evaluation;
13. capability-registry binding of the RAG implementation root;
14. exact-head Platform CI evidence;
15. production embedding/index/durable-store/runtime evidence.

## Canonical ownership map

| Concern | Canonical owner |
|---|---|
| Knowledge/RAG service boundary | `ilaios.capability.knowledge` |
| Knowledge graph/project context | `src/knowledge_graph`, `src/project_manager` |
| Retrieval implementation | `services/knowledge_rag.py` |
| Identity/tenant truth | existing identity/tenant authority |
| Privacy/DLP authority | `services/privacy.py` and canonical security/data contracts |
| Provider selection/routing | existing routing/governance authority |
| Evidence/audit authority | existing evidence/Core authority |
| Research/Data verification | `services/research_data_factory.py` |
| Factories | consumers of authorized context; not Knowledge authorities |

## RAG.00 exit result

The baseline is sufficiently resolved to start implementation without rewriting existing foundations:

- current implementation surface known;
- reusable primitives identified;
- missing RAG-specific surfaces classified;
- single Knowledge authority preserved;
- exact implementation ownership selected;
- no parallel router, policy plane or Knowledge capability planned.

**RAG.00 result: BASELINE COMPLETE for the exact snapshot above.**

This result does not promote RAG.01+ and does not claim production readiness.
