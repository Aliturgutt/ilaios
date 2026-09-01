# ILAIOS Knowledge / RAG — Bounded Implementation Record

**Workstream:** `RAG_KNOWLEDGE`
**Canonical capability identity:** `ilaios.capability.knowledge`
**Implementation root:** `services/knowledge_rag.py`
**Truth rule:** code + tests + exact-head CI determine current maturity

## Scope

This implementation extends the existing ILAIOS Knowledge capability in place. It does not introduce a second Core, routing authority, tenant authority, evidence authority, or factory-local private RAG stack.

The bounded implementation covers:

```text
Source
  -> immutable SourceVersion
  -> deterministic KnowledgeUnit chunks
  -> RAG quarantine
  -> embedding adapter
  -> index adapter
  -> authorization eligibility set
  -> vector scoring inside that set only
  -> deterministic reranking
  -> RetrievalResult
  -> source/version/unit citations
  -> AuthorizedContext
  -> downstream governed worker/factory
```

Retrieved knowledge remains untrusted data. `AuthorizedContext.safety_boundary` is `UNTRUSTED_KNOWLEDGE_DATA`; retrieved text never becomes control-plane authority.

## RAG.01 — Source / Data Contract

Implemented bounded contracts:

- `KnowledgeSource`
- `SourceVersion`
- `KnowledgeUnit`
- immutable content SHA-256 lineage
- tenant/project/classification/purpose/residency metadata

## RAG.02 — Tenant Isolation & Authorization

Implemented:

- `PrincipalScope`
- exact tenant/project matching
- classification allow-listing
- purpose authorization
- residency authorization
- optional explicit source allow-list
- fail-closed cross-scope mutation

Authorization is evaluated before any candidate is supplied to vector scoring.

## RAG.03 — Ingestion & Provenance

Implemented:

- deterministic source registration
- deterministic chunking
- exact source-version content hash
- exact unit content hash
- locator-preserving citations
- source/version/unit lineage in retrieval evidence

The RAG plane does not replace Research/Data verification or the canonical evidence authority.

## RAG.04 — Knowledge Unit / Index Lifecycle

Implemented:

- deterministic chunk IDs
- source version increment
- old-version de-index on update
- revoke de-index
- delete de-index
- deleted unit content clearing
- active-version-only retrieval

## RAG.05 — Embedding / Index Provider Adapter

Provider-neutral protocols:

- `EmbeddingProvider`
- `VectorIndex`

Bounded verification adapters:

- `DeterministicHashEmbeddingProvider`
- `InMemoryVectorIndex`

These are reference/test implementations, not production embedding quality, persistence, or scale claims.

## RAG.06 — Retrieval & Reranking

Implemented:

- bounded candidate scan
- vector similarity scoring
- deterministic lexical overlap reranking
- stable tie-breaking
- top-k and context-size budgets
- fail-closed rejection if the index returns a candidate outside the pre-authorized set

## RAG.07 — Authorization-Aware Query Path

The canonical bounded runtime path is `KnowledgeRAG.retrieve()`.

The service computes `eligible_unit_ids` before `VectorIndex.search()`. The vector index receives only the already-authorized set. Dedicated adversarial tests record the exact set supplied to scoring and verify other-tenant IDs never enter it.

This preserves ADR-0008: authorization is not a post-retrieval filter.

## RAG.08 — AuthorizedContext Integration

Implemented:

- exact RetrievalRequest/Result ID binding
- query SHA validation
- retrieval evidence-fingerprint validation
- result top-k/candidate/context-budget validation
- tenant/project/purpose binding
- citation provenance revalidation against canonical source/version/unit state
- current authorization revalidation before context assembly
- revocation-after-retrieval invalidates context assembly
- explicit untrusted-data safety boundary

## RAG.09 — Privacy / DLP / Injection Hardening

Implemented RAG-specific defense in depth:

- tenant/project isolation
- classification/purpose/residency checks
- prompt-injection quarantine for high-confidence instruction-override patterns
- high-confidence provider credential-pattern quarantine
- quarantined units never enter the active index

This does not replace `services/privacy.py`, Security Factory secret scanning, or external compliance controls.

## RAG.10 — Evaluation & Leakage Red-Team

Implemented:

- expected-source evaluation cases
- forbidden-source leakage checks
- deterministic evaluation fingerprint
- cross-tenant leakage regression tests
- stale/revoked/deleted source tests
- injection/credential quarantine tests
- malicious-index candidate-smuggling test
- query/evidence/citation tamper tests
- post-retrieval revocation test
- cross-scope snapshot-forgery test

## RAG.11 — Full Platform Integration / CI

Implementation lives under `services/` and tests under `tests/`, so existing Required CI / Platform CI covers:

- diff hygiene
- secret scanning
- CI supply-chain hardening
- DB migration safety
- pytest
- Ruff
- strict mypy / pre-commit typing path

Capability-registry binding remains on the single `ilaios.capability.knowledge` identity. No separate RAG factory or parallel capability ID is permitted.

## RAG.12 — Recovery / Observability / FinOps

Implemented bounded primitives:

- tenant/project-scoped `RAGSnapshot`
- deterministic snapshot fingerprint
- embedding-provider identity validation on restore
- source/version/unit scope and lineage validation
- unit content-hash validation
- active-state validation before index rebuild
- retrieval/ingestion/quarantine/active-unit metrics
- max top-k
- max candidate scan
- max context characters

These are bounded controls, not production SLO, production backup, or cryptographic-signature claims.

## RAG.13 — Final Lineage Red-Team

Bounded lineage:

```text
PrincipalScope
  -> RetrievalRequest
  -> tenant/project/purpose/classification/residency authorization
  -> eligible unit IDs
  -> VectorIndex.search(eligible IDs only)
  -> reject out-of-set candidate
  -> rerank
  -> RetrievalResult
  -> evidence fingerprint + citation lineage validation
  -> current authorization/revocation revalidation
  -> AuthorizedContext
```

Required invariants covered by tests:

- other-tenant source cannot enter scoring or results;
- unauthorized purpose fails closed;
- restricted classification is excluded;
- revoked source is no longer retrievable;
- an already-retrieved source cannot form context after revocation;
- deleted source content is cleared and not indexed;
- stale source versions do not remain active;
- quarantined injection/credential units do not enter retrieval;
- malicious index/provider output cannot smuggle unauthorized IDs;
- retrieval-result tampering is rejected;
- snapshot provider/scope/lineage drift fails closed;
- evaluation detects forbidden-source leakage.

RAG.13 can be marked VERIFIED only after exact-head Required CI passes for the implementation revision.

## RAG.14 — Production Promotion Decision

**Decision: NO-GO for `DEPLOYED / PRODUCTION`.**

Production promotion remains blocked until separate evidence proves, for the exact deployment scope:

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

A deterministic local adapter passing CI can justify bounded `VERIFIED`; it cannot justify `DEPLOYED / PRODUCTION`.

## Promotion rule

Before exact-head CI:

```text
RAG.01-RAG.13 = IMPLEMENTED / TESTS PRESENT / VERIFICATION PENDING
RAG.14 = NO-GO PRODUCTION
```

After exact-head Required CI PASS and merge, the bounded scope may be recorded as VERIFIED. Production remains blocked until RAG.14 runtime evidence exists.
