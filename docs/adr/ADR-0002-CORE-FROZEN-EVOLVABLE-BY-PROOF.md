# ADR-0002 — Core Frozen by Default, Evolvable by Proof

**Status:** Accepted — Canonical Rationale  
**Date:** 2026-08-13  
**Authority:** This ADR records rationale only and does not override canonical documents.

## Context

A platform Core that changes for every new feature eventually absorbs provider logic, UI logic, factory logic, and domain-specific behavior. That increases blast radius and makes the Core a convenience layer rather than a constitutional boundary.

## Decision

The ILAIOS Core is **frozen by default and evolvable only by proof**. A Core change requires evidence that a platform-wide invariant or canonical contract cannot be correctly implemented inside an existing governed capability boundary. Approved evolution extends the single existing Core in place.

## Consequences

- Convenience alone is not a valid Core-change reason.
- Provider, model, factory, UI, and domain-specific intelligence remain outside Core.
- Core changes require explicit governance, compatibility analysis, tests, and evidence.
- No `core_v2` or permanent parallel Core is created.

## Canonical References

- `../SYSTEM_ARCHITECTURE.md`
- `../IMPLEMENTATION_SPEC.md`
- `../GOVERNANCE.md`
