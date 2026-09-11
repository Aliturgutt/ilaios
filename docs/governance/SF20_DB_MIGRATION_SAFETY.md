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

## Canonical review acceptance

`REVIEW_REQUIRED` is not downgraded or removed. The SF-20 admission owner may accept that disposition only when an independent review artifact exactly matches the migration changeset.

The canonical evidence path is:

`docs/governance/sf20-reviews/<base_sha>-<changeset_sha256>.json`

`changeset_sha256` is the canonical SHA-256 of the selected migration added-line records (`path`, `line`, `text`). The evidence object must contain exactly these fields:

- `schema_version`: `1`
- `decision`: `"ACCEPT"`
- `base_sha`: exact lowercase 40-hex base commit SHA
- `changeset_sha256`: exact canonical migration changeset digest
- `changeset_author`: author identity resolved from Git for the staged/reviewed changeset
- `reviewer`: non-empty independent reviewer identity; it must differ from `changeset_author`
- `reviewed_at`: timezone-qualified ISO-8601 timestamp
- `migration_files`: exact migration-file set from the SF-20 report
- `finding_fingerprints`: exact set of all `REVIEW_REQUIRED` finding fingerprints
- `review_notes`: non-empty review record explaining the independent assessment

Acceptance is fail-closed. Missing evidence leaves `REVIEW_REQUIRED` unresolved. Malformed evidence, wrong base SHA, wrong changeset digest, wrong author, self-review, wrong migration-file set, or incomplete/extra finding fingerprints is rejected. A `BLOCK` finding can never be accepted by review evidence.

The safety report continues to show the original safety disposition. Admission records the accepted reviewer, evidence path, and evidence SHA-256 separately so the risk classification is not rewritten and the review decision remains auditable.

## Evidence and authority boundary

The SF-20 report is deterministic and bound to scan scope, exact base/head SHAs when running in CI, migration files, finding metadata, and a canonical report SHA-256. The gate does not execute SQL, open a database connection, publish artifacts, deploy, promote, mutate production, or authorize any runtime migration action.

A plain `PASS` proves only that the reviewed migration delta did not trigger the configured safety policy and that any touched canonical control-plane migration authority still satisfies its structural recovery invariants. An accepted `REVIEW_REQUIRED` proves only that exact SF-20 findings for the exact migration changeset received matching independent review evidence. Neither state proves a production migration has been executed, that a live backup is restorable, or that database-specific lock/performance behavior is safe without later deployment/runtime validation gates.
