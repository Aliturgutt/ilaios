from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.video_automation.models import ProviderRequest, ProviderResult
from src.video_automation.providers import ProviderCapabilities, PublishingProvider
from src.video_automation.publishing_execution import (
    PlatformPublisherRegistry,
    PlatformPublishingObservation,
    PublishingExecutionCoordinator,
    PublishingExecutionError,
    PublishingExecutionStatus,
    PublishingProviderAdapter,
)
from src.video_automation.publishing_package_preparation import (
    EpisodePublishingPackageManifest,
    PlatformPublishingPackage,
)


class _Publisher:
    def __init__(
        self,
        platform: str,
        *,
        succeed: bool = True,
    ) -> None:
        self._platform = platform
        self._succeed = succeed
        self.calls: list[PlatformPublishingPackage] = []

    @property
    def publisher_id(self) -> str:
        return f"fake:{self._platform}"

    @property
    def platform(self) -> str:
        return self._platform

    def publish(
        self,
        package: PlatformPublishingPackage,
    ) -> PlatformPublishingObservation:
        self.calls.append(package)
        if self._succeed:
            return PlatformPublishingObservation(
                package_id=package.package_id,
                platform=package.platform,
                account_id=package.account_id,
                status=PublishingExecutionStatus.SUCCEEDED,
                provider_name=f"{package.platform}-fake",
                platform_post_id=f"post-{package.package_id}",
                published_url=f"https://example.test/{package.package_id}",
            )
        return PlatformPublishingObservation(
            package_id=package.package_id,
            platform=package.platform,
            account_id=package.account_id,
            status=PublishingExecutionStatus.FAILED,
            provider_name=f"{package.platform}-fake",
            error_code="publish_failed",
            error_message="publishing failed",
        )


class _Provider(PublishingProvider):
    def __init__(self, *, succeed: bool = True) -> None:
        super().__init__(
            ProviderCapabilities(
                provider_name="provider-alpha",
                operations=("publish",),
                is_paid=False,
            )
        )
        self.succeed = succeed
        self.requests: list[ProviderRequest] = []

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self._validate_request(request)
        self.requests.append(request)
        if self.succeed:
            return ProviderResult(
                request_id=request.request_id,
                provider_name=self.capabilities.provider_name,
                success=True,
                external_id="external-001",
                metadata={
                    "platform_post_id": "post-001",
                    "published_url": "https://example.test/post-001",
                },
            )
        return ProviderResult(
            request_id=request.request_id,
            provider_name=self.capabilities.provider_name,
            success=False,
            error_code="provider_failed",
            error_message="provider publish failed",
        )


