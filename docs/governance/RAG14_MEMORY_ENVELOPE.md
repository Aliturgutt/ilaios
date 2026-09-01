# RAG.14 — 1 GiB Runtime Memory Envelope

## Current truth

Measured glibc target-container evidence for the pinned multilingual E5 candidate showed peak process RSS of approximately 483 MiB while maintaining 6/6 Top-1 retrieval quality and single-digit-millisecond P95 query latency. That leaves insufficient safety margin inside the historical 512 MiB ECS task once the surrounding ILAIOS runtime, HTTP server, durable SQLite stores, policy evaluation, and operational overhead are included.

## Prepared envelope

The canonical R01 task definition is prepared for:

```text
cpu: 256 units / 0.25 vCPU
memory: 1024 MiB
candidate benchmark ceiling: 768 MiB
minimum benchmark-to-task headroom: 256 MiB
```

This is configuration readiness only. It does not apply infrastructure, publish an image, start an ECS task, change DNS, or grant RAG.14 production authority.

## Cost and mutation boundary

Increasing requested task memory changes the resource envelope and can change AWS spend when deployed. Therefore any actual OpenTofu apply remains a fresh release-bound external-mutation decision. Historical or revoked approvals must not be reused.

## Production evidence still required

The 1 GiB envelope is not itself production proof. A bounded AWS canary must still demonstrate the exact release image and provider on the actual Fargate runtime, including CPU compatibility, measured task memory, health, tenant isolation, authorization/DLP/leakage controls, observability/SLO, deletion/backup recovery, cost evidence, and rollback.
