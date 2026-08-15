# RAG.14 — Canary Preparation

## Current state

`CANARY_CONFIGURATION_READY / CANARY_NOT_APPROVED / PRODUCTION_BLOCKED`

This package prepares the existing AWS staged runtime to carry the bounded Knowledge/RAG verification implementation without converting repository evidence into a production claim.

## Repository-side controls

- Knowledge is disabled in AWS staged infrastructure by default.
- Enabling Knowledge requires an explicit server-side principal, tenant, project, classifications, purposes, residencies and embedding mode.
- The current only implemented embedding mode is `verification_hash_v1`.
- `verification_hash_v1` is allowed only for `NOT_DEPLOYED`, `CANARY`, or `LIMITED` evidence exercises.
- `PRODUCTION + Knowledge` fails closed while the verification embedding adapter is the only available implementation.
- Terraform independently rejects Knowledge in `PRODUCTION` under the current verification-provider boundary.
- A RAG.14 canary approval must bind the exact runtime source SHA, exact immutable ECR image digest, one IPv4 `/32`, bounded tenant/project/service-principal policy, and fresh external-spend approval.
- Unknown approval fields are rejected. The historical generic R01 approval shape is not a valid RAG.14 approval.

## No active approval

No `.github/rag14-canary-approval.json` is created by this work. No AWS apply, ECS mutation, DNS mutation, secret mutation, or external spend is authorized by repository preparation alone.

The existing historical `.github/r01-canary-apply-approval.json` is not accepted as RAG.14 evidence and must not be silently reused.

## Promotion boundary

A future bounded canary may use `verification_hash_v1` only to prove runtime wiring, tenant isolation, durable state, deletion/revocation reconciliation, backup/restore, observability and deployment health. It cannot satisfy the RAG.14 `production_embedding_provider` requirement.

Production promotion still requires a separately selected and certified production embedding implementation plus the remaining runtime/evidence requirements enforced by `RAG14PromotionGate`.

## Forbidden claims

```text
Canary prepared == canary deployed              NO
Canary deployed == production embedding proven  NO
Signed image == RAG production                  NO
Repository CI == production SLO                 NO
Historical R01 approval == fresh RAG approval   NO
```
