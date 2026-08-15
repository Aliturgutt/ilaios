# RAG.14 — Self-Hosted Embedding Candidate

## Status

`PINNED_CANDIDATE / HOST_BENCHMARK_NOT_YET_EXECUTED / PRODUCTION_BLOCKED`

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

## Why it is not certified yet

Repository metadata, license information, upstream hashes, and file size are necessary supply-chain evidence but they do not prove that the model is acceptable in the current ILAIOS production runtime.

The following must be measured by the manual certification workflow before host-candidate certification:

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

Thresholds are intentionally bounded against the existing 512 MiB task memory limit. The candidate must keep peak benchmark RSS at or below 384 MiB, leaving explicit memory headroom for the surrounding runtime rather than consuming the whole task budget.

## Certification states

```text
CANDIDATE_NOT_CERTIFIED
    ↓ measured workflow PASS
HOST_CERTIFIED_CANDIDATE
    ↓ target canary runtime proof + independent production evidence
eligible for governed production-provider decision
```

`HOST_CERTIFIED_CANDIDATE` is not `PRODUCTION`.

The certification evaluator always emits:

```text
production_approved = false
```

## Execution policy

The workflow `.github/workflows/rag14-embedding-candidate-certification.yml` is `workflow_dispatch` only. It has no push trigger and therefore does not autonomously spend GitHub Actions minutes or download the model merely because this package is merged.

When explicitly run, the workflow:

1. checks out the exact source SHA;
2. installs exact top-level certification package versions;
3. downloads artifacts only from the pinned upstream revision;
4. verifies SHA-256 before model loading;
5. runs the measured multilingual retrieval benchmark;
6. fails if memory, latency, dimensions, artifact identity, runtime versions, language coverage, or Top-1 quality violate the candidate policy;
7. prints measured evidence to the workflow summary.

## Production boundary

The current AWS Knowledge runtime still rejects `PRODUCTION` while the only configured embedding mode is the deterministic verification adapter. This candidate package does not change that rule.

A future production-provider promotion still requires at minimum:

```text
successful measured candidate evidence
target-compatible runtime/container proof
production tenant/auth/DLP/leakage evidence
production observability/SLO evidence
release artifact + deployment health + rollback evidence
RAG14PromotionGate completeness
governed production decision
```

No external paid embedding API is required by this candidate design.
