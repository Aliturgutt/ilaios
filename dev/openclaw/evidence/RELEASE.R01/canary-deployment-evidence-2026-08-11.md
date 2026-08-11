# RELEASE.R01 Canary deployment evidence

Decision: PASS

Observed from GitHub Actions guarded apply run 31441253937 on commit `232197c617ed137f0fbf52766dcb421dcc1be75b`.

- AWS account: `101180464425`
- Region: `eu-central-1`
- Canary tenant: `ilaios-r01-canary`
- Approved IPv4 allowlist: `176.217.181.22/32`
- Immutable ECR image digest: `sha256:4534f8af614aa4fd890785e19f27e2ede7ce59435def93069884156261b86931`
- ACM certificate status prerequisite: `ISSUED`
- AWS authentication: GitHub OIDC assumed role `ILAIOS-GitHub-Deploy-Role`; no static AWS credentials introduced
- OpenTofu apply: successful
- ECS service: `ACTIVE`, desired `1`, running `1`, pending `0`
- ECS task definition after deployment: `arn:aws:ecs:eu-central-1:101180464425:task-definition/ilaios-r01-canary:4`
- ALB target health: `healthy`
- Canary DNS target: `ilaios-r01-canary-882623857.eu-central-1.elb.amazonaws.com`
- TLS listener is backed by the validated ACM certificate in the guarded OpenTofu configuration
- Serialized OpenTofu state artifact: `r01-tofu-state`, artifact ID `9083136103`, retained 90 days, artifact digest `sha256:913bff1f66c00f6f0330a5bf6142ea8f657ef6978c036d8b21b80b1ea2fd6283`
- Rollback mechanism retained: prior immutable ECS task-definition ARN with forced ECS deployment; ECS deployment circuit breaker remains part of the R01 design

Primary workflow evidence:
`https://github.com/Aliturgutt/ilaios/actions/runs/31441253937`

This evidence closes the previously recorded deployment blocker. No RELEASE.R02 or RELEASE.R03 promotion is authorized or performed.