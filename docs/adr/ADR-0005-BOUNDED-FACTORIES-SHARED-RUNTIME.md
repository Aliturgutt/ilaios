# ADR-0005 — Bounded Factories on the Shared Governed Runtime

**Status:** Accepted — Canonical Rationale  
**Date:** 2026-08-13  
**Authority:** This ADR records rationale only and does not override canonical documents.

## Context

ILAIOS needs domain-specific execution for Web, Video/Media, Software/App, Research/Data, Security, Creative/Document, Commerce/Growth, Personal Operations, and related capabilities. Making each factory a mini-platform would duplicate planning, policy, routing, state, recovery, and evidence.

## Decision

A Factory is a **bounded domain workflow/DAG and orchestration layer** running on the shared ILAIOS Control Plane and governed execution runtime. Factories may compose capabilities and typed artifacts but do not own a second Core, Planner, policy authority, routing truth, or evidence truth.

## Consequences

- Factories can evolve independently at the domain layer without fragmenting platform authority.
- Cross-factory composition uses typed contracts and the shared Control Plane.
- Factory-specific hidden runtimes and direct provider bypasses are prohibited.
- Shared recovery, approval, routing, evidence, and budget controls remain reusable.

## Canonical References

- `../SYSTEM_ARCHITECTURE.md`
- `../DEPENDENCY_GRAPH.md`
- `../GOVERNANCE.md`
