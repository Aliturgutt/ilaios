"""Tests for ILAIOS Video Automation domain models."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from src.video_automation.models import (
    AssetRequest,
    CostRecord,
    JobState,
    JobStateRecord,
    MediaAsset,
    MediaType,
    ProviderRequest,
    ProviderResult,
    PublishJob,
    RenderArtifact,
    ResearchPacket,
    Scene,
    ScriptSection,
    Shot,
    Timeline,
    TimelineItem,
    ValidationResult,
    VideoFormat,
    VideoJob,
    VideoScript,
)

UTC_NOW = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)
SHA256 = "a" * 64


def make_video_job() -> VideoJob:
    return VideoJob(
        job_id="job-1",
        project_id="project-1",
        topic="Deterministic AI systems",
        objective="Create an educational short video",
        target_audience="Software engineers",
        target_platforms=("youtube", "tiktok"),
        language="en",
        desired_duration_seconds=60,
        video_format=VideoFormat.SHORT_FORM,
        aspect_ratio="9:16",
        content_style="technical",
        publishing_strategy="scheduled",
        provider_policy="test-default",
        budget_policy="no-paid-providers",
        approval_policy="manual-before-publish",
        created_at=UTC_NOW,
    )


def test_video_job_is_constructed_and_immutable() -> None:
    job = make_video_job()

    assert job.job_id == "job-1"
    assert job.target_platforms == ("youtube", "tiktok")
    with pytest.raises(FrozenInstanceError):
        job.topic = "changed"  # type: ignore[misc]


def test_video_job_rejects_invalid_duration() -> None:
    with pytest.raises(ValueError, match="desired_duration_seconds"):
        VideoJob(
            job_id="job-1",
            project_id="project-1",
            topic="topic",
            objective="objective",
            target_audience="audience",
            target_platforms=("youtube",),
            language="en",
            desired_duration_seconds=0,
            video_format=VideoFormat.SHORT_FORM,
            aspect_ratio="9:16",
            content_style="technical",
            publishing_strategy="scheduled",
            provider_policy="test",
            budget_policy="free",
            approval_policy="manual",
            created_at=UTC_NOW,
        )


def test_video_job_rejects_duplicate_platforms() -> None:
    with pytest.raises(ValueError, match="duplicate target platform"):
        VideoJob(
            job_id="job-1",
            project_id="project-1",
            topic="topic",
            objective="objective",
            target_audience="audience",
            target_platforms=("youtube", "youtube"),
            language="en",
            desired_duration_seconds=60,
            video_format=VideoFormat.SHORT_FORM,
            aspect_ratio="9:16",
            content_style="technical",
            publishing_strategy="scheduled",
            provider_policy="test",
            budget_policy="free",
            approval_policy="manual",
            created_at=UTC_NOW,
        )


def test_video_job_requires_utc_timestamp() -> None:
    non_utc = datetime(2026, 8, 2, 15, 0, tzinfo=timezone(timedelta(hours=3)))
    with pytest.raises(ValueError, match="created_at must use UTC"):
        VideoJob(
            job_id="job-1",
            project_id="project-1",
            topic="topic",
            objective="objective",
            target_audience="audience",
            target_platforms=("youtube",),
            language="en",
            desired_duration_seconds=60,
            video_format=VideoFormat.SHORT_FORM,
            aspect_ratio="9:16",
            content_style="technical",
            publishing_strategy="scheduled",
            provider_policy="test",
            budget_policy="free",
            approval_policy="manual",
            created_at=non_utc,
        )


def test_research_packet_preserves_structured_evidence() -> None:
    packet = ResearchPacket(
        job_id="job-1",
        topic_summary="Summary",
        verified_facts=("Fact A",),
        source_references=("source://a",),
        key_claims=("Claim A",),
    )

    assert packet.verified_facts == ("Fact A",)
    assert packet.source_references == ("source://a",)


def test_video_script_requires_unique_section_ids() -> None:
    section = ScriptSection(
        section_id="s1",
        title="Opening",
        narration="Narration",
        estimated_duration_seconds=10,
    )

    with pytest.raises(ValueError, match="unique"):
        VideoScript(
            job_id="job-1",
            hook="Hook",
            introduction="Intro",
            sections=(section, section),
            cta=None,
            ending="End",
            estimated_duration_seconds=20,
        )


def test_scene_requires_positive_duration() -> None:
    with pytest.raises(ValueError, match="duration_seconds"):
        Scene(
            scene_id="scene-1",
            script_reference="s1",
            purpose="opening",
            duration_seconds=0,
            visual_description="Visual",
            narration_reference="s1",
            transition_intent="cut",
        )


def test_shot_can_be_constructed() -> None:
    shot = Shot(
        shot_id="shot-1",
        scene_id="scene-1",
        shot_type="establishing",
        camera_description="wide camera",
        subject="city",
        action="traffic moving",
        environment="urban",
        framing="wide",
        movement="slow push",
        estimated_duration_seconds=4.5,
        generation_prompt="Cinematic city",
        required_provider_capability="text-to-video",
    )

    assert shot.scene_id == "scene-1"
    assert shot.estimated_duration_seconds == 4.5


def test_asset_request_metadata_is_sorted_and_read_only() -> None:
    request = AssetRequest(
        asset_request_id="asset-request-1",
        job_id="job-1",
        shot_id="shot-1",
        media_type=MediaType.VIDEO,
        description="Opening clip",
        required_capability="text-to-video",
        metadata={"z": 2, "a": 1},
    )

    assert tuple(request.metadata.items()) == (("a", 1), ("z", 2))
    with pytest.raises(TypeError):
        request.metadata["x"] = 3  # type: ignore[index]


def test_media_asset_rejects_invalid_sha256() -> None:
    for checksum in ("abc", "g" * 64):
        with pytest.raises(ValueError, match="checksum_sha256"):
            MediaAsset(
                asset_id="asset-1",
                job_id="job-1",
                media_type=MediaType.VIDEO,
                file_path="media/clip.mp4",
                checksum_sha256=checksum,
                provider_name="local-test",
                source_reference="fixture://clip",
            )


def test_timeline_requires_unique_item_ids() -> None:
    item = TimelineItem(
        item_id="item-1",
        asset_id="asset-1",
        start_seconds=0,
        duration_seconds=4,
        layer=0,
    )

    with pytest.raises(ValueError, match="unique"):
        Timeline(job_id="job-1", items=(item, item))


def test_render_artifact_validates_technical_metadata() -> None:
    artifact = RenderArtifact(
        artifact_id="render-1",
        job_id="job-1",
        file_path="renders/final.mp4",
        checksum_sha256=SHA256,
        codec="h264",
        resolution="1080x1920",
        duration_seconds=60,
        fps=30,
        audio_codec="aac",
        aspect_ratio="9:16",
        size_bytes=1_000_000,
    )

    assert artifact.fps == 30
    assert artifact.size_bytes == 1_000_000


def test_publish_job_metadata_is_read_only() -> None:
    job = PublishJob(
        publish_job_id="publish-1",
        job_id="job-1",
        platform="youtube",
        account_id="account-1",
        artifact_id="render-1",
        scheduled_at=UTC_NOW,
        metadata={"title": "Demo"},
    )

    assert job.state is JobState.PENDING
    with pytest.raises(TypeError):
        job.metadata["title"] = "Changed"  # type: ignore[index]


def test_provider_request_payload_is_deterministic() -> None:
    request = ProviderRequest(
        request_id="req-1",
        job_id="job-1",
        provider_name="local-test",
        operation="generate_video",
        payload={"z": 2, "a": 1},
    )

    assert tuple(request.payload.items()) == (("a", 1), ("z", 2))


def test_successful_provider_result_rejects_error_fields() -> None:
    with pytest.raises(ValueError, match="successful provider result"):
        ProviderResult(
            request_id="req-1",
            provider_name="provider",
            success=True,
            error_message="unexpected",
        )


def test_failed_provider_result_requires_error_message() -> None:
    with pytest.raises(ValueError, match="requires error_message"):
        ProviderResult(
            request_id="req-1",
            provider_name="provider",
            success=False,
        )


def test_validation_result_can_hold_messages() -> None:
    result = ValidationResult(
        validator="technical",
        passed=False,
        messages=("missing audio",),
    )

    assert result.messages == ("missing audio",)


def test_cost_record_rejects_negative_cost() -> None:
    with pytest.raises(ValueError, match="estimated_cost"):
        CostRecord(
            job_id="job-1",
            provider="provider",
            operation="generate",
            estimated_cost=-1,
            actual_cost=None,
            currency="USD",
            timestamp=UTC_NOW,
        )


def test_job_state_record_requires_real_transition() -> None:
    with pytest.raises(ValueError, match="must change state"):
        JobStateRecord(
            job_id="job-1",
            previous_state=JobState.RUNNING,
            new_state=JobState.RUNNING,
            reason="no change",
            timestamp=UTC_NOW,
        )


def test_job_state_record_allows_initial_transition() -> None:
    record = JobStateRecord(
        job_id="job-1",
        previous_state=None,
        new_state=JobState.PENDING,
        reason="job created",
        timestamp=UTC_NOW,
    )

    assert record.previous_state is None
    assert record.new_state is JobState.PENDING
