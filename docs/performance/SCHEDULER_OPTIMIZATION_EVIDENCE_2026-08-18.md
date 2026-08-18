# Scheduler Optimization Evidence — 2026-08-18

## Scope

This evidence covers only `services/runtime/scheduler.py` worker selection. It does not change policy, approval, authorization, fencing-token semantics, evidence integrity, database schema, API contracts, or Desktop behavior.

## Baseline hotspot

Before this change, `WorkerScheduler.schedule()` evaluated `_active_count()` while filtering workers and again while sorting eligible workers. `_active_count()` scans every lease. With `W` workers and `L` leases, the structural lease-scan work therefore grew approximately as `O(W * L)`, with sorting also adding worker-ordering work.

The deterministic structural audit produced these baseline results from the pre-change scheduler:

| Workers | Seeded leases | `_active_count` calls | Lease items scanned | Selected worker |
| ---: | ---: | ---: | ---: | --- |
| 10 | 10 | 20 | 200 | `worker-000000` |
| 100 | 100 | 200 | 20,000 | `worker-000000` |
| 1,000 | 1,000 | 2,000 | 2,000,000 | `worker-000000` |

## Candidate optimization

The candidate performs one pass over leases to build active counts and then performs one linear `min()` selection over eligible workers using the same deterministic key:

`(active_count, worker_id)`

This removes repeated full lease scans and removes the need to sort the full eligible set.

Expected structural complexity of the selection path becomes `O(L + W)` with an `O(min(L, W))` active-count map in the representative case.

## After characterization

Running the same deterministic structural scenarios against the candidate produced:

| Workers | Seeded leases | Per-worker count calls | Bulk count passes | Lease items scanned | Selected worker |
| ---: | ---: | ---: | ---: | ---: | --- |
| 10 | 10 | 0 | 1 | 10 | `worker-000000` |
| 100 | 100 | 0 | 1 | 100 | `worker-000000` |
| 1,000 | 1,000 | 0 | 1 | 1,000 | `worker-000000` |

For the 1,000-worker / 1,000-lease scenario, the structural lease items scanned fall from 2,000,000 to 1,000, a 99.95% reduction in this measured scan-work proxy while preserving the selected worker.

## Correctness locks

The change must retain all existing scheduler tests and additionally locks:

- deterministic worker selection;
- quota enforcement;
- expired leases excluded from load selection;
- heartbeat behavior;
- stale fencing-token rejection;
- safe rescheduling after expiry;
- one structural active-lease scan in the characterization path.

## Red-team stop conditions

Do not merge if any of these occur:

- required CI gate fails;
- deterministic worker selection differs under equivalent state;
- quota behavior changes;
- expired leases count as active;
- fencing-token behavior changes;
- the structural audit performs more than one full active-lease aggregation pass for one schedule operation;
- unrelated runtime or governance files are changed.

## Rollback

The optimization is isolated to a dedicated PR. Reverting that PR restores the prior scheduler selection implementation without schema or data migration.
