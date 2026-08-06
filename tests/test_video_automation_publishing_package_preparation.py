from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import pytest

from src.video_automation.episode_assembly_execution import EpisodeAssemblyArtifact
from src.video_automation.final_episode_acceptance import (
    FinalEpisodeAcceptanceDecision,
    FinalEpisodeAcceptanceIssue,
    FinalEpisodeAcceptanceStatus,
)
from src.video_automation.publishing_package_preparation import (
    PublishingPackagePreparationError,
    PublishingPackagePreparer,
    PublishingTarget,
)


def _artifact(path: Path) -> EpisodeAssemblyArtifact:
    body = b"publishable-episode"
    path.write_bytes(body)
    return EpisodeAssemblyArtifact(
        artifact_id="episode-assembly-artifact-001",
        request_id="episode-assembly-request-001",
        episode_id="episode-001",
        executor_id="fake-executor-v1",
        output_path=str(path),
        sha256_hex=sha256(body).hexdigest(),
        byte_length=len(body),
        container_format="mp4",
        video_codec="h264",
        audio_codec="aac",
        width=1080,
        height=1920,
        frame_rate=30,
        source_asset_ids=("asset-1", "asset-2"),
        metadata={},
    )


def _acceptance(
    artifact: EpisodeAssemblyArtifact,
    *,
    status: FinalEpisodeAcceptanceStatus = FinalEpisodeAcceptanceStatus.ACCEPTED,
) -> FinalEpisodeAcceptanceDecision:
    issues = (
        ()
        if status is FinalEpisodeAcceptanceStatus.ACCEPTED
        else (FinalEpisodeAcceptanceIssue("rejected", "episode rejected"),)
    )
    return FinalEpisodeAcceptanceDecision(
        decision_id="final-episode-acceptance-001",
        artifact_id=artifact.artifact_id,
        technical_validation_id="assembled-output-validation-001",
        request_id=artifact.request_id,
        episode_id=artifact.episode_id,
        status=status,
        quality_checks=(),
        issues=issues,
        policy_id="final-episode-policy-001",
        metadata={},
    )


def _target(
    platform: str = "youtube",
    account_id: str = "channel-001",
) -> PublishingTarget:
    return PublishingTarget(
        platform=platform,
        account_id=account_id,
        scheduled_at=datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc),
        visibility="public",
        title="The Last Origin — Episode 001",
        description="The first chapter of The Last Origin.",
        tags=("lastorigin", "shorts"),
        metadata={"language": "en"},
    )


