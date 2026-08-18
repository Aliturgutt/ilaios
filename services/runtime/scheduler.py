"""Worker scheduling with quotas, leases, heartbeats, and fencing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


class SchedulingError(PermissionError):
    """Raised when scheduling or side-effect authorization fails closed."""


@dataclass(frozen=True, slots=True)
class WorkerProfile:
    worker_id: str
    capabilities: frozenset[str]
    max_concurrent_tasks: int

    def __post_init__(self) -> None:
        if self.max_concurrent_tasks < 1:
            raise SchedulingError("worker quota must be positive")


@dataclass(frozen=True, slots=True)
class Lease:
    task_id: str
    worker_id: str
    fencing_token: int
    expires_at: datetime


class WorkerScheduler:
    """Deterministic scheduler whose fencing tokens invalidate stale workers."""

    def __init__(self, *, lease_duration: timedelta) -> None:
        if lease_duration <= timedelta(0):
            raise SchedulingError("lease_duration must be positive")
        self._lease_duration = lease_duration
        self._workers: dict[str, WorkerProfile] = {}
        self._leases: dict[str, Lease] = {}
        self._next_fence: dict[str, int] = {}

    def register(self, profile: WorkerProfile) -> None:
        self._workers[profile.worker_id] = profile

    def schedule(
        self, task_id: str, capability: str, *, now: datetime
    ) -> Lease:
        existing = self._leases.get(task_id)
        if existing is not None and existing.expires_at > now:
            raise SchedulingError("task already has an active lease")

        active_counts = self._active_counts(now)
        selected = min(
            (
                worker
                for worker in self._workers.values()
                if capability in worker.capabilities
                and active_counts.get(worker.worker_id, 0)
                < worker.max_concurrent_tasks
            ),
            key=lambda worker: (
                active_counts.get(worker.worker_id, 0),
                worker.worker_id,
            ),
            default=None,
        )
        if selected is None:
            raise SchedulingError("no worker is within capability and quota")

        fence = self._next_fence.get(task_id, 0) + 1
        self._next_fence[task_id] = fence
        lease = Lease(
            task_id,
            selected.worker_id,
            fence,
            now + self._lease_duration,
        )
        self._leases[task_id] = lease
        return lease

    def heartbeat(self, lease: Lease, *, now: datetime) -> Lease:
        self.authorize_side_effect(lease, now=now)
        renewed = Lease(
            lease.task_id,
            lease.worker_id,
            lease.fencing_token,
            now + self._lease_duration,
        )
        self._leases[lease.task_id] = renewed
        return renewed

    def authorize_side_effect(self, lease: Lease, *, now: datetime) -> None:
        current = self._leases.get(lease.task_id)
        if current != lease:
            raise SchedulingError("stale or replaced fencing token")
        if current.expires_at <= now:
            raise SchedulingError("lease expired")

    def complete(self, lease: Lease, *, now: datetime) -> None:
        self.authorize_side_effect(lease, now=now)
        del self._leases[lease.task_id]

    def reschedule_expired(
        self, task_id: str, capability: str, *, now: datetime
    ) -> Lease:
        current = self._leases.get(task_id)
        if current is None or current.expires_at > now:
            raise SchedulingError("task lease is not expired")
        return self.schedule(task_id, capability, now=now)

    def _active_counts(self, now: datetime) -> dict[str, int]:
        counts: dict[str, int] = {}
        for lease in self._leases.values():
            if lease.expires_at <= now:
                continue
            counts[lease.worker_id] = counts.get(lease.worker_id, 0) + 1
        return counts

    def _active_count(self, worker_id: str, now: datetime) -> int:
        return sum(
            lease.worker_id == worker_id and lease.expires_at > now
            for lease in self._leases.values()
        )
