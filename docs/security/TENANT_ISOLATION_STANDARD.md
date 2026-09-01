# Tenant Isolation Standard

Status: CONTROLLED

## Invariant
Every tenant-owned resource must be authorized and accessed in a tenant context established by trusted server-side identity. Client-supplied tenant identifiers are selectors, never authorization proof.

## Requirements
- authorization is enforced at the control plane/data boundary;
- queries and object paths are tenant-scoped by construction;
- workers receive only the minimum tenant/project/job scope required;
- caches, queues, files, logs, vector/search stores and artifacts preserve tenant separation;
- privileged support/admin access is explicit, audited and least-privilege;
- cross-tenant joins/exports are prohibited unless an explicitly governed product capability authorizes them.

## Negative testing
Tests must attempt horizontal and vertical privilege escalation, guessed IDs, stale tokens, cache-key collisions, file-path traversal, cross-tenant artifact retrieval, job/worker confusion, and admin-scope misuse.

## Production evidence
A production isolation claim requires deployed-version identity, auth configuration, representative negative-test results against the intended environment or faithful staging equivalent, and audit evidence showing denied cross-tenant attempts. Repository unit tests alone establish VERIFIED at most.

## Failure
Any confirmed cross-tenant exposure is at least SEV-1 unless evidence proves the exposed data/control plane was non-sensitive and non-production; severity may only be lowered with documented evidence.
