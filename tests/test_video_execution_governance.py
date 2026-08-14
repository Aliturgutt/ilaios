from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from services.integrations.video_acceptance import (
    REQUIRED_VIDEO_QUALITY_CHECKS,
    VideoFinalAcceptanceCoordinator,
    VideoFinalAcceptanceError,
)
from services.integrations.video_editing import (
    GovernedVideoEditExecutor,
    edit_skill_id,
)
from services.integrations.video_publishing import GovernedVideoPublishingExecutor
from services.integrations.video_skill_governance import approve_video_skills
from services.runtime.routing import AgentProfile, RuntimeError, SkillRegistry
from src.video_automation.assembled_output_technical_validation import (
    AssembledOutputTechnicalValidation,
    AssembledOutputTechnicalValidationStatus,
)
from src.video_automation.episode_assembly_execution import EpisodeAssemblyArtifact
from src.video_automation.final_episode_acceptance import (
    FinalEpisodeAcceptancePolicy,
    FinalEpisodeAcceptanceStatus,
)
from src.video_automation.media_technical_validation import MediaProbeObservation
from src.video_automation.publishing_execution import (
    PlatformPublishingObservation,
    PublishingExecutionReport,
    PublishingExecutionStatus,
)
from src.video_automation.publishing_package_preparation import (
    EpisodePublishingPackageManifest,
    PlatformPublishingPackage,
)
from src.video_automation.video_editing import EditExecutionResult
from src.video_automation.video_quality import (
    QaObservationSource,
    VideoQaObservation,
    VideoQualityFoundation,
)
from src.video_automation.video_skills import EditKind, EditOperation, QaDomain

ARTIFACT_SHA = "a" * 64


class _RecordingEditExecution:
    def __init__(self) -> None:
        self.calls: list[EditOperation] = []

    def execute(self, operation: EditOperation) -> EditExecutionResult:
        self.calls.append(operation)
        return EditExecutionResult(
            operation_id=operation.operation_id,
            output_asset_id=operation.output_asset_id,
            output_path="/evidence/edited.mp4",
            sha256_hex="c" * 64,
            byte_length=128,
            command=("ffmpeg", operation.kind.value),
        )


class _RecordingPublishingExecution:
    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self, manifest: EpisodePublishingPackageManifest
    ) -> PublishingExecutionReport:
        self.calls += 1
        package = manifest.packages[0]
        observation = PlatformPublishingObservation(
            package_id=package.package_id,
            platform=package.platform,
            account_id=package.account_id,
            status=PublishingExecutionStatus.SUCCEEDED,
            provider_name="test-publisher",
            platform_post_id="post-001",
            published_url="https://example.invalid/post-001",
        )
        return PublishingExecutionReport(
            report_id="publishing-report-001",
            manifest_id=manifest.manifest_id,
            episode_id=manifest.episode_id,
            observations=(observation,),
            package_count=1,
            succeeded_count=1,
            failed_count=0,
        )


def _registry() -> SkillRegistry:
    registry = SkillRegistry()
    approve_video_skills(registry)
    return registry


def _edit_operation(kind: EditKind = EditKind.TRIM) -> EditOperation:
    parameters: dict[str, str | int | float | bool]
    inputs: tuple[str, ...]
    if kind is EditKind.TRIM:
        parameters = {"start_seconds": 0.0, "duration_seconds": 1.0}
        inputs = ("input-1",)
    elif kind is EditKind.CONCATENATE:
        parameters = {}
        inputs = ("input-1", "input-2")
    elif kind is EditKind.OVERLAY:
        parameters = {"x": 0, "y": 0}
        inputs = ("input-1", "input-2")
    elif kind is EditKind.CROP:
        parameters = {"width": 100, "height": 100, "x": 0, "y": 0}
        inputs = ("input-1",)
    elif kind is EditKind.SCALE:
        parameters = {
            "width": 720,
            "height": 1280,
            "fps": 30,
            "video_codec": "libx264",
            "audio_codec": "aac",
        }
        inputs = ("input-1",)
    else:
        parameters = {}
        inputs = ("input-1", "input-2")
    return EditOperation("edit-001", kind, inputs, "output-001", parameters)


