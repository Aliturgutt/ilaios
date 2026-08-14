# ILAIOS Knowledge / RAG — Bounded Implementation Record

**Workstream:** `RAG_KNOWLEDGE`  
**Canonical capability identity:** `ilaios.capability.knowledge`  
**Implementation root:** `services/knowledge_rag.py`  
**Truth rule:** code + tests + exact-head CI determine current maturity

## Scope

This implementation extends the existing ILAIOS Knowledge capability in place. It does not introduce a second Core, routing authority, tenant authority, evidence authority, or factory-local private RAG stack.

The bounded implementation covers the canonical flow:

```text
Source
  -> immutable SourceVersion
  -> deterministic KnowledgeUnit chunks
  -> RAG-specific quarantine
  -> embedding adapter
  -> index adapter
  -> authorization eligibility set
  -> vector scoring only inside that authorized set
  -> deterministic lexical reranking
  -> RetrievalResult
  -> source/version/unit citations
  -> AuthorizedContext
  -> downstream governed worker/factory
```

Retrieved knowledge remains untrusted data. `AuthorizedContext.safety_boundary` is explicitly `UNTRUSTED_KNOWLEDGE_DATA`; retrieved text does not become control-plane authority.

## Milestone mapping

### RAG.01 — Source / Data Contract

Implemented bounded contracts:

- `KnowledgeSource`
- `SourceVersion`
- `KnowledgeUnit`
- immutable content SHA-256 lineage
- tenant/project/classification/purpose/residency metadata

### RAG.02 — Tenant Isolation & Authorization Model

Implemented:

- `PrincipalScope`
- exact tenant/project matching
- classification allow-listing
- purpose authorization
- residency authorization
- optional explicit source allow-list
- fail-closed cross-scope mutation

Authorization is evaluated before any candidate is supplied to vector scoring.

### RAG.03 — Ingestion & Provenance

Implemented:

- deterministic source registration
- deterministic chunking
- exact source-version content hash
- exact unit content hash
- locator-preserving citations
- source/version/unit lineage in retrieval evidence

The RAG plane does not replace the Research/Data Factory verification or canonical evidence authority.

### RAG.04 — Knowledge Unit / Chunk / Index Lifecycle

Implemented:

- deterministic chunk IDs
- source version increment
- old-version de-index on update
- revoke de-index
- delete de-index
- deleted unit content clearing
- active-version-only retrieval

### RAG.05 — Embedding / Index Provider Adapter

Implemented provider-neutral protocols:

- `EmbeddingProvider`
- `VectorIndex`

The repository includes deterministic local verification adapters:

- `DeterministicHashEmbeddingProvider`
- `InMemoryVectorIndex`

These adapters are test/reference implementations. They are not claims of production embedding quality, production persistence, or production-scale vector infrastructure.

### RAG.06 — Retrieval & Reranking

Implemented:

- bounded candidate scan
- vector similarity scoring
- deterministic lexical overlap reranking
- stable tie-breaking
- top-k and context-size budgets

### RAG.07 — Authorization-Aware Query Path

The canonical runtime path is `KnowledgeRAG.retrieve()`.

The service computes an authorized `eligible_unit_ids` set before calling `VectorIndex.search()`. The vector index receives only this already-authorized candidate set.

This preserves ADR-0008 semantics: authorization is not a post-retrieval filter.

### RAG.08 — AuthorizedContext Integration

Implemented:

- exact RetrievalRequest/Result binding
- tenant/project/purpose binding
- query SHA binding
- retrieval evidence binding
- citation-preserving units
- explicit untrusted-data safety boundary

`KnowledgeRAG.build_authorized_context()` cannot bind a result from a different retrieval ID.

### RAG.09 — Privacy / DLP / Injection Hardening

Implemented RAG-specific defense in depth:

- tenant/project isolation
- classification/purpose/residency checks
- prompt-injection quarantine for high-confidence instruction-override patterns
- high-confidence provider credential-pattern quarantine
- quarantined units never enter the active index

This guard is deliberately bounded. It does not replace `services/privacy.py`, Security Factory secret scanning, or external compliance controls.

### RAG.10 — Evaluation & Leakage Red-Team

Implemented:

- expected-source evaluation cases
- forbidden-source leakage checks
- deterministic evaluation evidence hash
- cross-tenant leakage regression tests
- stale/revoked/deleted source tests
- injection/credential quarantine tests

### RAG.11 — Full Platform Integration / CI

The implementation is placed under `services/` and tests under `tests/`, so the existing Platform CI / Required CI path covers:

- pytest
- Ruff
- strict mypy/pre-commit typing path
- diff hygiene

Capability-registry binding must remain on the single `ilaios.capability.knowledge` identity.

No separate RAG factory or parallel capability identity is permitted.

### RAG.12 — Recovery / Observability / FinOps

Implemented bounded primitives:

- tenant/project-scoped `RAGSnapshot`
- deterministic snapshot evidence SHA-256
- content-hash validation on restore
- embedding-provider identity validation on restore
- active-index rebuild
- retrieval/ingestion/quarantine/active-unit metrics
- max top-k
- max candidate scan
- max context characters

These are bounded operational controls, not production SLO or production backup claims.

### RAG.13 — Final RAG Lineage Red-Team

Required lineage for the bounded implementation:

```text
PrincipalScope
    -> RetrievalRequest
    -> tenant/project/purpose/classification/residency authorization
    -> eligible unit IDs
    -> VectorIndex.search(eligible IDs only)
    -> rerank
    -> RetrievalResult
    -> Citation(source/version/unit hashes)
    -> AuthorizedContext
    -> evidence SHA
```

Red-team invariants covered by tests:

- other-tenant source does not enter results;
- unauthorized purpose fails closed;
- restricted classification is excluded;
- revoked source is no longer retrievable;
- deleted source content is cleared and not indexed;
- stale source versions do not remain active;
- quarantined injection/credential units do not enter retrieval;
- snapshot/provider drift fails closed;
- evaluation detects forbidden-source leakage;
- retrieval/context lineage is hash-bound.

RAG.13 can be marked VERIFIED only after exact-head required CI passes for the implementation revision.

## RAG.14 — Production Promotion Decision

**Decision for this bounded implementation: NO-GO for `DEPLOYED / PRODUCTION`.**

The repository implementation is intentionally insufficient for a production claim until separate evidence proves, for the exact deployment scope:

1. approved production embedding provider/model revision and integrity;
2. approved durable vector/index persistence implementation;
3. production tenant-isolation exercise;
4. production authorization-policy integration;
5. production DLP/secret/injection controls and leakage red-team;
6. production backup/restore and deletion/revocation reconciliation;
7. observability/SLO/alert evidence;
8. provider/routing/FinOps integration where external providers are used;
9. exact release artifact and deployment evidence;
10. rollback/recovery evidence.

A local deterministic adapter passing CI means the bounded capability may become `VERIFIED`; it does not mean `DEPLOYED / PRODUCTION`.

## Promotion rule

Before exact-head CI:

```text
RAG.01-RAG.13 = IMPLEMENTED / TESTS PRESENT / VERIFICATION PENDING
RAG.14 = NO-GO PRODUCTION
```

After exact-head Required CI PASS and merge, the bounded scope may be recorded as VERIFIED. Production remains blocked until RAG.14 external/runtime evidence exists.
