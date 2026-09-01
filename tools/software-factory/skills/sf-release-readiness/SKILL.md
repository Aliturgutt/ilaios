# sf-release-readiness

Identity: `sf-release-readiness` v1.0.0, IMPLEMENTED, build-release-operations, critical risk.

Purpose: evaluate readiness from validation, independent review, security, dependency/license and artifact evidence. Inputs: `intent`, `artifact_references`, `validation_evidence`. Outputs: artifacts, validations, supply-chain checks, unresolved blockers, release disposition.

This skill never publishes. It returns PromotionProposal/readiness evidence only; unresolved blockers prevent PASS. Independent review is required.

The common `../CONTRACT.md` applies.

## ILAIOS native methodology overlay

Apply `ilaios.skill.governance.review.v1` / `ILAIOS-METHODOLOGY-GOVERNANCE-V1` to release evidence. Confirm identity/tenant/capability boundaries, policy/approval disposition, side effects, supply-chain provenance, exact-head tests/review, rollback/recovery and unresolved blockers. Documentation is not implementation; implementation is not testing; CI is not production verification. Promote only to the highest maturity directly supported by observed evidence. This advisory overlay never publishes or authorizes a release.
