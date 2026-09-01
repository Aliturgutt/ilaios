# ILAIOS Execution Controller Protocol

## Purpose

This protocol standardizes long-running ChatGPT/GitHub execution work without replacing any canonical ILAIOS runtime authority. It is a development-workflow control layer only.

It preserves the existing branch/PR/exact-SHA/CI checkpoint model and adds durable state, bounded locking, repair-loop discipline, evidence binding, and resumability.

## Non-authority boundary

This protocol MUST NOT become or bypass canonical Core, Control Plane, Policy Engine, Approval Engine, Tool Gateway, Validation, Audit/Evidence, tenant isolation, security, DLP, budget, credential, provider-routing, deployment, or Store/publication authority.

Repository automation remains fail-closed when authority or evidence is ambiguous.

## Canonical execution loop

For every governed development task:

1. Re-read live `master` and authoritative task source.
2. Resolve exact task state, active branch/PR, base/head SHA, CI/workflow runs, blockers, and overlapping work.
3. Acquire or refresh a bounded task lock before repository mutation.
4. Select the single dependency-ready action. Continue through additional dependency-ready actions in the same run while safe and time permits.
5. Implement the smallest additive/backward-compatible change.
6. Persist an atomic Git checkpoint promptly.
7. Run targeted validation and required CI on the exact head SHA.
8. On failure, inspect real evidence, classify root cause, implement the smallest justified repair, add regression coverage when appropriate, and retest. Blind retry is prohibited.
9. Before merge, re-read current `master`; stale PASS is invalid. If `master` advanced, compare overlap and replay only the reviewed bounded delta when safe.
10. Merge only with exact-head evidence and expected-head protection under repository policy.
11. After merge, verify exact-master CI and any required runtime/E2E/provider/deployment evidence.
12. Mark a phase `VERIFIED` only when its required evidence chain is complete.
13. Persist `next_action`, release the lock when appropriate, and continue to the next dependency-ready phase.

## Durable state

Every new long-running automation SHOULD create a task-specific state file under:

`.github/automation/states/<task-id>.json`

The state file records at minimum:

- task identity and source
- lifecycle status and current phase
- exact `master`, base, and head SHA
- authoritative branch and PR
- last CI/workflow run and conclusion
- current `next_action`
- blocker classification
- retry counters and last failure fingerprint
- bounded lock owner/scope/expiry
- evidence references
- last durable update timestamp

Existing closure ledgers remain authoritative for their current task unless deliberately migrated. Do not rename or replace existing closure files merely to adopt this protocol.

## Locking

A lock is task/path scoped and prevents concurrent automations from mutating overlapping authorities or files.

Before mutation, an execution worker MUST:

1. inspect active PRs and task state;
2. compare intended changed paths with active work;
3. refuse parallel overlapping writes when a live non-expired lock or authoritative overlapping PR exists;
4. use non-overlapping dependency-ready work instead, or wait for the next run.

A stale lock may be reclaimed only after proving its owner is no longer actively mutating the same scope and recording the reason.

## Repair loop

Repository-owned deterministic failures MUST use:

`FAIL -> evidence -> root-cause classification -> minimal repair -> regression coverage when justified -> retest -> exact-head CI`

Rules:

- never weaken tests, thresholds, governance, or security for green CI;
- never retry the same unchanged failure blindly;
- increment `retry_count` only for a materially new repair/retry attempt;
- record a failure fingerprint so repeated identical failures are detectable;
- classify external/provider/human-only blockers separately from repository-owned failures;
- if one dependency is externally blocked, continue safe independent work where allowed.

## Evidence and maturity

Maturity remains:

`DESIGNED -> SPECIFIED -> IMPLEMENTED -> TESTED -> VERIFIED -> DEPLOYED/PRODUCTION`

No phase promotion without matching evidence.

Minimum source-development lineage:

`source/task -> base SHA -> branch/head SHA -> tests -> exact-head CI -> PR -> merge SHA -> exact-master CI`

Where applicable, extend with:

`runtime/provider/device/package/deployment -> E2E -> artifact/receipt -> evidence chain`

`CI PASS` is not equivalent to production verification.

## Human-only gates

Examples include CAPTCHA, account/legal acceptance, identity verification, payment/billing approval, OAuth/Store console actions that cannot be safely performed through authorized tooling, and third-party manual review.

Before declaring `HUMAN_BLOCKED`, complete all safe independent repository work and record the exact unmet condition and next human action.

## Timeout/resume

A ChatGPT/session timeout MUST NOT cause completed work to be repeated.

On every resume:

1. read the task state and authoritative task ledger;
2. re-read live GitHub truth;
3. invalidate stale SHA/CI assumptions;
4. resume only the incomplete atomic step.

GitHub state outranks chat history.

## Adoption rule

For future user requests of the form “use this task file, create an automation, and run it,” the automation should apply this protocol automatically unless the user explicitly disables it for that task.

The user-supplied task file remains the task source. This protocol is infrastructure; it does not rename, rewrite, or replace the user file.