from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.video_automation.post_publish_verification import (
    PostPublishVerificationCoordinator,
    PostPublishVerificationError,
    PublicationVerificationStatus,
)
from src.video_automation.publishing_execution import (
    PlatformPublishingObservation,
    PublishingExecutionReport,
    PublishingExecutionStatus,
)
from src.video_automation.publishing_package_preparation import (
    EpisodePublishingPackageManifest,
    PlatformPublishingPackage,
)


def _package(
    package_id: str,
    platform: str = "youtube",
    account_id: str = "channel-001",
) -> PlatformPublishingPackage:
    return PlatformPublishingPackage(
        package_id=package_id,
        episode_id="episode-001",
        artifact_id="artifact-001",
        acceptance_decision_id="acceptance-001",
        platform=platform,
        account_id=account_id,
        media_path="C:/media/episode.mp4",
        media_sha256_hex="a" * 64,
        media_byte_length=1234,
        scheduled_at=datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc),
        visibility="public",
        title="Episode 001",
        description="Description",
        tags=("shorts",),
        metadata={},
    )


def _manifest(
    packages: tuple[PlatformPublishingPackage, ...],
) -> EpisodePublishingPackageManifest:
    return EpisodePublishingPackageManifest(
        manifest_id="publishing-manifest-001",
        episode_id="episode-001",
        artifact_id="artifact-001",
        acceptance_decision_id="acceptance-001",
        packages=packages,
        package_count=len(packages),
        metadata={},
    )


def _success(
    package: PlatformPublishingPackage,
) -> PlatformPublishingObservation:
    return PlatformPublishingObservation(
        package_id=package.package_id,
        platform=package.platform,
        account_id=package.account_id,
        status=PublishingExecutionStatus.SUCCEEDED,
        provider_name=f"{package.platform}-provider",
        platform_post_id=f"post-{package.package_id}",
        published_url=f"https://example.test/{package.package_id}",
    )


def _failure(
    package: PlatformPublishingPackage,
) -> PlatformPublishingObservation:
    return PlatformPublishingObservation(
        package_id=package.package_id,
        platform=package.platform,
        account_id=package.account_id,
        status=PublishingExecutionStatus.FAILED,
        provider_name=f"{package.platform}-provider",
        error_code="publish_failed",
        error_message="provider publish failed",
    )


def _report(
    manifest: EpisodePublishingPackageManifest,
    observations: tuple[PlatformPublishingObservation, ...],
) -> PublishingExecutionReport:
    succeeded = sum(
        item.status is PublishingExecutionStatus.SUCCEEDED
        for item in observations
    )
    return PublishingExecutionReport(
        report_id="publishing-execution-report-001",
        manifest_id=manifest.manifest_id,
        episode_id=manifest.episode_id,
        observations=observations,
        package_count=len(observations),
        succeeded_count=succeeded,
        failed_count=len(observations) - succeeded,
        metadata={},
    )


def test_verifies_successful_publication() -> None:
    package = _package("package-001")
    manifest = _manifest((package,))
    result = PostPublishVerificationCoordinator().verify(
        manifest,
        _report(manifest, (_success(package),)),
    )
    assert result.all_verified is True
    assert result.verified_count == 1
    assert result.failed_count == 0
    assert result.evidence[0].status is PublicationVerificationStatus.VERIFIED


def test_records_failed_publication() -> None:
    package = _package("package-001")
    manifest = _manifest((package,))
    result = PostPublishVerificationCoordinator().verify(
        manifest,
        _report(manifest, (_failure(package),)),
    )
    assert result.all_verified is False
    assert result.verified_count == 0
    assert result.failed_count == 1
    assert result.evidence[0].status is PublicationVerificationStatus.FAILED


def test_mixed_execution_is_normalized() -> None:
    youtube = _package("youtube-package", "youtube", "channel-001")
    tiktok = _package("tiktok-package", "tiktok", "account-001")
    manifest = _manifest((youtube, tiktok))
    result = PostPublishVerificationCoordinator().verify(
        manifest,
        _report(manifest, (_success(youtube), _failure(tiktok))),
    )
    assert result.publication_count == 2
    assert result.verified_count == 1
    assert result.failed_count == 1


def test_verification_is_deterministic() -> None:
    package = _package("package-001")
    manifest = _manifest((package,))
    report = _report(manifest, (_success(package),))
    coordinator = PostPublishVerificationCoordinator()
    first = coordinator.verify(manifest, report)
    second = coordinator.verify(manifest, report)
    assert first.manifest_id == second.manifest_id
    assert first.evidence[0].verification_id == second.evidence[0].verification_id


