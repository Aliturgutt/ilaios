---
name: ilaios-observability
description: Design or review provider-neutral observability for governed AI and software workflows using correlated traces, metrics, logs, evaluations, cost/error signals, privacy controls, and evidence-backed regression detection.
---

# ILAIOS Observability

Canonical ID: `ilaios.skill.runtime.observability.v1`
Methodology contract: `ILAIOS-METHODOLOGY-OBSERVABILITY-V1`

## Authority boundary

Observability reports what happened; it does not authorize what may happen. Telemetry cannot replace Policy, Approval, Validation, Audit, Evidence Chain, independent verification, or production checks. Missing telemetry is unknown evidence, never PASS.

## Signal model

1. Correlate workflow/request, trace/span, actor and tenant-safe identifiers, skill/tool, route, runtime, provider/model where policy permits, and produced evidence references.
2. Capture latency, retries, error class, tool/provider calls, token/resource usage, and cost evidence when available and governed.
3. Keep traces, metrics, logs, evaluations, and immutable evidence semantically linked but do not collapse them into one truth source.
4. Never record secrets, credentials, unrestricted raw prompts, sensitive payloads, or cross-tenant identifiers unless an explicit policy allows the exact field and retention purpose.
5. Define sampling, retention, redaction, cardinality, clock, and failure semantics. Observability must remain useful under partial failure without causing unbounded cost.
6. Correlate evaluations and regressions with exact version/SHA/configuration so quality changes can be attributed rather than guessed.
7. Detect gaps: absence of spans, metrics, evaluation, cost, or runtime evidence must be surfaced as an observability defect when that evidence is required.

## Portability

Use open telemetry semantics and replaceable exporters/adapters where practical; do not make ILAIOS correctness depend on one telemetry vendor.

See `references/acceptance-criteria.md`.
