# ADR-0009 — Agent Registry / AgentManifest Is the Canonical Agent Identity Source

**Status:** Accepted — Canonical Rationale  
**Date:** 2026-08-13  
**Authority:** This ADR records rationale only and does not override canonical documents.

## Context

Agent names and relationships may appear in documentation tables, dashboards, UI projections, or operational reports. If those views become independent authorities, agent identity, permissions, and capability boundaries can drift.

## Decision

ILAIOS uses **one canonical Agent Registry / AgentManifest identity source**. Agent lists, tables, dashboards, and documentation views are projections only. The registry defines agent identity and declared boundaries; actual execution authority continues to come from PolicyDecision, ExecutionGrant, and applicable approval rules.

## Consequences

- There is no second agent identity truth.
- Documentation and UI can describe agents without granting authority.
- Agent count is not a constitutional constant; validated capability topology determines the required set.
- AgentManifest changes affecting capabilities or risk boundaries require versioning and governance review.

## Canonical References

- `../GOVERNANCE.md`
- `../IMPLEMENTATION_SPEC.md`
- `../DATA_ARCHITECTURE.md`
