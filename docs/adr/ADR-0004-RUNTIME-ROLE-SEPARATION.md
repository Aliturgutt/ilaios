# ADR-0004 — Skill, Agent, Worker, Tool, Adapter, and Provider Separation

**Status:** Accepted — Canonical Rationale  
**Date:** 2026-08-13  
**Authority:** This ADR records rationale only and does not override canonical documents.

## Context

Autonomous systems become unsafe when execution roles collapse into one another. A skill that grants permission, a provider treated as a worker, or a worker treated as policy authority creates hidden privilege escalation and vendor coupling.

## Decision

ILAIOS keeps the following concepts distinct: **Skill ≠ Agent ≠ Worker ≠ Tool ≠ Adapter ≠ Provider**. Skills provide bounded expertise; agents orchestrate within declared boundaries; workers execute scoped tasks; tools expose operations; adapters connect replaceable providers; providers supply external resources. None may self-expand authority.

## Consequences

- A skill cannot expand agent authority.
- A worker cannot mint PolicyDecision, ExecutionGrant, ApprovalDecision, or RoutingDecision authority.
- Providers remain replaceable resources rather than product authority.
- Tool access remains governed through canonical permission and execution boundaries.

## Canonical References

- `../SYSTEM_ARCHITECTURE.md`
- `../IMPLEMENTATION_SPEC.md`
- `../SECURITY_ARCHITECTURE.md`
- `../GOVERNANCE.md`
