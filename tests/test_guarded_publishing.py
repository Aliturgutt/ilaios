from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

import pytest

from src.video_automation.finished_product import FinishedVideoProduct
from src.video_automation.guarded_publishing import (
    DurablePublishingCoordinator,
    GuardedPublishingError,
    PublicationAuthorization,
)
from src.video_automation.publication_ledger import (
    PublicationLedgerError,
    PublicationSideEffectLedger,
    PublicationState,
)
from src.video_automation.publication_observability import (
    PublicationAlertSeverity,
    PublicationOperationsProjector,
    PublicationRecoveryAction,
)
from src.video_automation.publishing_execution import (
    PlatformPublishingObservation,
    PublishingExecutionStatus,
)
from src.video_automation.publishing_package_preparation import PlatformPublishingPackage


class _Publisher:
    def __init__(
        self,
        *,
        platform: str = "youtube",
        account_id: str = "youtube-account-001",
        oauth_authorization_ref: str = "oauth://youtube/account-001",
        required_oauth_scopes: tuple[str, ...] = ("video.upload",),
        observation_status: PublishingExecutionStatus = PublishingExecutionStatus.SUCCEEDED,
        error: Exception | None = None,
        conflicting_package_id: str | None = None,
    ) -> None:
        self._platform = platform
        self._account_id = account_id
        self._oauth_authorization_ref = oauth_authorization_ref
        self._required_oauth_scopes = required_oauth_scopes
        self._observation_status = observation_status
        self._error = error
        self._conflicting_package_id = conflicting_package_id
        self.calls = 0

    @property
    def publisher_id(self) -> str:
        return "test-publisher"

    @property
    def platform(self) -> str:
        return self._platform

    @property
    def account_id(self) -> str:
        return self._account_id

    @property
    def oauth_authorization_ref(self) -> str:
        return self._oauth_authorization_ref

    @property
    def required_oauth_scopes(self) -> tuple[str, ...]:
        return self._required_oauth_scopes

    def publish(self, package: PlatformPublishingPackage) -> PlatformPublishingObservation:
        self.calls += 1
        if self._error is not None:
            raise self._error
        package_id = self._conflicting_package_id or package.package_id
        if self._observation_status is PublishingExecutionStatus.SUCCEEDED:
            return PlatformPublishingObservation(
                package_id=package_id,
                platform=package.platform,
                account_id=package.account_id,
                status=PublishingExecutionStatus.SUCCEEDED,
                provider_name="test-provider",
                platform_post_id="post-001",
                published_url="https://example.invalid/post-001",
            )
        return PlatformPublishingObservation(
            package_id=package_id,
            platform=package.platform,
            account_id=package.account_id,
            status=PublishingExecutionStatus.FAILED,
            provider_name="test-provider",
            error_code="oauth_expired",
            error_message="OAuth authorization expired",
        )


def _product(tmp_path: Path) -> FinishedVideoProduct:
    final_path = tmp_path / "final.mp4"
    final_path.write_bytes(b"verified-final-video")
    digest = sha256(final_path.read_bytes()).hexdigest()
    return FinishedVideoProduct(
        product_id="finished-video-001",
        job_id="episode-001",
        final_path=str(final_path),
        final_sha256=digest,
        byte_length=final_path.stat().st_size,
        acceptance_id="media-acceptance-001",
        encoding_evidence_ref="evidence://encoding/001",
        audio_mix_evidence_ref="evidence://audio/001",
        caption_manifest_sha256=None,
        thumbnail_sha256=None,
        title="Episode title",
        description="Episode description",
    )


def _package(product: FinishedVideoProduct) -> PlatformPublishingPackage:
    return PlatformPublishingPackage(
        package_id="publishing-package-001",
        episode_id="episode-001",
        artifact_id="artifact-001",
        acceptance_decision_id="acceptance-001",
        platform="youtube",
        account_id="youtube-account-001",
        media_path=product.final_path,
        media_sha256_hex=product.final_sha256,
        media_byte_length=product.byte_length,
        scheduled_at=datetime(2026, 8, 14, 18, 0, tzinfo=timezone.utc),
        visibility="private",
        title=product.title,
        description=product.description,
        tags=("ilaios",),
    )


def _authorization(
    *,
    platform: str = "youtube",
    account_id: str = "youtube-account-001",
    scopes: tuple[str, ...] = ("video.upload",),
) -> PublicationAuthorization:
    return PublicationAuthorization(
        platform=platform,
        account_id=account_id,
        oauth_authorization_ref="oauth://youtube/account-001",
        scopes=scopes,
    )


def test_oauth_account_mismatch_blocks_before_any_publication_side_effect(
    tmp_path: Path,
) -> None:
    product = _product(tmp_path)
    package = _package(product)
    ledger = PublicationSideEffectLedger(tmp_path / "ledger")
    publisher = _Publisher()

    with pytest.raises(GuardedPublishingError, match="account does not match"):
        DurablePublishingCoordinator(ledger).publish(
            package=package,
            product=product,
            authorization=_authorization(account_id="different-account"),
            publisher=publisher,
        )

    assert publisher.calls == 0
    with pytest.raises(PublicationLedgerError, match="does not exist"):
        ledger.get(package.package_id)


