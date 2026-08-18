# ilaios-skill-validate

Validate an ILAIOS-native candidate skill before any evaluation or promotion attempt.

## Purpose

Use this skill to reject malformed, ambiguous, unsafe, or governance-bypassing candidate packages early and deterministically.

## Validation checks

1. Machine identity uses the `ilaios.skill.*` namespace.
2. Version is explicit and immutable once promoted.
3. `SKILL.md` contains a bounded purpose, required inputs, outputs, and acceptance criteria.
4. Capability dependencies and permissions are explicit and minimal.
5. No instruction grants itself tool, provider, tenant, secret, or deployment authority.
6. No instruction bypasses Policy, Approval, Tool Gateway, Validation, Audit, Evidence, routing, or tenant boundaries.
7. Authorized trace/evidence provenance is represented by a stable digest or evidence identifier.
8. Supporting scripts are bounded, reviewable, and do not contain secrets.
9. Test scenarios exist before promotion evaluation.
10. External references are provenance only; copied implementation text is rejected.

## Output

Return a validation result with explicit pass/fail findings and evidence references. Validation PASS means only that the candidate is eligible for evaluation; it does not mean the skill is tested, verified, promoted, deployed, or production-ready.

## Fail-closed rule

Any missing identity, permission scope, provenance, scenario coverage, governance boundary, or evidence requirement blocks progression.
