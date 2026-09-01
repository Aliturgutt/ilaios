---
name: auth-authorization-testing
description: Bounded first-party ILAIOS authentication and authorization observation testing through the existing WebAPISec path.
---

# Auth Authorization Testing

Use this skill to evaluate already-observed authentication and authorization outcomes for an explicitly authorized scope.

## Authority

Owner: `ilaios.agent.security.web-api.v1`

Capability: `security.web-api`

This skill does not widen WebAPISec authority. It accepts caller-supplied observations only and cannot perform network requests, use credentials, bypass controls, mutate repositories, or execute exploits.

## Required inputs

- admitted WebAPISec invocation
- valid execution grant
- security scope identifier
- one or more bounded observations containing case id, case kind, HTTP status, and optional location

Supported case kinds: `unauthenticated`, `cross_tenant`, `insufficient_role`, `authorized`.

## Execution

1. Confirm governance admission and canonical WebAPISec ownership.
2. Validate all observations fail-closed.
3. Evaluate unauthenticated, cross-tenant, insufficient-role, and authorized-flow outcomes.
4. Emit structured SecurityReport findings through the existing runtime adapter.
5. Preserve the canonical evidence and SecurityVerifier path when verification is required.

## Guardrails

- No network access.
- No credential use or extraction.
- No active exploitation.
- No authentication/authorization bypass.
- No repository mutation.
- No tenant or governance bypass.
- Duplicate or malformed observation evidence fails closed.

## Status rule

Analysis output is not verification. `VERIFIED` requires the existing independent SecurityVerifier evidence path.
