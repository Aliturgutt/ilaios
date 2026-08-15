# RAG.14 — Production Readiness Boundary

## Status

`REPOSITORY_AND_CONFIGURATION_READY / PRODUCTION_BLOCKED_PENDING_EXTERNAL_RUNTIME_EVIDENCE`

This document records the repository-side RAG.14 readiness primitives. It does **not** promote Knowledge/RAG to `DEPLOYED / PRODUCTION` and does not supersede canonical architecture, security, deployment, observability, FinOps, or governance authorities.

## Verified repository-side readiness primitives

- `SQLiteVectorIndex` provides durable SQLite-backed vector persistence.
- Search accepts and scores only the already-authorized candidate set supplied by canonical `KnowledgeRAG`.
- Persisted vectors carry SHA-256 integrity binding and dimension validation.
- SQLite durability is compatible with the existing `RuntimeBackupManager` backup/restore path.
- Delete/revoke index reconciliation remains exact-ID and survives restart.
- The Knowledge runtime is bound to Control Plane server-side tenant/project/policy configuration and remains disabled unless configuration is complete.
- The pinned production embedding mode is `multilingual_e5_small_qint8_v1`; production fails closed for non-production embedding modes.
- The production embedding provider is artifact- and package-pinned and performs startup integrity checks.
- Target-container certification exists for the pinned provider candidate, while real AWS/Fargate runtime compatibility remains a canary evidence requirement.
- The canonical R01/Fargate task envelope is prepared at 256 CPU units and 1024 MiB memory.
- When the pinned production provider is enabled in the staged AWS configuration, readiness requires a live six-case semantic/SLO startup self-test that checks dimensions, 6/6 Top-1 retrieval, query P95 latency and peak RSS and emits structured evidence.
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

Repository implementation of a provider, index, runtime envelope or evidence gate does not by itself satisfy the corresponding production evidence item. The evidence must be bound to the exact governed release/deployment scope required by the gate.

## Current evidence boundary

Repository tests and exact-head CI now prove that the production-readiness contracts, pinned provider configuration, durable index primitives, startup self-test gate and resource-envelope configuration are deterministic and fail closed within their verified scope.

Repository evidence still cannot prove that the exact release image has successfully run on AWS/Fargate, that live production-strength tenant/security exercises passed, that a production SLO/alert window was observed, that actual deployment cost was measured, or that rollback/recovery succeeded on the deployed release.

Therefore the allowed current claim is:

```text
RAG.14 repository/configuration production-readiness controls = VERIFIED
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
non-production embedding mode allowed in production?  NO
required live provider self-test may be skipped by the staged production config? NO
missing production evidence may yield READY?           NO
complete evidence may auto-deploy?                     NO
local gate may set production_approved=true?           NO
repository CI may be called production runtime proof?  NO
```
