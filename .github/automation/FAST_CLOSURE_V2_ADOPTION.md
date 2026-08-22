# Fast-Closure V2 Worker Adoption

All persistent automation workers must read `.github/automation/fast-closure-v2-state.json` at the start of a run and treat it as coordination metadata only. It never supersedes live GitHub truth, required CI, repository rulesets, or authoritative workstream ledgers.

## Required worker behavior

1. Re-read exact live master and the workstream's authoritative ledger/PR before mutation.
2. Read the durable Fast-Closure state and current merge-token owner.
3. If another workstream owns a live merge freeze/token, continue only non-overlapping development/test/CI/evidence preparation.
4. Do not replay/resync merely because master advanced while the workstream is developing or waiting on CI.
5. Perform fresh replay/resync only when the workstream enters its actual merge window and currentness requires it.
6. Update lifecycle state after meaningful progress using one of the allowed lifecycle values.
7. Release the token immediately for a proven external/human blocker.
8. Prefer exact-SHA artifact reuse for expensive deterministic outputs when provenance/digest/trust boundaries are proven; otherwise rebuild and fail closed.
9. Do not create temporary PR-specific scheduled automations when an existing persistent worker owns the workstream.
10. A worker may perform several safe dependent actions in one run inside one bounded scope, but it must checkpoint before switching scope.

## Time-to-close priority factors

Priority should be recomputed from live evidence using:

- remaining required gates
- expected CI/runtime duration
- external blocker probability
- replay/resync cost
- downstream unlock value
- current branch freshness
- exact-master verification cost

Implementation percentage alone is not sufficient.

## Artifact reuse safety

Artifact reuse is valid only when all of the following hold:

- producer and consumer bind to the identical exact source SHA
- artifact digest is recorded and verified
- producer workflow is trusted for the consuming gate
- required inputs/configuration are included in provenance
- reuse cannot convert an UNKNOWN state into PASS
- any provenance mismatch fails closed and forces rebuild

This is an optimization of duplicated computation, not an authorization to remove required gates.
