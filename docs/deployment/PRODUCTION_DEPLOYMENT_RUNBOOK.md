# Production Deployment Runbook

Status: CONTROLLED

## Safety boundary
This runbook does not authorize deployment. Production execution requires explicit human approval and the completed production readiness checklist.

## R01 — Canary
Deploy the exact verified immutable artifact to the minimum approved canary scope. Confirm environment/account, artifact digest, migrations, secrets references, health checks, telemetry and cost boundary. Stop on auth/tenant failure, migration uncertainty, severe error regression, missing observability, or unexpected spend/exposure. Run smoke and negative authorization checks. Preserve deployment/run IDs.

## R02 — Limited
Proceed only from a healthy R01 evidence set and separate approval where policy requires. Increase exposure gradually. Compare error rate, latency, job failures and security signals to canary baseline. Halt/rollback on SLO burn, security regression, data-integrity anomaly or dependency instability.

## R03 — Broad production
Proceed only after R02 acceptance evidence. Promote the same artifact unless a new commit/artifact restarts verification. Confirm alerts, dashboards, backup/restore readiness, support/incident path and rollback target before increasing traffic.

## Rollback
Rollback to the prior known-good immutable artifact when stop conditions trigger and rollback is data-compatible. If schema/data changes make rollback unsafe, halt traffic/change and execute the approved forward-fix/recovery plan.

## Completion evidence
Record commit, artifact digest, workflow/run, environment, approval, timestamps, migration result, health/smoke results, telemetry snapshot and final state. No such record means PRODUCTION is not proven.
