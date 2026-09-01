# RAG.14 — Canary Preparation

## Current state

`CANARY_CONFIGURATION_READY / CANARY_NOT_APPROVED / PRODUCTION_BLOCKED_PENDING_RUNTIME_EVIDENCE`

This package prepares the existing AWS staged runtime to carry the governed Knowledge/RAG implementation without converting repository evidence into a production claim.

## Repository-side controls

- Knowledge is disabled in AWS staged infrastructure by default.
- Enabling Knowledge requires an explicit server-side principal, tenant, project, classifications, purposes, residencies and embedding mode.
- `verification_hash_v1` remains a bounded verification adapter and is allowed only for non-production evidence exercises.
- The pinned production embedding mode is `multilingual_e5_small_qint8_v1`.
- Production Knowledge configuration fails closed unless the exact pinned production embedding mode is selected.
- The production provider is artifact- and package-pinned and performs startup integrity validation.
- Whenever Terraform enables `multilingual_e5_small_qint8_v1`, `ILAIOS_KNOWLEDGE_STARTUP_SELFTEST_REQUIRED=true` is injected so readiness depends on the live semantic/SLO startup self-test.
- The startup self-test checks embedding dimensions, all 6/6 semantic Top-1 cases, query P95 latency and peak process RSS, and emits structured `rag14_startup_selftest` evidence.
- The canonical R01/Fargate task envelope is prepared at 256 CPU units and 1024 MiB memory based on the measured production-provider candidate headroom.
- A RAG.14 canary approval must bind the exact runtime source SHA, exact immutable ECR image digest, one IPv4 `/32`, bounded tenant/project/service-principal policy, and fresh external-spend approval.
- Unknown approval fields are rejected. Historical generic R01 approval material is not a valid RAG.14 approval.

## No active approval

Repository readiness does not itself create a fresh RAG.14 canary approval and does not authorize an AWS apply, ECS mutation, image publication, DNS mutation, secret mutation, or external spend.

Historical approval material must not be silently reused. Any real canary must be bound to the exact release revision and immutable image being evaluated.

## What repository evidence now proves

The repository now contains and CI-verifies:

- durable Knowledge/RAG runtime wiring and Control Plane policy binding;
- durable SQLite-backed vector persistence and recovery primitives;
- a pinned multilingual E5 production embedding provider implementation;
- target-container certification and immutable provider/artifact integrity checks;
- a 1 GiB Fargate memory envelope;
- a fail-closed live provider semantic/SLO startup gate;
- exact-head CI coverage for the above repository-side controls.

These facts establish repository/configuration readiness only. They do not prove an AWS task has run successfully.

## Runtime evidence still required

A real bounded canary must still prove the exact release image and provider on the actual target runtime. Evidence must include, as applicable:

1. exact release source SHA and immutable image digest;
2. successful deployment result on the intended AWS target;
3. provider startup self-test PASS from the live task;
4. observed memory/CPU and deployment health;
5. production-strength tenant-isolation and authorization behavior;
6. DLP/injection/leakage controls in the deployed path;
7. deletion/revocation reconciliation and backup/restore evidence;
8. observability/SLO/alert evidence;
9. routing/FinOps and actual cost evidence;
10. rollback/recovery evidence.

`RAG14PromotionGate` remains fail-closed until the complete governed production evidence set is present. Even a complete local evidence package can only become `READY_FOR_GOVERNED_PROMOTION_REVIEW`; it does not autonomously deploy or approve production.

## Promotion boundary

The production provider existing in the repository is not the same as production runtime evidence. Production promotion remains blocked until the exact provider and release artifact have been exercised in the real governed runtime and the remaining RAG.14 evidence requirements are satisfied.

## Forbidden claims

```text
Canary prepared == canary deployed               NO
Provider implemented == provider proven live     NO
Canary deployed == production approved           NO
Startup self-test code == live startup PASS       NO
Signed image == RAG production                   NO
Repository CI == production SLO                  NO
Historical approval == fresh RAG approval        NO
```