def _package(
    platform: str = "youtube",
    account_id: str = "channel-001",
    package_id: str = "package-001",
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


def test_executes_registered_publisher(tmp_path: Path) -> None:
    del tmp_path
    publisher = _Publisher("youtube")
    registry = PlatformPublisherRegistry()
    registry.register(publisher)
    report = PublishingExecutionCoordinator(registry).execute(
        _manifest((_package(),))
    )
    assert report.package_count == 1
    assert report.succeeded_count == 1
    assert report.failed_count == 0
    assert publisher.calls == [_package()]


def test_execution_report_is_deterministic() -> None:
    registry = PlatformPublisherRegistry()
    registry.register(_Publisher("youtube"))
    coordinator = PublishingExecutionCoordinator(registry)
    manifest = _manifest((_package(),))
    first = coordinator.execute(manifest)
    second = coordinator.execute(manifest)
    assert first.report_id == second.report_id


def test_multiple_platforms_execute_in_manifest_order() -> None:
    youtube = _Publisher("youtube")
    tiktok = _Publisher("tiktok")
    registry = PlatformPublisherRegistry()
    registry.register(youtube)
    registry.register(tiktok)
    packages = (
        _package("tiktok", "account-001", "package-tiktok"),
        _package("youtube", "channel-001", "package-youtube"),
    )
    report = PublishingExecutionCoordinator(registry).execute(_manifest(packages))
    assert tuple(item.package_id for item in report.observations) == (
        "package-tiktok",
        "package-youtube",
    )


def test_failed_publish_is_recorded_not_retried() -> None:
    publisher = _Publisher("youtube", succeed=False)
    registry = PlatformPublisherRegistry()
    registry.register(publisher)
    report = PublishingExecutionCoordinator(registry).execute(
        _manifest((_package(),))
    )
    assert report.succeeded_count == 0
    assert report.failed_count == 1
    assert len(publisher.calls) == 1


def test_missing_publisher_is_rejected() -> None:
    registry = PlatformPublisherRegistry()
    with pytest.raises(PublishingExecutionError, match="no publisher"):
        PublishingExecutionCoordinator(registry).execute(
            _manifest((_package(),))
        )


def test_duplicate_platform_registration_is_rejected() -> None:
    registry = PlatformPublisherRegistry()
    registry.register(_Publisher("youtube"))
    with pytest.raises(PublishingExecutionError, match="already registered"):
        registry.register(_Publisher("YouTube"))


def test_observation_package_identity_must_match() -> None:
    class _WrongPublisher(_Publisher):
        def publish(
            self,
            package: PlatformPublishingPackage,
        ) -> PlatformPublishingObservation:
            return PlatformPublishingObservation(
                package_id="wrong-package",
                platform=package.platform,
                account_id=package.account_id,
                status=PublishingExecutionStatus.SUCCEEDED,
                provider_name="fake",
                platform_post_id="post-001",
            )

    registry = PlatformPublisherRegistry()
    registry.register(_WrongPublisher("youtube"))
    with pytest.raises(PublishingExecutionError, match="package_id mismatch"):
        PublishingExecutionCoordinator(registry).execute(
            _manifest((_package(),))
        )


def test_observation_platform_identity_must_match() -> None:
    class _WrongPublisher(_Publisher):
        def publish(
            self,
            package: PlatformPublishingPackage,
        ) -> PlatformPublishingObservation:
            return PlatformPublishingObservation(
                package_id=package.package_id,
                platform="tiktok",
                account_id=package.account_id,
                status=PublishingExecutionStatus.SUCCEEDED,
                provider_name="fake",
                platform_post_id="post-001",
            )

    registry = PlatformPublisherRegistry()
    registry.register(_WrongPublisher("youtube"))
    with pytest.raises(PublishingExecutionError, match="platform mismatch"):
        PublishingExecutionCoordinator(registry).execute(
            _manifest((_package(),))
        )


def test_observation_account_identity_must_match() -> None:
    class _WrongPublisher(_Publisher):
        def publish(
            self,
            package: PlatformPublishingPackage,
        ) -> PlatformPublishingObservation:
            return PlatformPublishingObservation(
                package_id=package.package_id,
                platform=package.platform,
                account_id="other-account",
                status=PublishingExecutionStatus.SUCCEEDED,
                provider_name="fake",
                platform_post_id="post-001",
            )

    registry = PlatformPublisherRegistry()
    registry.register(_WrongPublisher("youtube"))
    with pytest.raises(PublishingExecutionError, match="account_id mismatch"):
        PublishingExecutionCoordinator(registry).execute(
            _manifest((_package(),))
        )


def test_success_observation_requires_post_id() -> None:
    with pytest.raises(PublishingExecutionError, match="platform_post_id"):
        PlatformPublishingObservation(
            package_id="package-001",
            platform="youtube",
            account_id="channel-001",
            status=PublishingExecutionStatus.SUCCEEDED,
            provider_name="fake",
        )


def test_failed_observation_requires_error_message() -> None:
    with pytest.raises(PublishingExecutionError, match="error_message"):
        PlatformPublishingObservation(
            package_id="package-001",
            platform="youtube",
            account_id="channel-001",
            status=PublishingExecutionStatus.FAILED,
            provider_name="fake",
        )


def test_provider_adapter_builds_provider_request() -> None:
    provider = _Provider()
    adapter = PublishingProviderAdapter("youtube", provider)
    observation = adapter.publish(_package())
    assert observation.status is PublishingExecutionStatus.SUCCEEDED
    assert observation.platform_post_id == "post-001"
    assert len(provider.requests) == 1
    assert provider.requests[0].operation == "publish"
    assert provider.requests[0].payload["account_id"] == "channel-001"


def test_provider_adapter_normalizes_failure() -> None:
    provider = _Provider(succeed=False)
    observation = PublishingProviderAdapter("youtube", provider).publish(
        _package()
    )
    assert observation.status is PublishingExecutionStatus.FAILED
    assert observation.error_code == "provider_failed"
    assert observation.error_message == "provider publish failed"


def test_provider_adapter_rejects_wrong_platform() -> None:
    provider = _Provider()
    adapter = PublishingProviderAdapter("youtube", provider)
    with pytest.raises(PublishingExecutionError, match="does not match"):
        adapter.publish(_package(platform="tiktok"))


def test_report_metadata_is_immutable() -> None:
    registry = PlatformPublisherRegistry()
    registry.register(_Publisher("youtube"))
    report = PublishingExecutionCoordinator(registry).execute(
        _manifest((_package(),))
    )
    with pytest.raises(TypeError):
        report.metadata["x"] = "y"  # type: ignore[index]


def test_observation_metadata_is_immutable() -> None:
    observation = PlatformPublishingObservation(
        package_id="package-001",
        platform="youtube",
        account_id="channel-001",
        status=PublishingExecutionStatus.SUCCEEDED,
        provider_name="fake",
        platform_post_id="post-001",
        metadata={"a": "b"},
    )
    with pytest.raises(TypeError):
        observation.metadata["x"] = "y"  # type: ignore[index]


def test_platform_cannot_contain_whitespace() -> None:
    registry = PlatformPublisherRegistry()
    with pytest.raises(PublishingExecutionError, match="whitespace"):
        registry.register(_Publisher("you tube"))