def _publishing_manifest() -> EpisodePublishingPackageManifest:
    package = PlatformPublishingPackage(
        package_id="publishing-package-001",
        episode_id="episode-001",
        artifact_id="artifact-001",
        acceptance_decision_id="acceptance-001",
        platform="example",
        account_id="account-001",
        media_path="/evidence/final.mp4",
        media_sha256_hex=ARTIFACT_SHA,
        media_byte_length=1024,
        scheduled_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
        visibility="private",
        title="ILAIOS Video",
        description="Governed publishing test",
        tags=("ilaios",),
    )
    return EpisodePublishingPackageManifest(
        manifest_id="publishing-manifest-001",
        episode_id=package.episode_id,
        artifact_id=package.artifact_id,
        acceptance_decision_id=package.acceptance_decision_id,
        packages=(package,),
        package_count=1,
    )


def _artifact(sha: str = ARTIFACT_SHA) -> EpisodeAssemblyArtifact:
    return EpisodeAssemblyArtifact(
        artifact_id="artifact-001",
        request_id="assembly-request-001",
        episode_id="episode-001",
        executor_id="ffmpeg-concat-v1",
        output_path="/evidence/final.mp4",
        sha256_hex=sha,
        byte_length=1024,
        container_format="mp4",
        video_codec="h264",
        audio_codec="aac",
        width=1080,
        height=1920,
        frame_rate=30,
        source_asset_ids=("source-001",),
    )


def _technical_validation(
    sha: str = ARTIFACT_SHA,
) -> AssembledOutputTechnicalValidation:
    return AssembledOutputTechnicalValidation(
        validation_id="technical-validation-001",
        artifact_id="artifact-001",
        request_id="assembly-request-001",
        episode_id="episode-001",
        output_path="/evidence/final.mp4",
        sha256_hex=sha,
        byte_length=1024,
        status=AssembledOutputTechnicalValidationStatus.PASSED,
        observation=MediaProbeObservation(
            container="mp4",
            duration_seconds=4.0,
            width=1080,
            height=1920,
            frames_per_second=30.0,
            video_codec="h264",
            audio_codec="aac",
            video_stream_count=1,
            audio_stream_count=1,
        ),
        issues=(),
        probe_id="ffprobe-json-v1",
    )


def _qa_observations(
    sha: str = ARTIFACT_SHA,
    *,
    failing: QaDomain | None = None,
) -> tuple[VideoQaObservation, ...]:
    return tuple(
        VideoQaObservation(
            observation_id=f"observation-{domain.value}",
            domain=domain,
            artifact_sha256=sha,
            observer_id=f"observer-{domain.value}",
            producer_id="video-producer",
            source=(
                QaObservationSource.DETERMINISTIC_PROBE
                if domain is QaDomain.TECHNICAL
                else QaObservationSource.INDEPENDENT_MODEL
            ),
            score=0.2 if domain is failing else 0.95,
            threshold=0.8,
            evidence_reference=f"evidence:{domain.value}",
            provenance_reference=f"provenance:{domain.value}",
            repair_target=(f"scene:{domain.value}" if domain is failing else None),
        )
        for domain in QaDomain
    )


def _acceptance_policy() -> FinalEpisodeAcceptancePolicy:
    return FinalEpisodeAcceptancePolicy(
        required_quality_checks=REQUIRED_VIDEO_QUALITY_CHECKS,
        min_duration_seconds=1.0,
        max_duration_seconds=10.0,
        require_audio_stream=True,
        min_source_asset_count=1,
    )


def test_edit_kinds_map_to_exact_native_skill_ids() -> None:
    assert {kind: edit_skill_id(kind) for kind in EditKind} == {
        EditKind.TRIM: "ilaios.skill.video.edit.trim",
        EditKind.CONCATENATE: "ilaios.skill.video.edit.concatenate",
        EditKind.OVERLAY: "ilaios.skill.video.edit.overlay",
        EditKind.CROP: "ilaios.skill.video.edit.crop",
        EditKind.SCALE: "ilaios.skill.video.edit.scale",
        EditKind.AUDIO_MIX: "ilaios.skill.video.edit.audio-mix",
    }


def test_governed_edit_refuses_mutation_without_media_write() -> None:
    executor = _RecordingEditExecution()
    governed = GovernedVideoEditExecutor(
        _registry(),
        AgentProfile("edit-worker", frozenset({"media.read"})),
        executor,
    )
    with pytest.raises(RuntimeError, match="expand agent authority"):
        governed.execute(_edit_operation())
    assert executor.calls == []


