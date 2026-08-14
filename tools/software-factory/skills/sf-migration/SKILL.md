# sf-migration

Identity: `sf-migration` v1.0.0, IMPLEMENTED, test-quality.

Purpose: plan governed code/platform migrations while preserving compatibility and rollback evidence. Inputs: `intent`, `changed_paths`, `constraints`. Outputs: change proposal, migration steps, compatibility, rollback/compensation, tests, evidence.

Specialization: migration sequencing must be bounded, reversible where policy requires, and validated through canonical runtime adapters. Independent review is required.

The common `../CONTRACT.md` applies.
