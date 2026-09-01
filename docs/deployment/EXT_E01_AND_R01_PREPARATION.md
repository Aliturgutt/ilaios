# EXT.E01 and RELEASE.R01 Preparation

This package records AWS Canary preparation for account `101180464425` in
`eu-central-1`. It performs no deployment and leaves `ReleaseState.NOT_DEPLOYED`.

## Prepared contracts

- `infra/deployment/ext-e01-prerequisites.yaml` records provider, platform,
  capability, ownership, runtime-gap, and human-decision inputs.
- `infra/deployment/dns-tls-template.yaml` records domain, DNS, certificate,
  renewal, and validation inputs without inventing values.
- `infra/deployment/secrets-inventory.yaml` records secret references and
  lifecycle controls; it contains no credentials.
- `infra/release/r01_canary_prerequisites.yaml` is a fail-closed checklist for
  the future, explicitly approved canary promotion.

## Bound AWS implementation

`infra/aws/r01-canary` provides fail-closed OpenTofu configuration for the
minimum current runtime: ECR, one ECS Fargate task, encrypted EFS for proven
SQLite/filesystem adapters, allowlisted TLS ALB, CloudWatch, scoped IAM, ACM,
and a referenced Secrets Manager secret. It does not add EKS, RDS, S3, SQS,
NAT Gateway, Route 53, or a second region.

Historical runtime gaps are superseded by
`dev/openclaw/evidence/recovery/RELEASE.R00.REVALIDATION.v1/decision.yaml`.
The OIDC workflow runs `aws sts get-caller-identity` first and uploads its exact
JSON result; no static AWS credential is stored.

## FinOps boundary

ECS Fargate, ALB, EFS, CloudWatch, ECR storage, Secrets Manager, and data
transfer can incur external spend. VPC/IAM/ACM no-direct-charge components and
AWS credits do not override `external_spend: false`. Deployment is blocked on
`REQUIRED_EXTERNAL_SPEND_APPROVAL`.

## Promotion boundary

Preparation is not promotion. RELEASE.R01 remains prohibited until its explicit
human approval exists and every infrastructure, exposure, operations, and
security prerequisite in the canary checklist has independently verifiable
evidence. RELEASE.R02 and RELEASE.R03 remain out of scope.
