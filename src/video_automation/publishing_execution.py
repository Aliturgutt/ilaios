"""Provider-independent publishing execution.

This module consumes immutable publishing packages, resolves an explicit
platform publisher adapter, executes one publish operation per package, and
records immutable normalized execution evidence.

It does not select accounts, prepare metadata, retry failures, poll providers,
or make publishing policy decisions.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from types import MappingProxyType
from typing import Protocol

from .models import MetadataValue, ProviderRequest
from .providers import PublishingProvider, PublishingProviderOutput
from .publishing_package_preparation import (
    EpisodePublishingPackageManifest,
    PlatformPublishingPackage,
)


class PublishingExecutionError(ValueError):
    """Raised when deterministic publishing execution cannot proceed."""


class PublishingExecutionStatus(str, Enum):
    """Normalized execution result for one publishing package."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class PlatformPublishingObservation:
    """Normalized provider response from one publishing adapter."""

    package_id: str
    platform: str
    account_id: str
    status: PublishingExecutionStatus
    provider_name: str
    platform_post_id: str | None = None
    published_url: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("package_id", "platform", "account_id", "provider_name"):
            _require_non_blank(name, getattr(self, name))
        if self.status is PublishingExecutionStatus.SUCCEEDED:
            if self.platform_post_id is None:
                raise PublishingExecutionError(
                    "successful observation requires platform_post_id"
                )
            if self.error_code is not None or self.error_message is not None:
                raise PublishingExecutionError(
                    "successful observation must not contain errors"
                )
        else:
            if self.error_message is None:
                raise PublishingExecutionError(
                    "failed observation requires error_message"
                )
            if self.platform_post_id is not None or self.published_url is not None:
                raise PublishingExecutionError(
                    "failed observation must not contain publication identifiers"
                )
        for name in (
            "platform_post_id",
            "published_url",
            "error_code",
            "error_message",
        ):
            value = getattr(self, name)
            if value is not None:
                _require_non_blank(name, value)
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


class PlatformPublisher(Protocol):
    """Adapter contract for publishing one explicit platform package."""

    @property
    def publisher_id(self) -> str:
        """Return a deterministic adapter identifier."""

    @property
    def platform(self) -> str:
        """Return the normalized platform handled by this adapter."""

    def publish(
        self,
        package: PlatformPublishingPackage,
    ) -> PlatformPublishingObservation:
        """Execute one publish operation and return normalized evidence."""


class PlatformPublisherRegistry:
    """Immutable-by-registration registry for platform publisher adapters."""

    def __init__(self) -> None:
        self._publishers: dict[str, PlatformPublisher] = {}

    def register(self, publisher: PlatformPublisher) -> None:
        platform = _normalize_platform(publisher.platform)
        if platform in self._publishers:
            raise PublishingExecutionError(
                f"publisher already registered for platform: {platform}"
            )
        self._publishers[platform] = publisher

    def get(self, platform: str) -> PlatformPublisher:
        normalized = _normalize_platform(platform)
        try:
            return self._publishers[normalized]
        except KeyError as exc:
            raise PublishingExecutionError(
                f"no publisher registered for platform: {normalized}"
            ) from exc


class PublishingProviderAdapter:
    """Bridge an existing PublishingProvider to the PlatformPublisher contract."""

    def __init__(
        self,
        platform: str,
        provider: PublishingProvider,
    ) -> None:
        self._platform = _normalize_platform(platform)
        self._provider = provider

    @property
    def publisher_id(self) -> str:
        return f"publishing-provider:{self._provider.capabilities.provider_name}"

    @property
    def platform(self) -> str:
        return self._platform

    def publish(
        self,
        package: PlatformPublishingPackage,
    ) -> PlatformPublishingObservation:
        if package.platform != self._platform:
            raise PublishingExecutionError(
                "package platform does not match publisher adapter"
            )
        payload: dict[str, MetadataValue] = {
            "package_id": package.package_id,
            "account_id": package.account_id,
            "media_path": package.media_path,
            "media_sha256_hex": package.media_sha256_hex,
            "media_byte_length": package.media_byte_length,
            "scheduled_at": package.scheduled_at.isoformat(),
            "visibility": package.visibility,
            "title": package.title,
            "description": package.description,
            "tags": ",".join(package.tags),
        }
        request = ProviderRequest(
            request_id=f"publish:{package.package_id}",
            job_id=package.episode_id,
            provider_name=self._provider.capabilities.provider_name,
            operation="publish",
            payload=payload,
        )
        raw = self._provider.execute(request)
        output = PublishingProviderOutput(
            provider_result=raw,
            platform_post_id=(
                str(raw.metadata["platform_post_id"])
                if raw.success and "platform_post_id" in raw.metadata
                else None
            ),
            published_url=(
                str(raw.metadata["published_url"])
                if raw.success and "published_url" in raw.metadata
                else None
            ),
        )
        if output.provider_result.success:
            return PlatformPublishingObservation(
                package_id=package.package_id,
                platform=package.platform,
                account_id=package.account_id,
                status=PublishingExecutionStatus.SUCCEEDED,
                provider_name=output.provider_result.provider_name,
                platform_post_id=output.platform_post_id,
                published_url=output.published_url,
                metadata={
                    "publisher_id": self.publisher_id,
                    "provider_request_id": request.request_id,
                },
            )
        return PlatformPublishingObservation(
            package_id=package.package_id,
            platform=package.platform,
            account_id=package.account_id,
            status=PublishingExecutionStatus.FAILED,
            provider_name=output.provider_result.provider_name,
            error_code=output.provider_result.error_code,
            error_message=output.provider_result.error_message,
            metadata={
                "publisher_id": self.publisher_id,
                "provider_request_id": request.request_id,
            },
        )


