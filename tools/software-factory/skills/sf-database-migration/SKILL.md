# sf-database-migration

Identity: `sf-database-migration` v1.0.0, IMPLEMENTED, data-contract, critical risk.

Purpose: classify and plan governed database migrations. Inputs: `intent` and typed `schema_changes`. Outputs: schema change, destructive classification, compatibility, migration order, data-loss risk, forward migration, rollback/compensation, backup requirement and deployment sequencing.

Destructive/high-risk changes require REVIEW_REQUIRED or BLOCK by policy. No migration executes directly from this skill. Independent review is mandatory.

The common `../CONTRACT.md` applies.
