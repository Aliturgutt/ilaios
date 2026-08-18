# Skill: ILAIOS Browser Production Verify

## Purpose

Use an authorized browser capability to verify an exact production target and return observations suitable for evidence-backed release decisions.

## Risk

High. Browser execution can cross authentication, external-service, and production boundaries. Authorization and required approval must be resolved before execution.

## Procedure

1. Resolve the exact target domain, deployment/revision identity, required user context, and acceptance criteria.
2. Require canonical policy admission and approval when applicable. If authorization evidence is unavailable, fail closed.
3. Navigate only through the governed browser/tool boundary; the skill itself does not grant browser access.
4. Confirm the browser is observing the intended production target rather than preview, local, cached, or stale state when that distinction is material.
5. Exercise only bounded flows required by acceptance criteria.
6. Avoid destructive mutations unless separately authorized by policy and approval.
7. Capture observations and failure states through the canonical audit/evidence path.
8. Return VERIFIED only when every required observable criterion passes and identity linkage is established; otherwise return the strongest lower evidence-backed state.

## Forbidden

- credential harvesting or secret exposure;
- bypassing authentication, policy, approval, tenant, or Tool Gateway controls;
- inferring production success from source code, CI, or deployment metadata alone;
- vendor-specific routing embedded in the skill.
