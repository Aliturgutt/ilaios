# RAG.14 — Production Readiness Boundary

## Status

`IMPLEMENTATION_READY / PRODUCTION_BLOCKED`

This document records the repository-side RAG.14 readiness primitives. It does **not** promote Knowledge/RAG to `DEPLOYED / PRODUCTION` and does not supersede canonical architecture, security, deployment, observability, FinOps, or governance authorities.

## Added repository-side readiness primitives

- `SQLiteVectorIndex` provides durable SQLite-backed vector persistence.
- Search accepts and scores only the already-authorized candidate set supplied by canonical `KnowledgeRAG`.
- Persisted vectors carry SHA-256 integrity binding and dimension validation.
- SQLite durability is compatible with the existing `RuntimeBackupManager` backup/restore path.
- Delete/revoke index reconciliation remains exact-ID and survives restart.
- `RAG14PromotionGate` enumerates the full production evidence set and fails closed while any requirement is absent.
- Even when every evidence item is present, the local gate returns only `READY_FOR_GOVERNED_PROMOTION_REVIEW`; it never grants autonomous production authority.

## Required production evidence

The following evidence classes remain mandatory before a governed production promotion decision:

1. `production_embedding_provider`
2. `durable_vector_index`
3. `production_tenant_isolation`
4. `production_authorization_policy`
5. `production_dlp_and_injection_controls`
6. `production_leakage_redteam`
7. `production_backup_restore`
8. `production_deletion_reconciliation`
9. `production_observability_slo`
10. `production_routing_finops`
11. `exact_release_artifact`
12. `exact_deployment_result`
13. `deployment_health`
14. `rollback_recovery`

## Truth boundary

Repository tests can prove that the production-readiness contracts are deterministic, durable, fail-closed, backup-compatible, and incapable of bypassing authorization ordering. Repository tests cannot prove that a real production embedding provider, real deployed vector service, production tenant boundary, external DLP, production SLO window, deployment health, or rollback exercise has occurred.

Therefore the only allowed claim after this implementation passes CI is:

```text
RAG.14 repository-side production readiness controls = VERIFIED
Knowledge/RAG production promotion = BLOCKED pending external/runtime evidence
```

The following claim remains forbidden without governed production evidence:

```text
Knowledge/RAG = DEPLOYED / PRODUCTION
```

## Red-team invariants

```text
vector index authorizes data?                         NO
vector index may score IDs outside authorized set?   NO
restart may resurrect deleted index rows?             NO
backup restore may skip integrity checks?              NO
missing production evidence may yield READY?           NO
complete evidence may auto-deploy?                     NO
local gate may set production_approved=true?           NO
```
