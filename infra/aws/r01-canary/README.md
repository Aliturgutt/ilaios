# RELEASE.R01 AWS Canary

This OpenTofu-compatible package is bounded to AWS account `101180464425`,
`eu-central-1`, and `canary.ilaios.com`. `enable_canary` defaults to `false`.
No apply is permitted while `external_spend: false` remains authoritative.

The minimum runtime is one immutable-digest ECS Fargate task behind an
allowlisted TLS ALB, encrypted EFS for the proven SQLite/filesystem adapters,
ECR, CloudWatch, scoped task identities, ACM, and a referenced Secrets Manager
secret. EKS, RDS, S3, SQS, NAT Gateway, Route 53, and a second region are not
introduced. The task has no public ingress; its public IP avoids chargeable NAT
or VPC endpoints for bounded Canary egress.

Promotion requires `enable_canary=true`, an approved non-empty CIDR allowlist,
an immutable image digest, a validated ACM certificate ARN, an approved secret
ARN, `REQUIRED_EXTERNAL_SPEND_APPROVAL`, and `EXPLICIT_HUMAN_RELEASE_PROMOTION`.
Cloudflare DNS remains separate: create only a DNS-only CNAME for
`canary.ilaios.com` to the ALB target. Roll back to the prior immutable ECS task
definition; the ECS deployment circuit breaker also rolls back failed rollout.
