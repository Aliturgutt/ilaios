# ILAIOS Fast-Closure V2 Coordination Protocol

## Purpose

Reduce master churn, stale PASS invalidation, replay/resync loops, duplicate pull requests, and repeated expensive builds without weakening required CI, governance, security, runtime, provider, device, deployment, packaging, or evidence gates.

`KANIT YOKSA TAMAMLANDI YOK.`

Fast closure means fewer repeated operations, not fewer validations.

## Scheduler staggering

The five active schedulers are intentionally staggered within each hour:

- Desktop One-ZIP Closure: minute `00`
- ILAIOS Unified Closure: minute `12`
- Identity Closure Runner: minute `24`
- Web App Factory: minute `36`
- Agent Closure: minute `48`

Temporary PR-specific schedulers must not displace one of these five persistent schedulers. A PR-specific continuation belongs to its owning persistent worker.

## Parallel development, serial merge

Workers may independently perform non-overlapping branch work, tests, CI, bounded repairs, evidence preparation, and PR preparation. Master merge is a single-writer operation coordinated through `.github/automation/fast-closure-v2-state.json`.

A worker without the merge token must not merge to master. It may continue development and prepare a merge-ready checkpoint.

## Durable merge-token states

Allowed token states:

- `AVAILABLE`
- `RESERVED`
- `PRE_MERGE_VALIDATION`
- `MERGED`
- `EXACT_MASTER_VALIDATION`
- `RELEASED`

The state records the token owner, reservation SHA, candidate PR/head when applicable, and update time. `AVAILABLE` and `RELEASED` must not retain an owner.

A token must not be held while the owner is blocked on an external or human-only dependency. Release it and allow another dependency-ready workstream to proceed.

## Durable workstream lifecycle

Allowed lifecycle states:

- `DEVELOPING`
- `CI_RUNNING`
- `MERGE_READY`
- `TOKEN_WAIT`
- `MERGING`
- `EXACT_MASTER_VERIFY`
- `BLOCKED_EXTERNAL`
- `BLOCKED_INTERNAL`
- `CLOSED`

Every worker reads its lifecycle state before mutation and updates the durable checkpoint after meaningful atomic progress.

## Dynamic priority

Priority is based on time-to-close and dependency readiness, not implementation percentage alone. Rank candidates using the remaining required gates, expected CI/runtime duration, external-blocker risk, replay cost, downstream unlock value, and current branch freshness.

A blocked high-percentage workstream may be deprioritized behind a lower-percentage workstream that can close safely now.

## Merge-freeze window

A bounded merge freeze may begin when a candidate is code-complete and most required exact-head gates have passed with only final gates pending, or when all exact-head gates have passed and immediate pre-merge live validation is next.

During the freeze, other workers continue non-overlapping branch/test/CI work but do not merge unrelated changes. The freeze ends after merge plus exact-master validation/checkpoint, or immediately if the candidate fails or becomes externally blocked.

No freeze may become an indefinite lock.

## Replay/resync rule

Do not replay/rebase merely because master moved while a candidate is still developing or waiting on CI. Continue bounded development on the candidate where safe.

Fresh replay/resync is deferred until the actual merge window, when the worker owns the token and must prove current ancestry/currentness. At that point:

1. Re-read exact live master.
2. Compare candidate base to current master.
3. Check changed-path overlap.
4. Check semantic overlap.
5. Check repository currentness/mergeability requirements.
6. If required, replay only the reviewed bounded delta on exact current master.
7. Invalidate stale PASS and run fresh exact-head gates.

Stale PASS is never merge authority.

## Closure batching

Once a worker owns the merge token, prefer completing the same bounded closure chain without unrelated master merges:

`exact-head PASS -> live master -> overlap/currentness -> expected-head merge -> exact merged SHA -> exact-master CI -> runtime/provider/device/deploy/package evidence -> durable checkpoint -> token release`

Merge alone is not VERIFIED.

## CI and artifact reuse

Required gates remain separate authorities unless repository governance explicitly changes them. Optimization must come from reuse, not gate deletion.

For expensive deterministic outputs, prefer hash-bound reuse:

`exact source SHA -> build artifact -> downstream validation/package consumers`

A downstream gate may consume a verified artifact produced for the same exact SHA instead of rebuilding the identical output, provided artifact provenance, digest, workflow trust boundary, and failure semantics remain intact. If exact-SHA provenance cannot be proven, rebuild and fail closed.

Where dependencies/caches can be safely shared across workflows, reuse them. Do not reuse artifacts across different source SHAs.

## External blockers

Once an external/human-only blocker is evidenced, mark the workstream `BLOCKED_EXTERNAL`, release the merge token, preserve the exact next action, and let another dependency-ready workstream proceed. Re-check the blocker on a later scheduler run.

## Multi-action runs

A worker is not limited to one atomic action per scheduler run. Within one bounded workstream scope and without overlapping another writer, it may safely continue through several dependent actions such as:

`root-cause -> repair -> regression test -> commit -> CI trigger/checkpoint`

Do not write to two independent workstreams in the same dedicated worker run. The Unified worker may switch lanes only after checkpointing and must not hold overlapping write locks.

## Master churn controls

Avoid empty commits, README touches, meaningless comment-only commits, retry commits, or unrelated formatting changes merely to refresh CI. Prefer supported rerun, workflow dispatch, existing successor, or durable checkpoint mechanisms.

A master commit should correspond to a real bounded change or a genuinely required certification trigger.

## Metrics

Track at least:

- master advance count
- stale-PASS invalidation count
- replay/resync count
- CI cycles per successful merge
- successful merges per workstream
- exact-head PASS to merge time
- merge to exact-master VERIFIED time
- duplicate PR count
- churn-only commit count
- external-blocker wait time

The target is fewer repeats with unchanged validation strength.

## Safety invariants

Never use Fast-Closure mode to bypass required checks, weaken tests or thresholds, bypass branch protection, force merge, rewrite history, reuse stale PASS, fabricate evidence, expose secrets, expand scope without evidence, rewrite canonical Core, bypass governance/security authorities, exceed provider budgets, publish to a Store, or perform irreversible external mutations without the required authority/approval.
