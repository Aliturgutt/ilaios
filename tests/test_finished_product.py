from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from src.media_quality import (
    MediaAcceptanceGate,
    MediaAcceptanceEvidence,
    MediaKind,
    MediaQualityDomain,
    MediaQualityObservation,
    MediaRepairBudget,
    video_required_domains,
)
from src.video_automation.caption_subtitle import CaptionCue, CaptionSubtitleEngine
from src.video_automation.finished_product import (
    FinishedProductCertifier,
    FinishedProductError,
)
from src.video_automation.thumbnail_generation import ThumbnailArtifact


def _acceptance(artifact_sha: str, *, visual_score: float = 0.95) -> MediaAcceptanceEvidence:
    observations: list[MediaQualityObservation] = []
    for domain in video_required_domains():
        score = visual_score if domain is MediaQualityDomain.VISUAL else 0.95
        observations.append(
            MediaQualityObservation(
                observation_id=f"obs-{domain.value.lower()}",
                domain=domain,
                artifact_sha256=artifact_sha,
                producer_id="renderer",
                observer_id=f"observer-{domain.value.lower()}",
                score=score,
                threshold=0.8,
                evidence_ref=f"evidence://quality/{domain.value.lower()}",
                repair_target=None if score >= 0.8 else "final-render",
            )
        )
    return MediaAcceptanceGate().evaluate(
        media_kind=MediaKind.VIDEO,
        artifact_sha256=artifact_sha,
        observations=tuple(observations),
        required_domains=video_required_domains(),
        repair_budget=MediaRepairBudget(max_total_attempts=1, max_attempts_per_target=1),
    )


def _final_video(tmp_path: Path) -> tuple[Path, str]:
    path = tmp_path / "final.mp4"
    path.write_bytes(b"final-encoded-video-bytes")
    return path, sha256(path.read_bytes()).hexdigest()


def test_failed_qa_artifact_cannot_be_labeled_finished(tmp_path: Path) -> None:
    path, digest = _final_video(tmp_path)

    with pytest.raises(FinishedProductError, match="failed-QA"):
        FinishedProductCertifier().certify(
            job_id="job-001",
            final_path=path,
            acceptance=_acceptance(digest, visual_score=0.2),
            encoding_evidence_ref="evidence://ffmpeg/final-encode",
            audio_mix_evidence_ref="evidence://audio/final-mix",
            title="Title",
            description="Description",
        )


def test_final_file_must_match_exact_accepted_sha(tmp_path: Path) -> None:
    path, _ = _final_video(tmp_path)

    with pytest.raises(FinishedProductError, match="SHA does not match"):
        FinishedProductCertifier().certify(
            job_id="job-001",
            final_path=path,
            acceptance=_acceptance("a" * 64),
            encoding_evidence_ref="evidence://ffmpeg/final-encode",
            audio_mix_evidence_ref="evidence://audio/final-mix",
            title="Title",
            description="Description",
        )


def test_required_caption_and_thumbnail_evidence_are_enforced(tmp_path: Path) -> None:
    path, digest = _final_video(tmp_path)

    with pytest.raises(FinishedProductError, match="requires captions"):
        FinishedProductCertifier().certify(
            job_id="job-001",
            final_path=path,
            acceptance=_acceptance(digest),
            encoding_evidence_ref="evidence://ffmpeg/final-encode",
            audio_mix_evidence_ref="evidence://audio/final-mix",
            title="Title",
            description="Description",
            captions_required=True,
        )


def test_finished_product_binds_final_video_captions_thumbnail_and_metadata(
    tmp_path: Path,
) -> None:
    path, digest = _final_video(tmp_path)
    captions = CaptionSubtitleEngine().export(
        job_id="job-001",
        cues=(CaptionCue("cue-1", "Hello", 0.0, 1.0),),
        timing_source="script",
        output_directory=tmp_path / "captions",
    )
    thumbnail_path = tmp_path / "thumbnail.jpg"
    thumbnail_path.write_bytes(b"thumbnail-bytes")
    thumbnail_digest = sha256(thumbnail_path.read_bytes()).hexdigest()
    thumbnail = ThumbnailArtifact(
        thumbnail_id="thumbnail-001",
        request_id="thumbnail-request-001",
        source_artifact_sha256=digest,
        output_path=str(thumbnail_path),
        sha256_hex=thumbnail_digest,
        byte_length=thumbnail_path.stat().st_size,
        width=1280,
        height=720,
        timestamp_ms=0,
        renderer_id="test-renderer",
        safe_text_rendered=False,
        provenance_reference="evidence://thumbnail/provenance",
    )

    product = FinishedProductCertifier().certify(
        job_id="job-001",
        final_path=path,
        acceptance=_acceptance(digest),
        encoding_evidence_ref="evidence://ffmpeg/final-encode",
        audio_mix_evidence_ref="evidence://audio/final-mix",
        title="Finished title",
        description="Finished description",
        captions=captions,
        thumbnail=thumbnail,
        captions_required=True,
        thumbnail_required=True,
    )

    assert product.final_sha256 == digest
    assert product.byte_length == path.stat().st_size
    assert product.caption_manifest_sha256 is not None
    assert product.thumbnail_sha256 == thumbnail_digest
    assert product.product_id.startswith("finished-video-")
