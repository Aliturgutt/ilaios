# ILAIOS Product Surface Integration

Use this skill when a canonical product capability, maturity/readiness source, Website product surface, or Desktop product projection changes and downstream surface impact must be assessed.

## Authority

This skill does not create a second capability registry, Core, orchestrator, router, policy engine, approval engine, tool gateway, validation authority, tenant authority, or evidence authority.

Canonical runtime truth remains owned by the existing ILAIOS control-plane/runtime/readiness/evidence sources. `contracts/product_surface_contract.json` is a projection contract only.

## Required flow

1. Re-read current repository and exact branch HEAD.
2. Identify changed canonical source(s).
3. Read `contracts/product_surface_contract.json`.
4. Determine Website and Desktop projection impact.
5. Preserve CURRENT REALITY versus TARGET TRUTH.
6. Never promote `unknown`, documented, designed or implemented state to available/verified/production without required evidence.
7. Keep Website explanatory/public; it may describe target architecture only with truthful maturity framing.
8. Keep Desktop a governed client; operational status comes from authoritative backend/evidence state and fails closed when stale or unavailable.
9. Preserve EN/TR semantic parity for public Website projections.
10. Preserve Policy, Approval, Tool Gateway, Validation, Audit/Evidence, tenant and security boundaries.
11. Run `python scripts/validate_product_surface_contract.py` and the relevant test/CI gates on the exact current HEAD.
12. Record branch, HEAD SHA, PR and CI checkpoint before stopping or moving to the next phase.

## Change rules

- Capability rename/removal/update requires explicit downstream assessment.
- Missing canonical source is a failure, not an implicit default.
- Website and Desktop must not maintain independent maturity truth.
- Desktop cached state cannot outrank a failed authoritative refresh.
- UI labels such as AVAILABLE, VERIFIED, COMPLETED, DEPLOYED or PRODUCTION must be evidence-derived.
- Design changes are out of scope unless separately requested; prefer data/status/projection wiring only.
- Backward-compatible, additive, migration-safe changes are preferred.

## Verification

A valid change requires, as applicable:

- projection contract validation
- stale-source detection
- authority invariant validation
- EN/TR semantic parity assessment
- Website claim/maturity review
- Desktop runtime/evidence projection review
- existing tests and required CI gates
- exact-head attribution

No PASS from an older SHA may be reused as verification for a newer branch head.
