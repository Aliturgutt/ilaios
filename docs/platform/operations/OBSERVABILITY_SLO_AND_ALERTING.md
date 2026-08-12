# Observability, SLO and Alerting

Status: CONTROLLED

## Principle
SLOs are production commitments only after telemetry exists. Targets below are initial operational objectives and MUST be measured before being claimed as achieved.

## Initial service objectives
For production control-plane/API paths: target monthly availability >=99.9%; successful-request p95 latency <=1s for non-generation control operations; server error rate <1% over 5-minute windows. Long-running generation/job latency uses per-workload objectives rather than the API p95 target.

## SLIs
Measure availability, request/error rate, latency, job success/failure, queue/backlog where applicable, dependency/provider health, authentication failures, tenant-isolation denials, deployment health, and cost/quota anomalies.

## Alerts
Page/urgent alerts should cover sustained production unavailability, sharp 5xx increase, failed production deployment with user impact, security/tenant-boundary signals, exhausted critical capacity, and backup/restore failures. Warning alerts cover error-budget burn, latency degradation, provider degradation and cost anomalies.

## Dashboards and ownership
Each production service needs an owner, dashboard, environment/version dimension and links from incident/release evidence. Alerts must route to a monitored human channel before the service is considered operationally production-ready.

## Evidence
SLO achievement requires retained telemetry over the stated window. Configuration alone is not evidence that an SLO was met.
