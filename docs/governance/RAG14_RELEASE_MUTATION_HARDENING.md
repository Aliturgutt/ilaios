# RAG.14 Release Mutation Hardening

## Current truth

The RAG.14 embedding-candidate merge exposed a release-automation boundary defect: `.github/workflows/aws-r01-image-publish.yml` listened to broad `services/**` pushes on `master`, so a certification-only source change caused an AWS ECR image publication even though no RAG canary or production deployment had been approved.

Observed run `31888912862` published immutable ECR image digest `sha256:91b3896622dae9569d116ef9f5ee36dd49bb84528d16ab0abc31d2f1319327a9`, completed ECR scan with zero CRITICAL/HIGH findings, and completed managed signing. The run did not perform ECS, DNS, canary apply, limited apply, or production apply. This artifact therefore is not deployment or RAG.14 production evidence.

## Hardened boundary

R01 image publication is now an explicit external-mutation operation:

- no automatic `push` trigger;
- manual `workflow_dispatch` only;
- exact lowercase 40-character `source_sha` required;
- explicit `confirm_external_mutation=true` required;
- exact source commit is checked out and verified before AWS authentication;
- Git credentials are not persisted;
- GitHub Actions dependencies use immutable revisions;
- build tag and ECR immutable tag are derived from the requested exact source SHA.

This does not grant production approval. RAG.14 canary/limited/production promotion remains governed by its release-bound approval and evidence gates.

## Production closure implication

A future RAG.14 production artifact must be deliberately published from the exact release SHA and its resulting immutable image digest must be reconciled into the RAG.14 evidence set. Unrelated source merges must not produce external AWS mutations merely because they touch `services/**`.
