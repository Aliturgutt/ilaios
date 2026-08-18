"""Deterministic scheduler complexity characterization for ILAIOS.

This is an audit utility, not a production runtime dependency. It avoids wall-clock
thresholds and records structural work performed by WorkerScheduler._active_count.
The output can be compared before and after a candidate optimization without
changing scheduler semantics.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from types import MethodType

from services.runtime.scheduler import WorkerProfile, WorkerScheduler


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    workers: int
    seeded_leases: int
    active_count_calls: int
    lease_items_scanned: int
    selected_worker: str


def characterize(*, workers: int, seeded_leases: int) -> ScenarioResult:
    if workers < 1:
        raise ValueError("workers must be positive")
    if seeded_leases < 0:
        raise ValueError("seeded_leases cannot be negative")
    if seeded_leases > workers:
        raise ValueError("seeded_leases cannot exceed workers")

    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    scheduler = WorkerScheduler(lease_duration=timedelta(minutes=5))
    for index in range(workers):
        scheduler.register(
            WorkerProfile(
                worker_id=f"worker-{index:06d}",
                capabilities=frozenset({"audit"}),
                max_concurrent_tasks=2,
            )
        )

    for index in range(seeded_leases):
        scheduler.schedule(f"seed-{index:06d}", "audit", now=now)

    active_count_calls = 0
    lease_items_scanned = 0
    original = scheduler._active_count

    def counted_active_count(self: WorkerScheduler, worker_id: str, at: datetime) -> int:
        nonlocal active_count_calls, lease_items_scanned
        active_count_calls += 1
        lease_items_scanned += len(self._leases)
        return original(worker_id, at)

    scheduler._active_count = MethodType(counted_active_count, scheduler)  # type: ignore[method-assign]
    lease = scheduler.schedule("audit-target", "audit", now=now)

    return ScenarioResult(
        workers=workers,
        seeded_leases=seeded_leases,
        active_count_calls=active_count_calls,
        lease_items_scanned=lease_items_scanned,
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
