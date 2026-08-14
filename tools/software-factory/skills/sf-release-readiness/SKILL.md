# sf-release-readiness

Identity: `sf-release-readiness` v1.0.0, IMPLEMENTED, build-release-operations, critical risk.

Purpose: evaluate readiness from validation, independent review, security, dependency/license and artifact evidence. Inputs: `intent`, `artifact_references`, `validation_evidence`. Outputs: artifacts, validations, supply-chain checks, unresolved blockers, release disposition.

This skill never publishes. It returns PromotionProposal/readiness evidence only; unresolved blockers prevent PASS. Independent review is required.

The common `../CONTRACT.md` applies.
