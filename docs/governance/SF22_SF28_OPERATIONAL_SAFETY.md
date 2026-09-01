# SF-22 → SF-28 — Operational Safety Stack

## Authority

This stack adds first-party, deterministic, read-only Software Factory safety contracts. It reuses the existing durable runtime, validation, independent review, build/SBOM/signing evidence, observability, enterprise hardening, and operational drill boundaries. It does not create a parallel runtime, policy engine, promotion service, or recovery authority.

All reports are bound to exact base/head SHA lineage and explicitly grant no repository mutation, promotion, deployment, or production mutation authority.

## SF-22 — Retry / Resume

Retries must be bounded by attempt count, deadline, backoff, and retry budget. Side-effecting work must be idempotent or compensatable and must reuse canonical fencing. Resume checkpoints must be bound to active workflow/task/attempt evidence; stale checkpoints fail closed.

## SF-23 — Resource / Cost Governance

Budgets must be tenant-bound and expressed with a positive hard cap. Estimated cost cannot exceed the hard cap. Concurrency must remain within quota. Provider pricing evidence must be bound. Unlimited-resource requests and autonomous budget overrides are blocked. Near-cap execution preserves `REVIEW_REQUIRED`.

## SF-24 — Observability

Critical execution requires correlation, structured logs, metrics, traces, SLI, SLO, runbook binding, and secret/PII redaction. Missing coverage is `BLOCK`. Exhausted error budget preserves `REVIEW_REQUIRED` rather than silently promoting risk.

## SF-25 — Promotion Gateway

A promotion gate may pass only when validation, independent review, security, dependency/license governance, SBOM, build provenance, signing/attestation, secret scanning, DB migration safety, API contract safety, exact-head CI, and evidence lineage are all satisfied. Any blocker remains a blocker; upstream `REVIEW_REQUIRED` is preserved. A PASS report is eligibility evidence only and never direct deployment authority.

## SF-26 — PR / CI Automation

Software Factory changes require an isolated branch, exact base/head binding, successful required CI, and resolved review obligations. Direct master push, stale lineage, force merge, and validation bypass are blocked.

## SF-27 — Enterprise Hardening

Enterprise hardening requires tenant isolation, least privilege, immutable audit, encryption at rest/in transit, egress and retention policy, identity controls, rate limiting, and incident controls. Unsupported production-ready claims are blocked.

## SF-28 — Recovery

Recovery requires verified backup integrity, tested restore, rollback/compensation, RPO/RTO, failback, resumability, and idempotent or fenced replay. Destructive rollback without backup is blocked. The recovery evaluator emits plans/evidence only and cannot mutate production.

## Repository self-audit

The CI-facing self-audit fails closed if canonical foundations used by these phases disappear, including durable scheduler/execution, Software Factory validation/review/provenance/SBOM/signing, observability, enterprise hardening, operational drills, and canonical FINOPS/OBSERVABILITY/FAILURE_RECOVERY documents.
