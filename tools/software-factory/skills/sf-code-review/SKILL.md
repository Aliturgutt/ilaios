# sf-code-review

Identity: `sf-code-review` v1.0.0, IMPLEMENTED, independent-verification.

Purpose: independently review proposed code changes. Inputs: `intent`, `changed_paths`, `change_evidence`. Outputs: findings with ID/severity/location/evidence/reason/remediation/status, a decision, and evidence references.

Allowed decisions: APPROVE, REJECT, CHANGES_REQUIRED, REVIEW_REQUIRED. Generated code cannot self-certify; reviewer independence is mandatory.

The common `../CONTRACT.md` applies.

## ILAIOS native methodology overlay

Apply `ilaios.skill.governance.review.v1` / `ILAIOS-METHODOLOGY-GOVERNANCE-V1` to affected governance boundaries. Inventory identity/tenant/capability/tool/provider/data/egress paths; classify side effects and reversibility; verify least privilege, Policy/Approval/Tool Gateway, budget, provenance, evidence, rollback/recovery, and search for alternate-route or failure-open bypasses. Missing mandatory governance evidence fails closed. This advisory overlay cannot grant authorization or replace deterministic governance engines.
