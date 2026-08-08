from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.video_automation.models import PublishJob, ValidationResult
from src.video_automation.publishing_queue import PublishingQueue, PublishingQueueError


def _job(job_id: str, scheduled_at: datetime) -> PublishJob:
    return PublishJob(
        publish_job_id=job_id,
        job_id="video-1",
        platform="youtube",
        account_id="acct-1",
        artifact_id="artifact-1",
        scheduled_at=scheduled_at,
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
