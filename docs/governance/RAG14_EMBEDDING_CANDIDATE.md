# RAG.14 — Self-Hosted Embedding Candidate

## Status

`PINNED_CANDIDATE / TARGET_RUNTIME_BENCHMARK_REQUIRED / PRODUCTION_BLOCKED`

This document records a zero-API-fee, self-hosted embedding candidate for the Knowledge/RAG production workstream. It does not promote the candidate to a production provider and does not authorize deployment, spend, or external mutation.

## Candidate

```text
upstream: intfloat/multilingual-e5-small
revision: 095f0e876da34e2059887fa44e42d52e7909bfe7
license: MIT
embedding dimensions: 384
retrieval prefixes: query: / passage:
model artifact: onnx/model_qint8_avx512_vnni.onnx
model SHA-256: dd476dd0c2514e9b9be83aeb3853fac0763e0bdf4a71645407587d77c48a2d88
model size: 118346824 bytes
```

The candidate manifest is authoritative for this bounded certification attempt:

`infra/rag/multilingual-e5-small-qint8.candidate.json`

## Why target-runtime certification is required

Repository metadata, license information, upstream hashes, and file size are necessary supply-chain evidence but do not prove that the model can run inside the ILAIOS target runtime.

The current R01 application image is Alpine/musl while the pinned ONNX Runtime Python distribution for Linux x86_64 is a manylinux/glibc build. Therefore an Ubuntu host-only benchmark cannot be treated as target-container compatibility evidence.

The certification workflow runs the pinned candidate inside `python:3.12.13-slim-bookworm` on linux/amd64, records the resolved container image digest, and measures:

```text
artifact SHA-256 verification
exact package versions
actual ONNX CPU inference
actual embedding dimension
Turkish retrieval Top-1
English retrieval Top-1
cross-lingual retrieval Top-1
peak process RSS
P95 query latency
Linux x86_64 execution identity
```

## Measured memory decision

The first glibc target-container measurements established that the model executes correctly and quickly, but consumes about 483 MiB peak RSS. Disabling the ONNX CPU memory arena did not materially reduce that peak. Therefore the existing 512 MiB ECS task envelope is not production-safe once the surrounding ILAIOS runtime is included.

The candidate is now evaluated against a planned 1 GiB task envelope with a 768 MiB maximum benchmark RSS. This retains at least 256 MiB of task-level headroom before production canary measurements. The infrastructure must be separately aligned to 1 GiB and the resulting cost/spend change must remain release-bound and approval-gated before any AWS apply.

The language fixture was also corrected so the case labelled `tr-tenant` uses a Turkish tenant-isolation passage. Cross-lingual quality remains independently covered by dedicated English↔Turkish cases. With that correction, the measured retrieval suite reached 6/6 Top-1; no quality threshold was relaxed.

## Certification states

```text
CANDIDATE_NOT_CERTIFIED
    ↓ measured target-container workflow PASS
TARGET_RUNTIME_CERTIFIED_CANDIDATE
    ↓ real AWS canary inference + CPU compatibility + governed production evidence
eligible for governed production-provider decision
```

Neither state is `PRODUCTION`. The certification evaluator always emits:

```text
production_approved = false
```

## Execution policy

The workflow `.github/workflows/rag14-embedding-candidate-certification.yml` performs no cloud mutation and has no credentials. It can run on a bounded pull request touching the candidate/certification package, and it remains manually dispatchable for explicit re-certification.

The workflow:

1. checks out the exact source SHA;
2. resolves the glibc target base image and records its immutable digest;
3. executes the benchmark inside that linux/amd64 container;
4. installs exact top-level certification package versions only inside the ephemeral container;
5. downloads artifacts only from the pinned upstream revision;
6. verifies SHA-256 before model loading;
7. runs the measured multilingual retrieval benchmark;
8. fails if memory, latency, dimensions, artifact identity, runtime versions, language coverage, or Top-1 quality violate the candidate policy;
9. prints measured evidence to the workflow summary.

## CPU compatibility boundary

The selected upstream artifact is named `model_qint8_avx512_vnni.onnx`. A successful GitHub target-container benchmark does not prove that every AWS Fargate host exposes the CPU instruction capabilities used by the optimized model. The production workstream therefore still requires a real bounded AWS canary inference proof on the exact release image before this provider can satisfy `production_embedding_provider` evidence.

## Production boundary

The current AWS Knowledge runtime still rejects `PRODUCTION` while the only configured embedding mode is the deterministic verification adapter. This candidate package does not change that rule.

A future production-provider promotion still requires at minimum:

```text
successful measured target-container candidate evidence
1 GiB target task envelope aligned in infrastructure
exact pinned runtime image + package/model identities
real AWS canary inference and CPU compatibility proof
production tenant/auth/DLP/leakage evidence
production observability/SLO evidence
release artifact + deployment health + rollback evidence
RAG14PromotionGate completeness
governed production decision
```

No external paid embedding API is required by this candidate design.
