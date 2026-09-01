# SF-20 DB Migration Safety

SF-20 adds a deterministic, fail-closed database-migration admission gate to the governed Software Factory.

## Scope

- CI scope: migration-related added lines in the exact `REVIEWED_CHANGESET` between exact base/head commit SHAs.
- Pre-commit scope: migration-related added lines in the `STAGED_CHANGESET`.
- The existing `sf-database-migration` skill remains the planning/classification authority; SF-20 is the execution-admission safety gate and does not create a competing migration skill.
- The existing control-plane SQLite migration engine remains the runtime migration implementation. When that authority is changed, SF-20 verifies contiguous up/down version pairing, foreign-key enforcement, backup-before-rollback, and restore-on-failure invariants.

## Dispositions

- `PASS`: no configured migration safety finding is present.
- `REVIEW_REQUIRED`: compatibility, locking, schema-contract, or bounded data-rewrite risk requires independent review before merge.
- `BLOCK`: clearly unsafe operations such as database/schema destruction, unbounded truncation, disabled foreign keys, or unbounded data rewrites are rejected.

Destructive or high-risk schema changes require verified backup and rollback/compensation evidence. Compatibility-sensitive changes should follow expand → migrate/backfill → validate → contract sequencing rather than a one-step destructive cutover.

## Evidence and authority boundary

The SF-20 report is deterministic and bound to scan scope, exact base/head SHAs when running in CI, migration files, finding metadata, and a canonical report SHA-256. The gate does not execute SQL, open a database connection, publish artifacts, deploy, promote, mutate production, or authorize acceptance.

A `PASS` proves only that the reviewed migration delta did not trigger the configured safety policy and that any touched canonical control-plane migration authority still satisfies its structural recovery invariants. It does not prove a production migration has been executed, that a live backup is restorable, or that database-specific lock/performance behavior is safe without the later deployment/runtime validation gates.
