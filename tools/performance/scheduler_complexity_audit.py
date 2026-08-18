"""Deterministic scheduler complexity characterization for ILAIOS.

This is an audit utility, not a production runtime dependency. It avoids wall-clock
thresholds and records structural lease scans performed while WorkerScheduler
selects a worker. The output can be compared before and after a candidate
optimization without changing scheduler semantics.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from services.runtime.scheduler import Lease, WorkerProfile, WorkerScheduler


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    workers: int
    seeded_leases: int
    active_count_calls: int
    bulk_active_count_calls: int
    lease_items_scanned: int
    selected_worker: str


class AuditWorkerScheduler(WorkerScheduler):
    """Instrumented scheduler used only by the audit command."""

    def __init__(self, *, lease_duration: timedelta) -> None:
        super().__init__(lease_duration=lease_duration)
        self.active_count_calls = 0
        self.bulk_active_count_calls = 0
        self.lease_items_scanned = 0

    def _active_counts(self, now: datetime) -> dict[str, int]:
        self.bulk_active_count_calls += 1
        self.lease_items_scanned += len(self._leases)
        return super()._active_counts(now)

    def _active_count(self, worker_id: str, now: datetime) -> int:
        self.active_count_calls += 1
        self.lease_items_scanned += len(self._leases)
        return super()._active_count(worker_id, now)


def characterize(*, workers: int, seeded_leases: int) -> ScenarioResult:
    if workers < 1:
        raise ValueError("workers must be positive")
    if seeded_leases < 0:
        raise ValueError("seeded_leases cannot be negative")
    if seeded_leases > workers:
        raise ValueError("seeded_leases cannot exceed workers")

    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    scheduler = AuditWorkerScheduler(lease_duration=timedelta(minutes=5))
    for index in range(workers):
        scheduler.register(
            WorkerProfile(
                worker_id=f"worker-{index:06d}",
                capabilities=frozenset({"audit"}),
                max_concurrent_tasks=2,
            )
        )

    # Seed the fixture directly so setup cost does not contaminate the target
    # schedule operation. Each seeded worker has one active lease and remains
    # below its quota of two concurrent tasks.
    for index in range(seeded_leases):
        task_id = f"seed-{index:06d}"
        scheduler._leases[task_id] = Lease(
            task_id=task_id,
            worker_id=f"worker-{index:06d}",
            fencing_token=1,
            expires_at=now + timedelta(minutes=5),
        )

    scheduler.active_count_calls = 0
    scheduler.bulk_active_count_calls = 0
    scheduler.lease_items_scanned = 0
    lease = scheduler.schedule("audit-target", "audit", now=now)

    return ScenarioResult(
        workers=workers,
        seeded_leases=seeded_leases,
        active_count_calls=scheduler.active_count_calls,
        bulk_active_count_calls=scheduler.bulk_active_count_calls,
        lease_items_scanned=scheduler.lease_items_scanned,
        selected_worker=lease.worker_id,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        action="append",
        default=[],
        metavar="WORKERS:LEASES",
        help="repeatable scenario, for example 100:100",
    )
    args = parser.parse_args()

    raw_scenarios = args.scenario or ["10:10", "100:100", "1000:1000"]
    results: list[ScenarioResult] = []
    for raw in raw_scenarios:
        workers_text, leases_text = raw.split(":", maxsplit=1)
        results.append(
            characterize(workers=int(workers_text), seeded_leases=int(leases_text))
        )

    print(json.dumps([asdict(item) for item in results], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
