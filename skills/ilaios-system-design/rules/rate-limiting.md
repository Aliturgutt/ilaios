# Rate Limiting Rules

1. Apply limits at the narrowest useful identity boundary: principal, tenant, project,
   API key, endpoint or workload class.
2. Limits must protect downstream systems, not only the edge tier.
3. Burst allowances and sustained rates must be explicit.
4. Return deterministic retry guidance where the protocol permits it.
5. Rate limiting must not become a cross-tenant denial-of-service mechanism.
6. Algorithm choice is requirement-driven; the skill must not pretend one limiter
   algorithm is universally correct.
