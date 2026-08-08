"""Canonical M25 scheduler and publishing queue."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import PublishJob, ValidationResult


class PublishingQueueError(ValueError):
    """Raised when an invalid or unvalidated publish job is queued."""


@dataclass(frozen=True, slots=True)
class QueuedPublishJob:
    job: PublishJob
    validation: ValidationResult

    def __post_init__(self) -> None:
        if not self.validation.passed:
            raise PublishingQueueError("publish job requires passed validation")


class PublishingQueue:
    """Job-based deterministic scheduler; it performs no platform upload itself."""

    def __init__(self) -> None:
        self._jobs: dict[str, QueuedPublishJob] = {}

    def enqueue(self, job: PublishJob, validation: ValidationResult) -> None:
        if not validation.passed:
            raise PublishingQueueError("publishing requires passed validation")
        if job.publish_job_id in self._jobs:
            raise PublishingQueueError("publish_job_id must be unique")
        self._jobs[job.publish_job_id] = QueuedPublishJob(job, validation)

    def ready(self, now: datetime) -> tuple[QueuedPublishJob, ...]:
        if now.tzinfo is None:
            raise PublishingQueueError("now must be timezone-aware")
        ready = [item for item in self._jobs.values() if item.job.scheduled_at <= now]
        return tuple(sorted(ready, key=lambda item: (item.job.scheduled_at, item.job.publish_job_id)))

    def remove(self, publish_job_id: str) -> QueuedPublishJob:
        try:
            return self._jobs.pop(publish_job_id)
        except KeyError as exc:
            raise PublishingQueueError("unknown publish_job_id") from exc

    def snapshot(self) -> tuple[QueuedPublishJob, ...]:
        return tuple(self._jobs[key] for key in sorted(self._jobs))