def test_prepares_one_package_from_accepted_episode(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    manifest = PublishingPackagePreparer().prepare(
        artifact,
        _acceptance(artifact),
        (_target(),),
    )
    assert manifest.package_count == 1
    assert manifest.packages[0].platform == "youtube"
    assert manifest.packages[0].media_sha256_hex == artifact.sha256_hex


def test_package_preparation_is_deterministic(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    preparer = PublishingPackagePreparer()
    first = preparer.prepare(artifact, _acceptance(artifact), (_target(),))
    second = preparer.prepare(artifact, _acceptance(artifact), (_target(),))
    assert first.manifest_id == second.manifest_id
    assert first.packages[0].package_id == second.packages[0].package_id


def test_rejected_episode_cannot_be_packaged(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    with pytest.raises(PublishingPackagePreparationError, match="ACCEPTED"):
        PublishingPackagePreparer().prepare(
            artifact,
            _acceptance(
                artifact,
                status=FinalEpisodeAcceptanceStatus.REJECTED,
            ),
            (_target(),),
        )


def test_artifact_identity_must_match(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    acceptance = _acceptance(artifact)
    object.__setattr__(acceptance, "artifact_id", "artifact-other")
    with pytest.raises(PublishingPackagePreparationError, match="artifact_id"):
        PublishingPackagePreparer().prepare(
            artifact, acceptance, (_target(),)
        )


def test_episode_identity_must_match(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    acceptance = _acceptance(artifact)
    object.__setattr__(acceptance, "episode_id", "episode-other")
    with pytest.raises(PublishingPackagePreparationError, match="episode_id"):
        PublishingPackagePreparer().prepare(
            artifact, acceptance, (_target(),)
        )


def test_request_identity_must_match(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    acceptance = _acceptance(artifact)
    object.__setattr__(acceptance, "request_id", "request-other")
    with pytest.raises(PublishingPackagePreparationError, match="request_id"):
        PublishingPackagePreparer().prepare(
            artifact, acceptance, (_target(),)
        )


def test_requires_at_least_one_target(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    with pytest.raises(PublishingPackagePreparationError, match="at least one"):
        PublishingPackagePreparer().prepare(
            artifact, _acceptance(artifact), ()
        )


def test_duplicate_platform_account_target_is_rejected(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    target = _target()
    with pytest.raises(PublishingPackagePreparationError, match="unique"):
        PublishingPackagePreparer().prepare(
            artifact,
            _acceptance(artifact),
            (target, target),
        )


def test_targets_are_sorted_deterministically(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    manifest = PublishingPackagePreparer().prepare(
        artifact,
        _acceptance(artifact),
        (
            _target("youtube", "channel-b"),
            _target("tiktok", "account-a"),
            _target("youtube", "channel-a"),
        ),
    )
    assert tuple(
        (package.platform, package.account_id) for package in manifest.packages
    ) == (
        ("tiktok", "account-a"),
        ("youtube", "channel-a"),
        ("youtube", "channel-b"),
    )


def test_platform_and_visibility_are_normalized() -> None:
    target = PublishingTarget(
        platform=" YouTube ",
        account_id="channel-001",
        scheduled_at=datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc),
        visibility=" PUBLIC ",
        title="Episode",
        description="Description",
    )
    assert target.platform == "youtube"
    assert target.visibility == "public"


def test_tags_are_normalized() -> None:
    target = PublishingTarget(
        platform="youtube",
        account_id="channel-001",
        scheduled_at=datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc),
        visibility="public",
        title="Episode",
        description="Description",
        tags=("LastOrigin", "SHORTS"),
    )
    assert target.tags == ("lastorigin", "shorts")


def test_duplicate_tags_are_rejected() -> None:
    with pytest.raises(PublishingPackagePreparationError, match="unique"):
        PublishingTarget(
            platform="youtube",
            account_id="channel-001",
            scheduled_at=datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc),
            visibility="public",
            title="Episode",
            description="Description",
            tags=("shorts", "SHORTS"),
        )


def test_tag_whitespace_is_rejected() -> None:
    with pytest.raises(PublishingPackagePreparationError, match="whitespace"):
        PublishingTarget(
            platform="youtube",
            account_id="channel-001",
            scheduled_at=datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc),
            visibility="public",
            title="Episode",
            description="Description",
            tags=("last origin",),
        )


def test_scheduled_at_must_be_timezone_aware() -> None:
    with pytest.raises(PublishingPackagePreparationError, match="timezone-aware"):
        PublishingTarget(
            platform="youtube",
            account_id="channel-001",
            scheduled_at=datetime(2026, 8, 5, 9, 0),  # noqa: DTZ001
            visibility="public",
            title="Episode",
            description="Description",
        )


def test_manifest_metadata_is_immutable(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    manifest = PublishingPackagePreparer().prepare(
        artifact,
        _acceptance(artifact),
        (_target(),),
    )
    with pytest.raises(TypeError):
        manifest.metadata["x"] = "y"  # type: ignore[index]


def test_package_metadata_is_immutable(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    manifest = PublishingPackagePreparer().prepare(
        artifact,
        _acceptance(artifact),
        (_target(),),
    )
    with pytest.raises(TypeError):
        manifest.packages[0].metadata["x"] = "y"  # type: ignore[index]


def test_package_carries_acceptance_policy_evidence(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    manifest = PublishingPackagePreparer().prepare(
        artifact,
        _acceptance(artifact),
        (_target(),),
    )
    assert manifest.packages[0].metadata["acceptance_policy_id"] == (
        "final-episode-policy-001"
    )
