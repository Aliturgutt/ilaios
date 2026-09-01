"""Deterministic post-publish verification and evidence normalization.

This module cross-checks a publishing execution report against the immutable
publishing package manifest and produces final publication verification
evidence. It classifies each package as VERIFIED or FAILED based only on
recorded execution evidence.

It does not call platform APIs, poll posts, retry publishing, fetch analytics,
modify publications, or infer provider state.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from types import MappingProxyType

from .publishing_execution import (
    PlatformPublishingObservation,
    PublishingExecutionReport,
    PublishingExecutionStatus,
)
from .publishing_package_preparation import (
    EpisodePublishingPackageManifest,
    PlatformPublishingPackage,
)


class PostPublishVerificationError(ValueError):
    """Raised when post-publish evidence cannot be verified deterministically."""


class PublicationVerificationStatus(str, Enum):
    """Normalized final verification state for one publication."""

    VERIFIED = "verified"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class PublicationVerificationEvidence:
    """Immutable verification evidence for one publishing package."""

    verification_id: str
    package_id: str
    platform: str
    account_id: str
    provider_name: str
    status: PublicationVerificationStatus
    platform_post_id: str | None = None
    published_url: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "verification_id",
            "package_id",
            "platform",
            "account_id",
            "provider_name",
        ):
            _require_non_blank(name, getattr(self, name))
        if self.status is PublicationVerificationStatus.VERIFIED:
            if self.platform_post_id is None:
                raise PostPublishVerificationError(
                    "verified publication requires platform_post_id"
                )
            if self.error_code is not None or self.error_message is not None:
                raise PostPublishVerificationError(
                    "verified publication must not contain errors"
                )
        else:
            if self.error_message is None:
                raise PostPublishVerificationError(
                    "failed publication requires error_message"
                )
            if self.platform_post_id is not None or self.published_url is not None:
                raise PostPublishVerificationError(
                    "failed publication must not contain publication identifiers"
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


@dataclass(frozen=True, slots=True)
class PostPublishVerificationManifest:
    """Immutable final verification manifest for one publishing execution."""

    manifest_id: str
    execution_report_id: str
    publishing_manifest_id: str
    episode_id: str
    evidence: tuple[PublicationVerificationEvidence, ...]
    publication_count: int
    verified_count: int
    failed_count: int
    all_verified: bool
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "manifest_id",
            "execution_report_id",
            "publishing_manifest_id",
            "episode_id",
        ):
            _require_non_blank(name, getattr(self, name))
        if not self.evidence:
            raise PostPublishVerificationError("evidence must not be empty")
        if self.publication_count != len(self.evidence):
            raise PostPublishVerificationError(
                "publication_count must equal evidence length"
            )
        verified = sum(
            item.status is PublicationVerificationStatus.VERIFIED
            for item in self.evidence
        )
        failed = sum(
            item.status is PublicationVerificationStatus.FAILED
            for item in self.evidence
        )
        if self.verified_count != verified:
            raise PostPublishVerificationError(
                "verified_count is inconsistent"
            )
        if self.failed_count != failed:
            raise PostPublishVerificationError("failed_count is inconsistent")
        if self.verified_count + self.failed_count != self.publication_count:
            raise PostPublishVerificationError(
                "verification counts are inconsistent"
            )
        if self.all_verified != (self.failed_count == 0):
            raise PostPublishVerificationError(
                "all_verified is inconsistent"
            )
        package_ids = tuple(item.package_id for item in self.evidence)
        if len(package_ids) != len(set(package_ids)):
            raise PostPublishVerificationError(
                "verification package_ids must be unique"
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


class PostPublishVerificationCoordinator:
    """Cross-check execution evidence and build final publication verification."""

    def verify(
        self,
        publishing_manifest: EpisodePublishingPackageManifest,
        execution_report: PublishingExecutionReport,
    ) -> PostPublishVerificationManifest:
        _validate_report_identity(publishing_manifest, execution_report)

        package_by_id = {
            package.package_id: package for package in publishing_manifest.packages
        }
        observation_by_id: dict[str, PlatformPublishingObservation] = {}

        for observation in execution_report.observations:
            if observation.package_id in observation_by_id:
                raise PostPublishVerificationError(
                    f"duplicate observation package_id: {observation.package_id}"
                )
            observation_by_id[observation.package_id] = observation

        if set(package_by_id) != set(observation_by_id):
            missing = sorted(set(package_by_id) - set(observation_by_id))
            extra = sorted(set(observation_by_id) - set(package_by_id))
            raise PostPublishVerificationError(
                f"package/observation mismatch: missing={missing}, extra={extra}"
            )

        evidence = tuple(
            self._verify_one(
                package_by_id[package_id],
                observation_by_id[package_id],
                execution_report.report_id,
            )
            for package_id in sorted(package_by_id)
        )
        verified_count = sum(
            item.status is PublicationVerificationStatus.VERIFIED
            for item in evidence
        )
        failed_count = len(evidence) - verified_count

        material = "\n".join(
            (
                f"publishing_manifest_id={publishing_manifest.manifest_id}",
                f"execution_report_id={execution_report.report_id}",
                f"episode_id={publishing_manifest.episode_id}",
                *(
                    "|".join(
                        (
                            item.package_id,
                            item.status.value,
                            item.platform_post_id or "",
                            item.error_code or "",
                        )
                    )
                    for item in evidence
                ),
            )
        )
        verification_manifest_id = (
            "post-publish-verification-"
            f"{sha256(material.encode('utf-8')).hexdigest()[:16]}"
        )

        return PostPublishVerificationManifest(
            manifest_id=verification_manifest_id,
            execution_report_id=execution_report.report_id,
            publishing_manifest_id=publishing_manifest.manifest_id,
            episode_id=publishing_manifest.episode_id,
            evidence=evidence,
            publication_count=len(evidence),
            verified_count=verified_count,
            failed_count=failed_count,
            all_verified=failed_count == 0,
            metadata={
                "artifact_id": publishing_manifest.artifact_id,
                "acceptance_decision_id": (
                    publishing_manifest.acceptance_decision_id
                ),
            },
        )

    def _verify_one(
        self,
        package: PlatformPublishingPackage,
        observation: PlatformPublishingObservation,
        execution_report_id: str,
    ) -> PublicationVerificationEvidence:
        package_id = package.package_id
        platform = package.platform
        account_id = package.account_id

        if observation.platform != platform:
            raise PostPublishVerificationError(
                f"platform mismatch for package: {package_id}"
            )
        if observation.account_id != account_id:
            raise PostPublishVerificationError(
                f"account_id mismatch for package: {package_id}"
            )

        status = (
            PublicationVerificationStatus.VERIFIED
            if observation.status is PublishingExecutionStatus.SUCCEEDED
            else PublicationVerificationStatus.FAILED
        )
        material = "|".join(
            (
                execution_report_id,
                package_id,
                observation.provider_name,
                status.value,
                observation.platform_post_id or "",
                observation.published_url or "",
                observation.error_code or "",
                observation.error_message or "",
            )
        )
        verification_id = (
            "publication-verification-"
            f"{sha256(material.encode('utf-8')).hexdigest()[:16]}"
        )

        return PublicationVerificationEvidence(
            verification_id=verification_id,
            package_id=package_id,
            platform=platform,
            account_id=account_id,
            provider_name=observation.provider_name,
            status=status,
            platform_post_id=observation.platform_post_id,
            published_url=observation.published_url,
            error_code=observation.error_code,
            error_message=observation.error_message,
            metadata={
                "execution_report_id": execution_report_id,
            },
        )


def _validate_report_identity(
    publishing_manifest: EpisodePublishingPackageManifest,
    execution_report: PublishingExecutionReport,
) -> None:
    if execution_report.manifest_id != publishing_manifest.manifest_id:
        raise PostPublishVerificationError(
            "execution report manifest_id does not match publishing manifest"
        )
    if execution_report.episode_id != publishing_manifest.episode_id:
        raise PostPublishVerificationError(
            "execution report episode_id does not match publishing manifest"
        )
    if execution_report.package_count != publishing_manifest.package_count:
        raise PostPublishVerificationError(
            "execution report package_count does not match publishing manifest"
        )


def _freeze_metadata(metadata: Mapping[str, str]) -> Mapping[str, str]:
    normalized = dict(metadata)
    for key, value in normalized.items():
        _require_non_blank("metadata key", key)
        _require_non_blank(f"metadata value for {key}", value)
    return MappingProxyType(dict(sorted(normalized.items())))


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip():
        raise PostPublishVerificationError(f"{name} must not be blank")