@dataclass(frozen=True, slots=True)
class PublishingExecutionReport:
    """Immutable execution evidence for one publishing manifest."""

    report_id: str
    manifest_id: str
    episode_id: str
    observations: tuple[PlatformPublishingObservation, ...]
    package_count: int
    succeeded_count: int
    failed_count: int
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("report_id", "manifest_id", "episode_id"):
            _require_non_blank(name, getattr(self, name))
        if not self.observations:
            raise PublishingExecutionError("observations must not be empty")
        if self.package_count != len(self.observations):
            raise PublishingExecutionError(
                "package_count must equal observations length"
            )
        succeeded = sum(
            observation.status is PublishingExecutionStatus.SUCCEEDED
            for observation in self.observations
        )
        failed = sum(
            observation.status is PublishingExecutionStatus.FAILED
            for observation in self.observations
        )
        if self.succeeded_count != succeeded:
            raise PublishingExecutionError("succeeded_count is inconsistent")
        if self.failed_count != failed:
            raise PublishingExecutionError("failed_count is inconsistent")
        if self.succeeded_count + self.failed_count != self.package_count:
            raise PublishingExecutionError("execution counts are inconsistent")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


class PublishingExecutionCoordinator:
    """Execute every package exactly once through its registered publisher."""

    def __init__(self, registry: PlatformPublisherRegistry) -> None:
        self._registry = registry

    def execute(
        self,
        manifest: EpisodePublishingPackageManifest,
    ) -> PublishingExecutionReport:
        observations = tuple(
            self._execute_package(package) for package in manifest.packages
        )
        succeeded_count = sum(
            observation.status is PublishingExecutionStatus.SUCCEEDED
            for observation in observations
        )
        failed_count = len(observations) - succeeded_count
        material = "\n".join(
            (
                f"manifest_id={manifest.manifest_id}",
                f"episode_id={manifest.episode_id}",
                *(
                    "|".join(
                        (
                            observation.package_id,
                            observation.status.value,
                            observation.provider_name,
                            observation.platform_post_id or "",
                            observation.error_code or "",
                        )
                    )
                    for observation in observations
                ),
            )
        )
        report_id = (
            "publishing-execution-report-"
            f"{sha256(material.encode('utf-8')).hexdigest()[:16]}"
        )
        return PublishingExecutionReport(
            report_id=report_id,
            manifest_id=manifest.manifest_id,
            episode_id=manifest.episode_id,
            observations=observations,
            package_count=len(observations),
            succeeded_count=succeeded_count,
            failed_count=failed_count,
            metadata={
                "artifact_id": manifest.artifact_id,
                "acceptance_decision_id": manifest.acceptance_decision_id,
            },
        )

    def _execute_package(
        self,
        package: PlatformPublishingPackage,
    ) -> PlatformPublishingObservation:
        publisher = self._registry.get(package.platform)
        observation = publisher.publish(package)
        if observation.package_id != package.package_id:
            raise PublishingExecutionError(
                "publisher observation package_id mismatch"
            )
        if observation.platform != package.platform:
            raise PublishingExecutionError(
                "publisher observation platform mismatch"
            )
        if observation.account_id != package.account_id:
            raise PublishingExecutionError(
                "publisher observation account_id mismatch"
            )
        return observation


def _normalize_platform(value: str) -> str:
    _require_non_blank("platform", value)
    normalized = value.strip().lower()
    if any(character.isspace() for character in normalized):
        raise PublishingExecutionError(
            "platform must not contain whitespace"
        )
    return normalized


def _freeze_metadata(metadata: Mapping[str, str]) -> Mapping[str, str]:
    normalized = dict(metadata)
    for key, value in normalized.items():
        _require_non_blank("metadata key", key)
        _require_non_blank(f"metadata value for {key}", value)
    return MappingProxyType(dict(sorted(normalized.items())))


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip():
        raise PublishingExecutionError(f"{name} must not be blank")
