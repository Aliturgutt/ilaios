from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from src.video_automation.finished_product import FinishedVideoProduct
from src.video_automation.guarded_publishing import (
    DurablePublishingCoordinator,
    PublicationAuthorization,
)
from src.video_automation.publication_ledger import (
    PublicationSideEffectLedger,
    PublicationState,
)
from src.video_automation.publishing_execution import (
    PlatformPublishingObservation,
    PublishingExecutionStatus,
)
from src.video_automation.publishing_package_preparation import PlatformPublishingPackage


class _Publisher:
    calls = 0

    @property
    def publisher_id(self) -> str:
        return "recovery-test-publisher"

    @property
    def platform(self) -> str:
        return "youtube"

    @property
    def account_id(self) -> str:
        return "youtube-account"

    @property
    def oauth_authorization_ref(self) -> str:
        return "oauth://youtube/account"

    @property
    def required_oauth_scopes(self) -> tuple[str, ...]:
        return ("current-upload-scope",)

    def publish(self, package: PlatformPublishingPackage) -> PlatformPublishingObservation:
        self.calls += 1
        return PlatformPublishingObservation(
            package_id=package.package_id,
            platform=package.platform,
            account_id=package.account_id,
            status=PublishingExecutionStatus.SUCCEEDED,
            provider_name="test-provider",
            platform_post_id="post-recovered",
        )


def _fixtures(tmp_path: Path) -> tuple[FinishedVideoProduct, PlatformPublishingPackage]:
    final_path = tmp_path / "final.mp4"
    final_path.write_bytes(b"final-video")
    digest = sha256(final_path.read_bytes()).hexdigest()
    product = FinishedVideoProduct(
        product_id="finished-video-recovery",
        job_id="episode-recovery",
        final_path=str(final_path),
        final_sha256=digest,
        byte_length=final_path.stat().st_size,
        acceptance_id="media-acceptance-recovery",
        encoding_evidence_ref="evidence://encoding/recovery",
        audio_mix_evidence_ref="evidence://audio/recovery",
        caption_manifest_sha256=None,
        thumbnail_sha256=None,
        title="Recovery",
        description="Recovery test",
    )
    package = PlatformPublishingPackage(
        package_id="package-recovery",
        episode_id="episode-recovery",
        artifact_id="artifact-recovery",
        acceptance_decision_id="acceptance-recovery",
        platform="youtube",
        account_id="youtube-account",
        media_path=str(final_path),
        media_sha256_hex=digest,
        media_byte_length=final_path.stat().st_size,
        scheduled_at=datetime(2026, 8, 14, 18, 0, tzinfo=timezone.utc),
        visibility="private",
        title="Recovery",
        description="Recovery test",
        tags=(),
    )
    return product, package


def test_same_identity_can_resume_only_from_prepared_before_external_submission(
    tmp_path: Path,
) -> None:
    product, package = _fixtures(tmp_path)
    ledger = PublicationSideEffectLedger(tmp_path / "ledger")
    prepared = ledger.prepare(package=package, product=product)
    assert prepared.state is PublicationState.PREPARED

    publisher = _Publisher()
    DurablePublishingCoordinator(ledger).publish(
        package=package,
        product=product,
        authorization=PublicationAuthorization(
            platform="youtube",
            account_id="youtube-account",
            oauth_authorization_ref="oauth://youtube/account",
            scopes=("current-upload-scope",),
        ),
        publisher=publisher,
    )

    assert publisher.calls == 1
    assert ledger.get(package.package_id).state is PublicationState.PUBLISHED
