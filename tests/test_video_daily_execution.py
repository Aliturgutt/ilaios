from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from services.integrations.video_daily_execution import (
    CanonicalDailyVideoExecutionMaterializer,
)
from src.media_quality import (
    MediaAcceptanceGate,
    MediaKind,
    MediaQualityDomain,
    MediaQualityObservation,
    MediaRepairBudget,
)
from src.video_automation.daily_youtube_orchestration import DailyYouTubeOrchestrationError
from src.video_automation.episode_assembly_execution import EpisodeAssemblyArtifact
from src.video_automation.final_episode_acceptance import (
    FinalEpisodeAcceptanceDecision,
    FinalEpisodeAcceptanceIssue,
    FinalEpisodeAcceptanceStatus,
)
from src.video_automation.thumbnail_generation import ThumbnailArtifact


def _artifact(tmp_path: Path) -> EpisodeAssemblyArtifact:
    final_path = tmp_path / "final.mp4"
    final_path.write_bytes(b"accepted-final-video")
    body = final_path.read_bytes()
    return EpisodeAssemblyArtifact(
        artifact_id="artifact-001",
        request_id="request-001",
        episode_id="episode-001",
        executor_id="ffmpeg-concat-v1",
        output_path=str(final_path),
        sha256_hex=sha256(body).hexdigest(),
        byte_length=len(body),
        container_format="mp4",
        video_codec="h264",
        audio_codec="aac",
        width=1920,
        height=1080,
        frame_rate=24,
        source_asset_ids=("source-001",),
    )


def _final_acceptance(
    artifact: EpisodeAssemblyArtifact,
    *,
    accepted: bool = True,
) -> FinalEpisodeAcceptanceDecision:
    issues: tuple[FinalEpisodeAcceptanceIssue, ...] = ()
    status = FinalEpisodeAcceptanceStatus.ACCEPTED
    if not accepted:
        status = FinalEpisodeAcceptanceStatus.REJECTED
        issues = (FinalEpisodeAcceptanceIssue("qa_failed", "final QA failed"),)
    return FinalEpisodeAcceptanceDecision(
        decision_id="decision-001",
        artifact_id=artifact.artifact_id,
        technical_validation_id="technical-001",
        request_id=artifact.request_id,
        episode_id=artifact.episode_id,
        status=status,
        quality_checks=(),
        issues=issues,
        policy_id="policy-001",
    )


def _media_acceptance(artifact: EpisodeAssemblyArtifact):
    observation = MediaQualityObservation(
        observation_id="technical-observation-001",
        domain=MediaQualityDomain.TECHNICAL,
        artifact_sha256=artifact.sha256_hex,
        producer_id="video-producer",
        observer_id="technical-observer",
        score=1.0,
        threshold=1.0,
        evidence_ref="evidence://technical/final",
    )
    return MediaAcceptanceGate().evaluate(
        media_kind=MediaKind.VIDEO,
        artifact_sha256=artifact.sha256_hex,
        observations=(observation,),
        required_domains=(MediaQualityDomain.TECHNICAL,),
        repair_budget=MediaRepairBudget(max_total_attempts=0, max_attempts_per_target=0),
    )


def _thumbnail(tmp_path: Path, artifact: EpisodeAssemblyArtifact) -> ThumbnailArtifact:
    path = tmp_path / "thumbnail.jpg"
    path.write_bytes(b"accepted-thumbnail")
    body = path.read_bytes()
    return ThumbnailArtifact(
        thumbnail_id="thumbnail-001",
        request_id=artifact.request_id,
        source_artifact_sha256=artifact.sha256_hex,
        output_path=str(path),
        sha256_hex=sha256(body).hexdigest(),
        byte_length=len(body),
        width=1280,
        height=720,
        timestamp_ms=1000,
        renderer_id="ffmpeg-thumbnail-v1:frame-only",
        safe_text_rendered=False,
        provenance_reference="evidence://thumbnail/final",
    )


def test_materializer_binds_exact_accepted_artifact_to_daily_contract(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path)
    acceptance = _final_acceptance(artifact)
    media_acceptance = _media_acceptance(artifact)
    thumbnail = _thumbnail(tmp_path, artifact)

    execution = CanonicalDailyVideoExecutionMaterializer().materialize(
        artifact=artifact,
        final_acceptance=acceptance,
        media_acceptance=media_acceptance,
        thumbnail=thumbnail,
        job_id="job-001",
        title="Verified daily episode",
        description="Source-bound daily Video Factory episode.",
        encoding_evidence_ref="evidence://encoding/final",
        audio_mix_evidence_ref="evidence://audio/final",
    )

    assert execution.artifact is artifact
    assert execution.acceptance is acceptance
    assert execution.product.final_sha256 == artifact.sha256_hex
    assert execution.product.thumbnail_sha256 == thumbnail.sha256_hex
    assert execution.thumbnail_path == thumbnail.output_path


def test_materializer_fails_closed_on_rejected_or_mismatched_evidence(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path)
    media_acceptance = _media_acceptance(artifact)
    thumbnail = _thumbnail(tmp_path, artifact)
    materializer = CanonicalDailyVideoExecutionMaterializer()

    with pytest.raises(DailyYouTubeOrchestrationError, match="final episode acceptance"):
        materializer.materialize(
            artifact=artifact,
            final_acceptance=_final_acceptance(artifact, accepted=False),
            media_acceptance=media_acceptance,
            thumbnail=thumbnail,
            job_id="job-001",
            title="Verified daily episode",
            description="Source-bound daily Video Factory episode.",
            encoding_evidence_ref="evidence://encoding/final",
            audio_mix_evidence_ref="evidence://audio/final",
        )

    wrong_thumbnail = ThumbnailArtifact(
        thumbnail_id=thumbnail.thumbnail_id,
        request_id=thumbnail.request_id,
        source_artifact_sha256="f" * 64,
        output_path=thumbnail.output_path,
        sha256_hex=thumbnail.sha256_hex,
        byte_length=thumbnail.byte_length,
        width=thumbnail.width,
        height=thumbnail.height,
        timestamp_ms=thumbnail.timestamp_ms,
        renderer_id=thumbnail.renderer_id,
        safe_text_rendered=thumbnail.safe_text_rendered,
        provenance_reference=thumbnail.provenance_reference,
    )
    with pytest.raises(DailyYouTubeOrchestrationError, match="thumbnail"):
        materializer.materialize(
            artifact=artifact,
            final_acceptance=_final_acceptance(artifact),
            media_acceptance=media_acceptance,
            thumbnail=wrong_thumbnail,
            job_id="job-001",
            title="Verified daily episode",
            description="Source-bound daily Video Factory episode.",
            encoding_evidence_ref="evidence://encoding/final",
            audio_mix_evidence_ref="evidence://audio/final",
        )
