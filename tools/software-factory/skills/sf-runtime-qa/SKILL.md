# sf-runtime-qa

Identity: `sf-runtime-qa` v1.0.0, IMPLEMENTED, build-release-operations.

Purpose: perform governed smoke/runtime validation. Inputs: `intent`, `critical_workflows`. Outputs: runtime checks, health behavior, critical workflows, failure classification, runtime evidence.

Specialization: startup, required health behavior and critical workflows are evaluated only through canonical SF-6 RuntimeAdapters and evidence collection; no unsandboxed fallback.

The common `../CONTRACT.md` applies.

## ILAIOS native methodology overlay

Apply `ilaios.skill.runtime.observability.v1` / `ILAIOS-METHODOLOGY-OBSERVABILITY-V1` when validating observable runtime behavior. Correlate exact request/version evidence with required traces, metrics, logs, evaluations, latency/retry/error and governed cost signals; enforce redaction/tenant isolation and surface missing required telemetry as unknown evidence, never PASS. Use replaceable telemetry adapters where practical. This instruction-only overlay does not authorize execution or replace runtime, validation, audit, evidence, or production verification.
