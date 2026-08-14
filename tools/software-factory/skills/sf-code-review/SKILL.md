# sf-code-review

Identity: `sf-code-review` v1.0.0, IMPLEMENTED, independent-verification.

Purpose: independently review proposed code changes. Inputs: `intent`, `changed_paths`, `change_evidence`. Outputs: findings with ID/severity/location/evidence/reason/remediation/status, a decision, and evidence references.

Allowed decisions: APPROVE, REJECT, CHANGES_REQUIRED, REVIEW_REQUIRED. Generated code cannot self-certify; reviewer independence is mandatory.

The common `../CONTRACT.md` applies.
