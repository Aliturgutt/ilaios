from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.video_automation.publication_side_effects import (
    PublicationSideEffectError,
    PublicationSideEffectLedger,
    PublicationSideEffectState,
    SafePlatformPublicationCoordinator,
)
from src.video_automation.publishing_execution import (
    PlatformPublishingObservation,
    PublishingExecutionStatus,
)
from src.video_automation.publishing_package_preparation import PlatformPublishingPackage


def _package(*, package_id: str = "publishing-package-001") -> PlatformPublishingPackage:
    return PlatformPublishingPackage(
        package_id=package_id,
        episode_id="episode-001",
        artifact_id="artifact-001",
        acceptance_decision_id="acceptance-001",
        platform="youtube",
        account_id="account-001",
        media_path="/tmp/final.mp4",
        media_sha256_hex="a" * 64,
        media_byte_length=1234,
        scheduled_at=datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc),
        visibility="public",
        title="Episode 1",
        description="Description",
        tags=("ilaios",),
    )


class _SuccessPublisher:
    publisher_id = "test.youtube"
    platform = "youtube"

    def publish(self, package: PlatformPublishingPackage) -> PlatformPublishingObservation:
        return PlatformPublishingObservation(
            package_id=package.package_id,
            platform=package.platform,
            account_id=package.account_id,
            status=PublishingExecutionStatus.SUCCEEDED,
            provider_name=self.publisher_id,
            platform_post_id="post-001",
            published_url="https://example.invalid/post-001",
        )


class _TimeoutPublisher:
    publisher_id = "test.youtube"
    platform = "youtube"

    def publish(self, package: PlatformPublishingPackage) -> PlatformPublishingObservation:
        raise TimeoutError("upstream timed out after request submission")


def test_success_is_ledgered_before_reconciliation_and_duplicate_repost_is_blocked(
    tmp_path: Path,
) -> None:
    ledger = PublicationSideEffectLedger(tmp_path)
    coordinator = SafePlatformPublicationCoordinator(ledger)
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
    package = _package()

    observation = coordinator.publish(
        package=package, publisher=_SuccessPublisher(), now=now
    )
    assert observation.status is PublishingExecutionStatus.SUCCEEDED
    accepted = ledger.get(package.package_id)
    assert accepted.state is PublicationSideEffectState.ACCEPTED
    assert accepted.artifact_sha256 == "a" * 64
    assert accepted.platform_post_id == "post-001"

    with pytest.raises(PublicationSideEffectError, match="blind repost blocked"):
        coordinator.publish(package=package, publisher=_SuccessPublisher(), now=now)

    verified = ledger.verify_existing_publication(
        package.package_id,
        platform_post_id="post-001",
        published_url="https://example.invalid/post-001",
        now=now,
    )
    assert verified.state is PublicationSideEffectState.VERIFIED


def test_timeout_becomes_ambiguous_and_same_package_cannot_be_posted_again(
    tmp_path: Path,
) -> None:
    ledger = PublicationSideEffectLedger(tmp_path)
    coordinator = SafePlatformPublicationCoordinator(ledger)
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
    package = _package()

    with pytest.raises(PublicationSideEffectError, match="ambiguous"):
        coordinator.publish(package=package, publisher=_TimeoutPublisher(), now=now)
    assert ledger.get(package.package_id).state is PublicationSideEffectState.AMBIGUOUS

    with pytest.raises(PublicationSideEffectError, match="blind repost blocked"):
        coordinator.publish(package=package, publisher=_SuccessPublisher(), now=now)


def test_publication_ledger_survives_restart(tmp_path: Path) -> None:
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
    ledger = PublicationSideEffectLedger(tmp_path)
    SafePlatformPublicationCoordinator(ledger).publish(
        package=_package(), publisher=_SuccessPublisher(), now=now
    )

    restarted = PublicationSideEffectLedger(tmp_path)
    record = restarted.get("publishing-package-001")
    assert record.state is PublicationSideEffectState.ACCEPTED
    assert record.episode_id == "episode-001"