def test_missing_required_scope_blocks_before_any_publication_side_effect(
    tmp_path: Path,
) -> None:
    product = _product(tmp_path)
    package = _package(product)
    ledger = PublicationSideEffectLedger(tmp_path / "ledger")
    publisher = _Publisher(required_oauth_scopes=("video.upload", "channel.manage"))

    with pytest.raises(GuardedPublishingError, match="missing required OAuth scopes"):
        DurablePublishingCoordinator(ledger).publish(
            package=package,
            product=product,
            authorization=_authorization(scopes=("video.upload",)),
            publisher=publisher,
        )

    assert publisher.calls == 0
    with pytest.raises(PublicationLedgerError, match="does not exist"):
        ledger.get(package.package_id)


def test_successful_publication_is_durable_and_same_package_cannot_repost(
    tmp_path: Path,
) -> None:
    product = _product(tmp_path)
    package = _package(product)
    ledger = PublicationSideEffectLedger(tmp_path / "ledger")
    publisher = _Publisher()
    coordinator = DurablePublishingCoordinator(ledger)

    result = coordinator.publish(
        package=package,
        product=product,
        authorization=_authorization(),
        publisher=publisher,
    )

    assert result.observation.status is PublishingExecutionStatus.SUCCEEDED
    assert publisher.calls == 1
    record = ledger.get(package.package_id)
    assert record.state is PublicationState.PUBLISHED
    assert record.external_post_id == "post-001"

    with pytest.raises(PublicationLedgerError, match="side-effect history"):
        coordinator.publish(
            package=package,
            product=product,
            authorization=_authorization(),
            publisher=publisher,
        )

    assert publisher.calls == 1


def test_publisher_exception_becomes_ambiguous_and_is_never_blindly_retried(
    tmp_path: Path,
) -> None:
    product = _product(tmp_path)
    package = _package(product)
    ledger = PublicationSideEffectLedger(tmp_path / "ledger")
    publisher = _Publisher(error=TimeoutError("response lost"))
    coordinator = DurablePublishingCoordinator(ledger)

    with pytest.raises(GuardedPublishingError, match="ambiguous"):
        coordinator.publish(
            package=package,
            product=product,
            authorization=_authorization(),
            publisher=publisher,
        )

    assert publisher.calls == 1
    assert ledger.get(package.package_id).state is PublicationState.AMBIGUOUS

    with pytest.raises(PublicationLedgerError, match="side-effect history"):
        coordinator.publish(
            package=package,
            product=product,
            authorization=_authorization(),
            publisher=publisher,
        )
    assert publisher.calls == 1


def test_explicit_provider_failure_is_recorded_and_not_reposted(tmp_path: Path) -> None:
    product = _product(tmp_path)
    package = _package(product)
    ledger = PublicationSideEffectLedger(tmp_path / "ledger")
    publisher = _Publisher(observation_status=PublishingExecutionStatus.FAILED)
    coordinator = DurablePublishingCoordinator(ledger)

    result = coordinator.publish(
        package=package,
        product=product,
        authorization=_authorization(),
        publisher=publisher,
    )

    assert result.observation.status is PublishingExecutionStatus.FAILED
    assert publisher.calls == 1
    assert ledger.get(package.package_id).state is PublicationState.FAILED

    with pytest.raises(PublicationLedgerError, match="side-effect history"):
        coordinator.publish(
            package=package,
            product=product,
            authorization=_authorization(),
            publisher=publisher,
        )
    assert publisher.calls == 1


def test_conflicting_response_identity_becomes_ambiguous(tmp_path: Path) -> None:
    product = _product(tmp_path)
    package = _package(product)
    ledger = PublicationSideEffectLedger(tmp_path / "ledger")
    publisher = _Publisher(conflicting_package_id="other-package")

    with pytest.raises(GuardedPublishingError, match="response identity is ambiguous"):
        DurablePublishingCoordinator(ledger).publish(
            package=package,
            product=product,
            authorization=_authorization(),
            publisher=publisher,
        )

    assert publisher.calls == 1
    assert ledger.get(package.package_id).state is PublicationState.AMBIGUOUS


def test_observability_flags_stale_submitting_without_mutation(tmp_path: Path) -> None:
    product = _product(tmp_path)
    package = _package(product)
    ledger = PublicationSideEffectLedger(tmp_path / "ledger")
    ledger.prepare(package=package, product=product)
    ledger.submitting(package.package_id)

    snapshot = PublicationOperationsProjector(ledger).snapshot(
        now=datetime.now(timezone.utc) + timedelta(hours=1),
        stale_submitting_after=timedelta(minutes=15),
    )

    assert snapshot.total == 1
    assert snapshot.submitting == 1
    assert len(snapshot.alerts) == 1
    alert = snapshot.alerts[0]
    assert alert.severity is PublicationAlertSeverity.CRITICAL
    assert alert.recommended_actions == (
        PublicationRecoveryAction.RECONCILE_PLATFORM_STATE,
    )
    assert ledger.get(package.package_id).state is PublicationState.SUBMITTING
