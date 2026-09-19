# sf-database-migration

Identity: `sf-database-migration` v1.0.0, IMPLEMENTED, data-contract, critical risk.

Purpose: classify and plan governed database migrations. Inputs: `intent` and typed `schema_changes`. Outputs: schema change, destructive classification, compatibility, migration order, data-loss risk, forward migration, rollback/compensation, backup requirement and deployment sequencing.

Destructive/high-risk changes require REVIEW_REQUIRED or BLOCK by policy. No migration executes directly from this skill. Independent review is mandatory.

SF-20 execution admission is enforced by `services/software_factory_db_migration_safety.py`. The gate scans exact reviewed/staged migration deltas, blocks clearly destructive/unbounded operations, requires review for compatibility/locking/data-rewrite risk, and verifies the canonical control-plane migration recovery contract when that authority changes. A gate PASS grants no migration-execution, promotion, deployment, or production authority.

The common `../CONTRACT.md` applies.
