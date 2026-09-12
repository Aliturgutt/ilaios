"""Bind existing accepted Video outputs into the canonical daily execution contract.

This adapter does not create a Video runtime, QA authority, scheduler, publisher,
or acceptance gate. It only materializes the exact already-accepted assembly,
media-acceptance evidence, thumbnail, and finished-product certification into the
existing ``CanonicalDailyVideoExecution`` contract consumed by the daily YouTube
orchestrator.
"""

from __future__ import annotations

from src.media_quality import MediaAcceptanceEvidence, MediaKind
from src.video_automation.daily_youtube_orchestration import (
    CanonicalDailyVideoExecution,
    DailyYouTubeOrchestrationError,
)
from src.video_automation.episode_assembly_execution import EpisodeAssemblyArtifact
from src.video_automation.final_episode_acceptance import (
    FinalEpisodeAcceptanceDecision,
    FinalEpisodeAcceptanceStatus,
)
from src.video_automation.finished_product import FinishedProductCertifier
from src.video_automation.thumbnail_generation import ThumbnailArtifact


class CanonicalDailyVideoExecutionMaterializer:
    """Materialize one daily execution from existing canonical acceptance evidence."""

    def __init__(self, certifier: FinishedProductCertifier | None = None) -> None:
        self._certifier = certifier or FinishedProductCertifier()

    def materialize(
        self,
        *,
        artifact: EpisodeAssemblyArtifact,
        final_acceptance: FinalEpisodeAcceptanceDecision,
        media_acceptance: MediaAcceptanceEvidence,
        thumbnail: ThumbnailArtifact,
        job_id: str,
        title: str,
        description: str,
        encoding_evidence_ref: str,
        audio_mix_evidence_ref: str,
    ) -> CanonicalDailyVideoExecution:
        """Return the Daily contract only when every input binds to one final MP4."""

        if final_acceptance.status is not FinalEpisodeAcceptanceStatus.ACCEPTED:
            raise DailyYouTubeOrchestrationError(
                "daily execution requires canonical final episode acceptance"
            )
        if final_acceptance.artifact_id != artifact.artifact_id:
            raise DailyYouTubeOrchestrationError(
                "daily final acceptance references another assembly artifact"
            )
        if final_acceptance.request_id != artifact.request_id:
            raise DailyYouTubeOrchestrationError(
                "daily final acceptance request identity mismatch"
            )
        if final_acceptance.episode_id != artifact.episode_id:
            raise DailyYouTubeOrchestrationError(
                "daily final acceptance episode identity mismatch"
            )
        if media_acceptance.media_kind is not MediaKind.VIDEO:
            raise DailyYouTubeOrchestrationError(
                "daily finished product requires VIDEO media acceptance"
            )
        if not media_acceptance.accepted:
            raise DailyYouTubeOrchestrationError(
                "daily finished product requires accepted media evidence"
            )
        if media_acceptance.artifact_sha256 != artifact.sha256_hex:
            raise DailyYouTubeOrchestrationError(
                "daily media acceptance SHA does not match assembly artifact"
            )
        if thumbnail.source_artifact_sha256 != artifact.sha256_hex:
            raise DailyYouTubeOrchestrationError(
                "daily thumbnail is not bound to the accepted assembly artifact"
            )

        product = self._certifier.certify(
            job_id=job_id,
            final_path=artifact.output_path,
            acceptance=media_acceptance,
            encoding_evidence_ref=encoding_evidence_ref,
            audio_mix_evidence_ref=audio_mix_evidence_ref,
            title=title,
            description=description,
            thumbnail=thumbnail,
            thumbnail_required=True,
        )
        return CanonicalDailyVideoExecution(
            artifact=artifact,
            acceptance=final_acceptance,
            product=product,
            thumbnail_path=thumbnail.output_path,
            thumbnail_sha256=thumbnail.sha256_hex,
        )


__all__ = ["CanonicalDailyVideoExecutionMaterializer"]
