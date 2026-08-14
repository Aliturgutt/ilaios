# sf-runtime-qa

Identity: `sf-runtime-qa` v1.0.0, IMPLEMENTED, build-release-operations.

Purpose: perform governed smoke/runtime validation. Inputs: `intent`, `critical_workflows`. Outputs: runtime checks, health behavior, critical workflows, failure classification, runtime evidence.

Specialization: startup, required health behavior and critical workflows are evaluated only through canonical SF-6 RuntimeAdapters and evidence collection; no unsandboxed fallback.

The common `../CONTRACT.md` applies.
