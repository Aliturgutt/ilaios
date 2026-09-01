# ADR-0001 — Single Constitutional Core

**Status:** Accepted — Canonical Rationale  
**Date:** 2026-08-13  
**Authority:** This ADR records rationale only and does not override canonical documents.

## Context

ILAIOS needs one platform-wide authority chain for identity, state, policy boundaries, routing, execution governance, and evidence. Parallel Cores or Control Planes would create conflicting truth, inconsistent security, and bypass paths.

## Decision

ILAIOS uses **one Constitutional Core and one authoritative Control Plane**. New factories, providers, models, skills, agents, user interfaces, and domain capabilities must integrate with this existing authority rather than creating a parallel Core or runtime authority.

## Consequences

- Architecture remains coherent across all product domains.
- Domain growth occurs below the shared authority boundary.
- A migration mechanism may exist temporarily only when it has one final authority and an explicit retirement path.
- A second Core, second Planner, second policy authority, second routing authority, or second evidence truth is rejected.

## Canonical References

- `../SYSTEM_ARCHITECTURE.md`
- `../IMPLEMENTATION_SPEC.md`
- `../GOVERNANCE.md`
