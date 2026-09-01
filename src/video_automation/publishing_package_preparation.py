"""Deterministic publishing package preparation.

This module converts an accepted final episode and immutable assembly artifact
into provider-neutral platform publishing packages. It prepares metadata and
publication intent only.

It does not authenticate, call platform APIs, upload media, publish content,
schedule external jobs, select accounts, or retry failed publications.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from types import MappingProxyType

from .episode_assembly_execution import EpisodeAssemblyArtifact
from .final_episode_acceptance import (
    FinalEpisodeAcceptanceDecision,
    FinalEpisodeAcceptanceStatus,
)


class PublishingPackagePreparationError(ValueError):
    """Raised when deterministic publishing packaging cannot be completed."""


@dataclass(frozen=True, slots=True)
class PublishingTarget:
    """Explicit platform/account publishing target supplied by orchestration."""

    platform: str
    account_id: str
    scheduled_at: datetime
    visibility: str
    title: str
    description: str
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "platform",
            "account_id",
            "visibility",
            "title",
            "description",
        ):
            _require_non_blank(name, getattr(self, name))
        _validate_timezone_aware("scheduled_at", self.scheduled_at)

        normalized_tags = tuple(_normalize_tag(tag) for tag in self.tags)
        if len(normalized_tags) != len(set(normalized_tags)):
            raise PublishingPackagePreparationError("tags must be unique")
        object.__setattr__(self, "platform", self.platform.strip().lower())
        object.__setattr__(self, "visibility", self.visibility.strip().lower())
        object.__setattr__(self, "tags", normalized_tags)
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class PlatformPublishingPackage:
    """Immutable publication package for exactly one platform/account target."""

    package_id: str
    episode_id: str
    artifact_id: str
    acceptance_decision_id: str
    platform: str
    account_id: str
    media_path: str
    media_sha256_hex: str
    media_byte_length: int
    scheduled_at: datetime
    visibility: str
    title: str
    description: str
    tags: tuple[str, ...]
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "package_id",
            "episode_id",
            "artifact_id",
            "acceptance_decision_id",
            "platform",
            "account_id",
            "media_path",
            "media_sha256_hex",
            "visibility",
            "title",
            "description",
        ):
            _require_non_blank(name, getattr(self, name))
        _validate_sha256(self.media_sha256_hex)
        if self.media_byte_length <= 0:
            raise PublishingPackagePreparationError(
                "media_byte_length must be greater than zero"
            )
        _validate_timezone_aware("scheduled_at", self.scheduled_at)
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class EpisodePublishingPackageManifest:
    """Immutable provider-neutral publishing package manifest for one episode."""

    manifest_id: str
    episode_id: str
    artifact_id: str
    acceptance_decision_id: str
    packages: tuple[PlatformPublishingPackage, ...]
    package_count: int
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "manifest_id",
            "episode_id",
            "artifact_id",
            "acceptance_decision_id",
        ):
            _require_non_blank(name, getattr(self, name))
        if not self.packages:
            raise PublishingPackagePreparationError(
                "packages must not be empty"
            )
        if self.package_count != len(self.packages):
            raise PublishingPackagePreparationError(
                "package_count must equal packages length"
            )
        identities = tuple(
            (package.platform, package.account_id) for package in self.packages
        )
        if len(identities) != len(set(identities)):
            raise PublishingPackagePreparationError(
                "platform/account targets must be unique"
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


class PublishingPackagePreparer:
    """Prepare deterministic platform packages from accepted episode evidence."""

    def prepare(
        self,
        artifact: EpisodeAssemblyArtifact,
        acceptance: FinalEpisodeAcceptanceDecision,
        targets: Sequence[PublishingTarget],
    ) -> EpisodePublishingPackageManifest:
        _validate_acceptance_identity(artifact, acceptance)
        if acceptance.status is not FinalEpisodeAcceptanceStatus.ACCEPTED:
            raise PublishingPackagePreparationError(
                "final episode acceptance must be ACCEPTED before packaging"
            )
        if not targets:
            raise PublishingPackagePreparationError(
                "at least one publishing target is required"
            )

        normalized_targets = tuple(
            sorted(
                targets,
                key=lambda target: (
                    target.platform,
                    target.account_id,
                    target.scheduled_at.isoformat(),
                ),
            )
        )
        target_keys = tuple(
            (target.platform, target.account_id) for target in normalized_targets
        )
        if len(target_keys) != len(set(target_keys)):
            raise PublishingPackagePreparationError(
                "platform/account targets must be unique"
            )

        packages = tuple(
            self._build_package(artifact, acceptance, target)
            for target in normalized_targets
        )
        material = "\n".join(
            (
                f"episode_id={artifact.episode_id}",
                f"artifact_id={artifact.artifact_id}",
                f"acceptance_decision_id={acceptance.decision_id}",
                *(
                    f"package_id={package.package_id}"
                    for package in packages
                ),
            )
        )
        manifest_id = (
            "publishing-package-manifest-"
            f"{sha256(material.encode('utf-8')).hexdigest()[:16]}"
        )
        return EpisodePublishingPackageManifest(
            manifest_id=manifest_id,
            episode_id=artifact.episode_id,
            artifact_id=artifact.artifact_id,
            acceptance_decision_id=acceptance.decision_id,
            packages=packages,
            package_count=len(packages),
            metadata={
                "source_media_sha256": artifact.sha256_hex,
                "target_count": str(len(packages)),
            },
        )

    def _build_package(
        self,
        artifact: EpisodeAssemblyArtifact,
        acceptance: FinalEpisodeAcceptanceDecision,
        target: PublishingTarget,
    ) -> PlatformPublishingPackage:
        material = "|".join(
            (
                artifact.episode_id,
                artifact.artifact_id,
                acceptance.decision_id,
                target.platform,
                target.account_id,
                target.scheduled_at.isoformat(),
                target.visibility,
                target.title,
                target.description,
                ",".join(target.tags),
            )
        )
        package_id = (
            f"publishing-package-"
            f"{sha256(material.encode('utf-8')).hexdigest()[:16]}"
        )
        metadata = dict(target.metadata)
        metadata["acceptance_policy_id"] = acceptance.policy_id
        return PlatformPublishingPackage(
            package_id=package_id,
            episode_id=artifact.episode_id,
            artifact_id=artifact.artifact_id,
            acceptance_decision_id=acceptance.decision_id,
            platform=target.platform,
            account_id=target.account_id,
            media_path=artifact.output_path,
            media_sha256_hex=artifact.sha256_hex,
            media_byte_length=artifact.byte_length,
            scheduled_at=target.scheduled_at,
            visibility=target.visibility,
            title=target.title.strip(),
            description=target.description.strip(),
            tags=target.tags,
            metadata=metadata,
        )


def _validate_acceptance_identity(
    artifact: EpisodeAssemblyArtifact,
    acceptance: FinalEpisodeAcceptanceDecision,
) -> None:
    if acceptance.artifact_id != artifact.artifact_id:
        raise PublishingPackagePreparationError(
            "acceptance artifact_id does not match assembly artifact"
        )
    if acceptance.request_id != artifact.request_id:
        raise PublishingPackagePreparationError(
            "acceptance request_id does not match assembly artifact"
        )
    if acceptance.episode_id != artifact.episode_id:
        raise PublishingPackagePreparationError(
            "acceptance episode_id does not match assembly artifact"
        )


def _normalize_tag(value: str) -> str:
    _require_non_blank("tag", value)
    normalized = value.strip().lower()
    if any(character.isspace() for character in normalized):
        raise PublishingPackagePreparationError(
            "tags must not contain whitespace"
        )
    return normalized


def _validate_timezone_aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise PublishingPackagePreparationError(
            f"{name} must be timezone-aware"
        )


def _validate_sha256(value: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise PublishingPackagePreparationError(
            "media_sha256_hex must be a lowercase SHA-256 digest"
        )


def _freeze_metadata(metadata: Mapping[str, str]) -> Mapping[str, str]:
    normalized = dict(metadata)
    for key, value in normalized.items():
        _require_non_blank("metadata key", key)
        _require_non_blank(f"metadata value for {key}", value)
    return MappingProxyType(dict(sorted(normalized.items())))


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip():
        raise PublishingPackagePreparationError(f"{name} must not be blank")