def test_evidence_is_sorted_by_package_id() -> None:
    second = _package("package-b", "youtube", "channel-b")
    first = _package("package-a", "tiktok", "account-a")
    manifest = _manifest((second, first))
    result = PostPublishVerificationCoordinator().verify(
        manifest,
        _report(manifest, (_success(second), _success(first))),
    )
    assert tuple(item.package_id for item in result.evidence) == (
        "package-a",
        "package-b",
    )


def test_manifest_identity_must_match() -> None:
    package = _package("package-001")
    manifest = _manifest((package,))
    report = _report(manifest, (_success(package),))
    object.__setattr__(report, "manifest_id", "other-manifest")
    with pytest.raises(PostPublishVerificationError, match="manifest_id"):
        PostPublishVerificationCoordinator().verify(manifest, report)


def test_episode_identity_must_match() -> None:
    package = _package("package-001")
    manifest = _manifest((package,))
    report = _report(manifest, (_success(package),))
    object.__setattr__(report, "episode_id", "episode-other")
    with pytest.raises(PostPublishVerificationError, match="episode_id"):
        PostPublishVerificationCoordinator().verify(manifest, report)


def test_package_count_must_match() -> None:
    package = _package("package-001")
    manifest = _manifest((package,))
    report = _report(manifest, (_success(package),))
    object.__setattr__(report, "package_count", 2)
    with pytest.raises(PostPublishVerificationError, match="package_count"):
        PostPublishVerificationCoordinator().verify(manifest, report)


def test_missing_observation_is_rejected() -> None:
    first = _package("package-a")
    second = _package("package-b", "tiktok", "account-b")
    manifest = _manifest((first, second))
    report = _report(manifest, (_success(first),))
    object.__setattr__(report, "package_count", 2)
    with pytest.raises(PostPublishVerificationError, match="mismatch"):
        PostPublishVerificationCoordinator().verify(manifest, report)


def test_extra_observation_is_rejected() -> None:
    package = _package("package-a")
    extra = _package("package-extra", "tiktok", "account-extra")
    manifest = _manifest((package,))
    observations = (_success(package), _success(extra))
    report = _report(manifest, observations)
    object.__setattr__(report, "package_count", 1)
    with pytest.raises(PostPublishVerificationError, match="mismatch"):
        PostPublishVerificationCoordinator().verify(manifest, report)


def test_duplicate_observation_is_rejected() -> None:
    package = _package("package-001")
    manifest = _manifest((package,))
    observation = _success(package)
    report = _report(manifest, (observation, observation))
    object.__setattr__(report, "package_count", 1)
    with pytest.raises(PostPublishVerificationError, match="duplicate"):
        PostPublishVerificationCoordinator().verify(manifest, report)


def test_platform_must_match_package() -> None:
    package = _package("package-001")
    manifest = _manifest((package,))
    observation = _success(package)
    object.__setattr__(observation, "platform", "tiktok")
    with pytest.raises(PostPublishVerificationError, match="platform mismatch"):
        PostPublishVerificationCoordinator().verify(
            manifest,
            _report(manifest, (observation,)),
        )


def test_account_must_match_package() -> None:
    package = _package("package-001")
    manifest = _manifest((package,))
    observation = _success(package)
    object.__setattr__(observation, "account_id", "other-account")
    with pytest.raises(PostPublishVerificationError, match="account_id mismatch"):
        PostPublishVerificationCoordinator().verify(
            manifest,
            _report(manifest, (observation,)),
        )


def test_verified_evidence_preserves_publication_identifiers() -> None:
    package = _package("package-001")
    manifest = _manifest((package,))
    result = PostPublishVerificationCoordinator().verify(
        manifest,
        _report(manifest, (_success(package),)),
    )
    item = result.evidence[0]
    assert item.platform_post_id == "post-package-001"
    assert item.published_url == "https://example.test/package-001"


def test_failed_evidence_preserves_error() -> None:
    package = _package("package-001")
    manifest = _manifest((package,))
    result = PostPublishVerificationCoordinator().verify(
        manifest,
        _report(manifest, (_failure(package),)),
    )
    item = result.evidence[0]
    assert item.error_code == "publish_failed"
    assert item.error_message == "provider publish failed"


def test_manifest_metadata_is_immutable() -> None:
    package = _package("package-001")
    manifest = _manifest((package,))
    result = PostPublishVerificationCoordinator().verify(
        manifest,
        _report(manifest, (_success(package),)),
    )
    with pytest.raises(TypeError):
        result.metadata["x"] = "y"  # type: ignore[index]


def test_evidence_metadata_is_immutable() -> None:
    package = _package("package-001")
    manifest = _manifest((package,))
    result = PostPublishVerificationCoordinator().verify(
        manifest,
        _report(manifest, (_success(package),)),
    )
    with pytest.raises(TypeError):
        result.evidence[0].metadata["x"] = "y"  # type: ignore[index]
