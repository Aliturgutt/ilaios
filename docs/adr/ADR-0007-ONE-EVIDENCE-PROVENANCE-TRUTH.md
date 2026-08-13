# ADR-0007 — One Evidence and Provenance Truth

**Status:** Accepted — Canonical Rationale  
**Date:** 2026-08-13  
**Authority:** This ADR records rationale only and does not override canonical documents.

## Context

Autonomous execution produces logs, metrics, traces, runtime state, artifacts, validations, approvals, routing decisions, and external side effects. Treating operational telemetry or status prose as proof would allow false completion and conflicting histories.

## Decision

ILAIOS maintains **one canonical evidence/provenance truth** for material execution and acceptance. Logs and metrics are observability signals; runtime state is operational truth; artifacts are produced outputs; EvidenceRecords prove what was authorized, executed, produced, validated, and accepted for the relevant scope.

## Consequences

- Documentation cannot promote maturity by assertion.
- Logs do not replace evidence.
- Evidence is preserved across retry, repair, resume, cancellation, compensation, rollback, and failure.
- Missing required evidence blocks a claim of verified success.

## Canonical References

- `../canonical/SYSTEM_ARCHITECTURE.md`
- `../canonical/DATA_ARCHITECTURE.md`
- `../operations/OBSERVABILITY.md`
- `../operations/FAILURE_RECOVERY.md`
