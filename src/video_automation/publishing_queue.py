"""Canonical M25 scheduler and publishing queue."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .models import PublishJob, ValidationResult


class PublishingQueueError(ValueError):
    """Raised when an invalid publishing queue operation is requested."""


@dataclass(frozen=True, slots=True)
class QueuedPublishJob:
    """Validated publish job waiting for its scheduling condition."""

    job: PublishJob
    validation: ValidationResult

    def __post_init__(self) -> None:
        if not self.validation.passed:
            raise PublishingQueueError("publish job requires passed validation")


@dataclass(frozen=True, slots=True)
class PublishingDispatchResult:
    """Normalized evidence that one queued job was dispatched."""

    publish_job_id: str
    accepted: bool
    dispatch_reference: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not self.publish_job_id.strip():
            raise PublishingQueueError("publish_job_id must not be blank")
        if self.accepted:
            if self.dispatch_reference is None or not self.dispatch_reference.strip():
                raise PublishingQueueError(
                    "accepted dispatch requires dispatch_reference"
                )
            if self.error_message is not None:
                raise PublishingQueueError(
                    "accepted dispatch must not contain error_message"
                )
        elif self.error_message is None or not self.error_message.strip():
            raise PublishingQueueError(
                "rejected dispatch requires error_message"
            )


class PublishJobDispatcher(Protocol):
    """Provider-independent boundary that accepts one due publish job."""

    def dispatch(self, job: PublishJob) -> PublishingDispatchResult:
        """Dispatch one job to the publishing execution layer."""


class PublishingQueue:
    """Deterministic scheduler for validated job-based publishing."""

    def __init__(self) -> None:
        self._jobs: dict[str, QueuedPublishJob] = {}

    def enqueue(self, job: PublishJob, validation: ValidationResult) -> None:
        """Queue a validated publish job exactly once."""

        if not validation.passed:
            raise PublishingQueueError("publishing requires passed validation")
        if job.publish_job_id in self._jobs:
            raise PublishingQueueError("publish_job_id must be unique")
        self._jobs[job.publish_job_id] = QueuedPublishJob(job, validation)

    def ready(self, now: datetime) -> tuple[QueuedPublishJob, ...]:
        """Return due validated jobs in deterministic scheduling order."""

        if now.tzinfo is None:
            raise PublishingQueueError("now must be timezone-aware")
        ready = [
            item
            for item in self._jobs.values()
            if item.job.scheduled_at <= now
        ]
        return tuple(
            sorted(
                ready,
                key=lambda item: (
                    item.job.scheduled_at,
                    item.job.publish_job_id,
                ),
            )
        )

    def dispatch_ready(
        self,
        now: datetime,
        dispatcher: PublishJobDispatcher,
    ) -> tuple[PublishingDispatchResult, ...]:
        """Dispatch every due validated job once and return dispatch evidence.

        Accepted jobs are removed from the queue. Rejected jobs remain queued so
        later retry/recovery policy can decide whether another dispatch attempt
        is allowed; M25 itself does not implement retry policy.
        """

        results: list[PublishingDispatchResult] = []
        for queued in self.ready(now):
            result = dispatcher.dispatch(queued.job)
            if result.publish_job_id != queued.job.publish_job_id:
                raise PublishingQueueError(
                    "dispatcher result publish_job_id does not match queued job"
                )
            results.append(result)
            if result.accepted:
                self.remove(queued.job.publish_job_id)
        return tuple(results)

    def remove(self, publish_job_id: str) -> QueuedPublishJob:
        """Remove one queued job by identifier."""

        try:
            return self._jobs.pop(publish_job_id)
        except KeyError as exc:
            raise PublishingQueueError("unknown publish_job_id") from exc

    def snapshot(self) -> tuple[QueuedPublishJob, ...]:
        """Return a stable snapshot of the current queue."""

        return tuple(self._jobs[key] for key in sorted(self._jobs))
