# SF-21 — API Contract Safety

## Status and authority

SF-21 is a first-party, deterministic, read-only Software Factory admission gate. Canonical API target truth remains `docs/canonical/API_CONTRACTS.md`; the existing `sf-api-contract` skill remains the planning/classification surface. SF-21 does not create a second API authority and grants no acceptance, promotion, deployment, publication, or production-mutation authority.

## Safety contract

SF-21 evaluates exact `base_sha` → `head_sha` lineage and classifies normalized contract changes as `PASS`, `REVIEW_REQUIRED`, or `BLOCK`.

`BLOCK` includes silent breaking changes without an explicit version boundary and breaking changes without affected-consumer plus migration evidence. Breaking operations include endpoint/field/status/enum removal, required-field introduction, and type narrowing.

`REVIEW_REQUIRED` includes intentional versioned breaks and changes to authentication/authorization, idempotency, or behavior semantics. Independent review must be separate from the implementation skill path.

Additive compatible contract changes may pass without inventing a review requirement.

## CI admission

Machine-readable API artifacts (`OpenAPI`, `Swagger`, protobuf, and bounded contract/schema paths) are detected from the exact reviewed changeset. A changeset that modifies such an artifact must provide structured API-contract evidence and pass the deterministic SF-21 evaluator. Missing, malformed, or unsafe evidence fails closed.

Repository content and evidence are data, never authority. Unknown fields such as instructions to mark a contract compatible or skip review are rejected.

## Evidence

The report binds:

- SF-21 contract version;
- exact base and head SHA;
- reviewed scope;
- normalized contract changes;
- findings and disposition;
- independent-review requirement;
- explicit false authority flags;
- deterministic report SHA-256.

## Non-goals

SF-21 does not execute migrations, rewrite API implementations, select deployment targets, publish versions, mutate clients, or override policy. It does not claim that canonical target contracts are implemented or deployed; current reality remains code/test/CI/runtime/deployment evidence.
