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

`REVIEW_REQUIRED` is not downgraded or removed. The SF-20 admission owner may accept that disposition only when an independent review artifact exactly matches the migration changeset and its reviewer provenance is verified against Git history.

The canonical evidence path is:

`docs/governance/sf20-reviews/<changeset_sha256>.json`

`changeset_sha256` is the canonical SHA-256 of the selected migration added-line records (`path`, `line`, `text`). The evidence object must contain exactly these fields:

- `schema_version`: `1`
- `decision`: `"ACCEPT"`
- `base_sha`: exact lowercase 40-hex review base SHA
- `changeset_sha256`: exact canonical migration changeset digest
- `changeset_authors`: exact migration author identity set resolved from Git, or the staged Git author
- `reviewer`: independent reviewer identity; it must not be one of the migration authors
- `reviewed_at`: timezone-qualified ISO-8601 timestamp
- `evidence_commit_sha`: exact Git commit containing this evidence artifact
- `migration_files`: exact migration-file set from the SF-20 report
- `finding_fingerprints`: exact set of all `REVIEW_REQUIRED` finding fingerprints
- `review_notes`: non-empty review record explaining the independent assessment

The evidence commit is itself validated. It must be in the subject history, its Git author must equal `reviewer`, it must change only its own SF-20 evidence artifact, and the artifact content at that commit must exactly match the current evidence. In reviewed CI changesets, the evidence commit must be separate from and later than all migration-changing commits. For staged changes, the evidence base must remain free of committed migration-file drift before the staged patch is admitted.

Acceptance is fail-closed. Missing evidence leaves `REVIEW_REQUIRED` unresolved. Malformed evidence, wrong/stale base SHA, wrong changeset digest, wrong author set, self-review, unverifiable reviewer provenance, mixed migration/evidence commit, wrong migration-file set, or incomplete/extra finding fingerprints is rejected. A `BLOCK` finding can never be accepted by review evidence.

The safety report continues to show the original safety disposition. Admission records the accepted reviewer, evidence path, evidence commit SHA, and evidence SHA-256 separately so the risk classification is not rewritten and the review decision remains auditable.

## Evidence and authority boundary

The SF-20 report is deterministic and bound to scan scope, exact base/head SHAs when running in CI, migration files, finding metadata, and a canonical report SHA-256. The gate does not execute SQL, open a database connection, publish artifacts, deploy, promote, mutate production, or authorize any runtime migration action.

A plain `PASS` proves only that the reviewed migration delta did not trigger the configured safety policy and that any touched canonical control-plane migration authority still satisfies its structural recovery invariants. An accepted `REVIEW_REQUIRED` proves only that exact SF-20 findings for the exact migration changeset received matching, Git-provenanced independent review evidence. Neither state proves a production migration has been executed, that a live backup is restorable, or that database-specific lock/performance behavior is safe without later deployment/runtime validation gates.
