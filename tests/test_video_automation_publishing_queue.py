from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.video_automation.models import PublishJob, ValidationResult
from src.video_automation.publishing_queue import (
    PublishingDispatchResult,
    PublishingQueue,
    PublishingQueueError,
    PublishJobDispatcher,
)


def _job(job_id: str, scheduled_at: datetime) -> PublishJob:
    return PublishJob(
        publish_job_id=job_id,
        job_id="video-1",
        platform="youtube",
        account_id="acct-1",
        artifact_id="artifact-1",
        scheduled_at=scheduled_at,
    )


class RecordingDispatcher(PublishJobDispatcher):
    def __init__(self, *, accepted: bool = True) -> None:
        self.accepted = accepted
        self.dispatched_ids: list[str] = []

    def dispatch(self, job: PublishJob) -> PublishingDispatchResult:
        self.dispatched_ids.append(job.publish_job_id)
        if self.accepted:
            return PublishingDispatchResult(
                publish_job_id=job.publish_job_id,
                accepted=True,
                dispatch_reference=f"dispatch:{job.publish_job_id}",
            )
        return PublishingDispatchResult(
            publish_job_id=job.publish_job_id,
            accepted=False,
            error_message="temporary dispatch failure",
        )


def test_queue_rejects_unvalidated_publish_job() -> None:
    queue = PublishingQueue()
    with pytest.raises(PublishingQueueError, match="passed validation"):
        queue.enqueue(
            _job("p1", datetime.now(timezone.utc)),
            ValidationResult("content", False, ("failed",)),
        )


def test_ready_returns_only_due_validated_jobs_in_stable_order() -> None:
    queue = PublishingQueue()
    now = datetime.now(timezone.utc)
    passed = ValidationResult("content", True)
    queue.enqueue(_job("later", now + timedelta(minutes=1)), passed)
    queue.enqueue(_job("ready-b", now), passed)
    queue.enqueue(_job("ready-a", now), passed)
    assert [item.job.publish_job_id for item in queue.ready(now)] == [
        "ready-a",
        "ready-b",
    ]


def test_duplicate_publish_job_id_fails_closed() -> None:
    queue = PublishingQueue()
    now = datetime.now(timezone.utc)
    passed = ValidationResult("content", True)
    queue.enqueue(_job("same", now), passed)
    with pytest.raises(PublishingQueueError, match="unique"):
        queue.enqueue(_job("same", now), passed)


def test_dispatch_ready_dispatches_only_due_jobs_and_removes_accepted() -> None:
    queue = PublishingQueue()
    now = datetime.now(timezone.utc)
    passed = ValidationResult("content", True)
    queue.enqueue(_job("later", now + timedelta(minutes=1)), passed)
    queue.enqueue(_job("ready-b", now), passed)
    queue.enqueue(_job("ready-a", now), passed)
    dispatcher = RecordingDispatcher()

    results = queue.dispatch_ready(now, dispatcher)

    assert dispatcher.dispatched_ids == ["ready-a", "ready-b"]
    assert [result.publish_job_id for result in results] == [
        "ready-a",
        "ready-b",
    ]
    assert [item.job.publish_job_id for item in queue.snapshot()] == ["later"]


def test_rejected_dispatch_remains_queued_for_retry_policy() -> None:
    queue = PublishingQueue()
    now = datetime.now(timezone.utc)
    queue.enqueue(
        _job("ready", now),
        ValidationResult("content", True),
    )
    dispatcher = RecordingDispatcher(accepted=False)

    results = queue.dispatch_ready(now, dispatcher)

    assert results[0].accepted is False
    assert [item.job.publish_job_id for item in queue.snapshot()] == ["ready"]


def test_dispatch_result_must_match_queued_job() -> None:
    class MismatchedDispatcher:
        def dispatch(self, job: PublishJob) -> PublishingDispatchResult:
            return PublishingDispatchResult(
                publish_job_id="different",
                accepted=True,
                dispatch_reference="dispatch:different",
            )

    queue = PublishingQueue()
    now = datetime.now(timezone.utc)
    queue.enqueue(
        _job("ready", now),
        ValidationResult("content", True),
    )

    with pytest.raises(PublishingQueueError, match="does not match"):
        queue.dispatch_ready(now, MismatchedDispatcher())

    assert [item.job.publish_job_id for item in queue.snapshot()] == ["ready"]