def test_governed_edit_delegates_after_exact_skill_validation() -> None:
    executor = _RecordingEditExecution()
    operation = _edit_operation(EditKind.CROP)
    result = GovernedVideoEditExecutor(
        _registry(),
        AgentProfile("edit-worker", frozenset({"media.read", "media.write"})),
        executor,
    ).execute(operation)
    assert executor.calls == [operation]
    assert result.operation_id == operation.operation_id


def test_governed_publish_refuses_side_effect_without_social_authority() -> None:
    executor = _RecordingPublishingExecution()
    governed = GovernedVideoPublishingExecutor(
        _registry(),
        AgentProfile("publish-worker", frozenset({"media.read"})),
        executor,
    )
    with pytest.raises(RuntimeError, match="expand agent authority"):
        governed.execute(_publishing_manifest())
    assert executor.calls == 0


def test_governed_publish_delegates_only_after_external_authority_validation() -> None:
    executor = _RecordingPublishingExecution()
    report = GovernedVideoPublishingExecutor(
        _registry(),
        AgentProfile(
            "publish-worker",
            frozenset({"media.read", "social.publish"}),
        ),
        executor,
    ).execute(_publishing_manifest())
    assert executor.calls == 1
    assert report.succeeded_count == 1


def test_final_acceptance_requires_policy_to_cover_all_four_qa_domains() -> None:
    with pytest.raises(VideoFinalAcceptanceError, match="missing QA domains"):
        VideoFinalAcceptanceCoordinator(
            FinalEpisodeAcceptancePolicy(
                required_quality_checks=(
                    "visual_quality",
                    "audio_quality",
                    "technical_quality",
                ),
                min_duration_seconds=1.0,
                max_duration_seconds=10.0,
            )
        )


def test_four_domain_qa_can_enter_existing_final_acceptance_gate() -> None:
    run = VideoQualityFoundation().evaluate(
        ARTIFACT_SHA,
        _qa_observations(),
        evaluator_id="final-evaluator",
    )
    decision = VideoFinalAcceptanceCoordinator(_acceptance_policy()).evaluate(
        _artifact(),
        _technical_validation(),
        run,
    )
    assert decision.status is FinalEpisodeAcceptanceStatus.ACCEPTED
    assert {check.check_code for check in decision.quality_checks} == set(
        REQUIRED_VIDEO_QUALITY_CHECKS
    )


def test_failed_qa_domain_is_rejected_by_existing_final_acceptance_gate() -> None:
    run = VideoQualityFoundation().evaluate(
        ARTIFACT_SHA,
        _qa_observations(failing=QaDomain.BRAND),
        evaluator_id="final-evaluator",
    )
    decision = VideoFinalAcceptanceCoordinator(_acceptance_policy()).evaluate(
        _artifact(),
        _technical_validation(),
        run,
    )
    assert decision.status is FinalEpisodeAcceptanceStatus.REJECTED
    assert "quality_check_failed:brand_quality" in {
        issue.code for issue in decision.issues
    }


def test_final_acceptance_rejects_qa_for_a_different_artifact() -> None:
    different_sha = "b" * 64
    run = VideoQualityFoundation().evaluate(
        different_sha,
        _qa_observations(different_sha),
        evaluator_id="final-evaluator",
    )
    with pytest.raises(VideoFinalAcceptanceError, match="does not match assembly"):
        VideoFinalAcceptanceCoordinator(_acceptance_policy()).evaluate(
            _artifact(),
            _technical_validation(),
            run,
        )


def test_final_acceptance_rejects_forged_evaluator_independence() -> None:
    run = VideoQualityFoundation().evaluate(
        ARTIFACT_SHA,
        _qa_observations(),
        evaluator_id="final-evaluator",
    )
    forged = replace(
        run,
        evaluation=replace(run.evaluation, evaluator_id="observer-visual"),
    )
    with pytest.raises(VideoFinalAcceptanceError, match="remain independent"):
        VideoFinalAcceptanceCoordinator(_acceptance_policy()).evaluate(
            _artifact(),
            _technical_validation(),
            forged,
        )
