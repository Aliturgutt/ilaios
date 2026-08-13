# ADR-0003 — One RoutingDecision Truth

**Status:** Accepted — Canonical Rationale  
**Date:** 2026-08-13  
**Authority:** This ADR records rationale only and does not override canonical documents.

## Context

ILAIOS may use multiple replaceable providers and routing references. If factories, agents, or provider adapters choose providers independently, policy, privacy, residency, quality, budget, and evidence decisions can diverge.

## Decision

Provider/resource selection produces **one canonical governed `RoutingDecision`**. Factories and agents express capability requirements; they do not create independent routing truth. External routing systems may exist only beneath ILAIOS policy and routing authority.

## Consequences

- Provider selection remains replaceable and governed.
- Fallback and re-route paths preserve the same authority model.
- Factory-to-provider and hidden-router bypasses are prohibited.
- Routing decisions can be evidenced and audited consistently.

## Canonical References

- `../SYSTEM_ARCHITECTURE.md`
- `../DEPENDENCY_GRAPH.md`
- `../API_CONTRACTS.md`
- `../GOVERNANCE.md`
