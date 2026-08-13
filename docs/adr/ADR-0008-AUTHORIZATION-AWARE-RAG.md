# ADR-0008 — Authorization-Aware Retrieval Is a Security Boundary

**Status:** Accepted — Canonical Rationale  
**Date:** 2026-08-13  
**Authority:** This ADR records rationale only and does not override canonical documents.

## Context

Knowledge/RAG can expose sensitive tenant, project, source, and classified information before generation begins. Applying authorization only after retrieval would allow unauthorized context to enter prompts, workers, providers, logs, or artifacts.

## Decision

Retrieval is **authorization-aware before context is returned**. Retrieval decisions use canonical identity/tenant/project scope and applicable classification, purpose, residency, retention, source authorization, and provenance requirements. Unauthorized retrieval is a security violation, not a relevance error.

## Consequences

- Cross-tenant retrieval is denied.
- Deleted, revoked, or stale source authorization is reconciled before reuse.
- Provider fallback does not weaken privacy or residency constraints.
- Retrieved context retains source/provenance linkage for evidence and validation.

## Canonical References

- `../SECURITY_ARCHITECTURE.md`
- `../DATA_ARCHITECTURE.md`
- `../THREAT_MODEL.md`
- `../FAILURE_RECOVERY.md`
