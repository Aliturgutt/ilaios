from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from src.video_automation.final_episode_acceptance import (
    FinalEpisodeAcceptanceDecision,
    FinalEpisodeAcceptanceIssue,
    FinalEpisodeAcceptanceStatus,
)
from src.video_automation.finished_product import (
    FinishedProductError,
    FinishedVideoFinalizer,
    FinishedVideoInputs,
    FinishedVideoManifestStore,
)


_ARTIFACT = b"deterministic-finished-video"


def _inputs() -> FinishedVideoInputs:
    return FinishedVideoInputs(
        episode_id="episode-001",
        request_id="request-001",
        final_artifact_reference="artifact://episode-001/final.mp4",
        final_artifact_sha256=sha256(_ARTIFACT).hexdigest(),
        duration_seconds=60,
        resolution="1920x1080",
        script_reference="evidence://script/001",
        shot_plan_reference="evidence://shots/001",
        generated_clip_references=("artifact://clip/001",),
        voice_dialogue_references=("artifact://voice/001",),
        music_references=("artifact://music/001",),
        sfx_references=("artifact://sfx/001",),
        caption_artifact_reference="artifact://captions/001.vtt",
        edit_timeline_evidence_ref="evidence://timeline/001",
        technical_validation_ref="evidence://technical/001",
        visual_quality_evidence_ref="evidence://visual/001",
        audio_quality_evidence_ref="evidence://audio/001",
        brand_quality_evidence_ref="evidence://brand/001",
        continuity_evidence_ref="evidence://continuity/001",
        thumbnail_reference="artifact://thumbnail/001.jpg",
    )


def _accepted() -> FinalEpisodeAcceptanceDecision:
    return FinalEpisodeAcceptanceDecision(
        decision_id="acceptance-001",
        artifact_id="artifact-001",
        technical_validation_id="technical-001",
        request_id="request-001",
        episode_id="episode-001",
        status=FinalEpisodeAcceptanceStatus.ACCEPTED,
        quality_checks=(),
        issues=(),
        policy_id="policy-001",
    )


def test_finished_video_requires_canonical_final_acceptance() -> None:
    rejected = replace(
        _accepted(),
        status=FinalEpisodeAcceptanceStatus.REJECTED,
        issues=(FinalEpisodeAcceptanceIssue("quality_failed", "quality failed"),),
    )
    with pytest.raises(FinishedProductError, match="must be ACCEPTED"):
        FinishedVideoFinalizer().finalize(
            _inputs(), acceptance=rejected, final_artifact_bytes=_ARTIFACT
        )


def test_finished_video_rejects_partial_evidence() -> None:
    with pytest.raises(FinishedProductError, match="music_references"):
        replace(_inputs(), music_references=())


def test_finished_video_is_bound_to_exact_artifact_bytes() -> None:
    with pytest.raises(FinishedProductError, match="SHA-256"):
        FinishedVideoFinalizer().finalize(
            _inputs(), acceptance=_accepted(), final_artifact_bytes=b"different"
        )


def test_finished_manifest_persists_immutably_across_restart(tmp_path: Path) -> None:
    manifest = FinishedVideoFinalizer().finalize(
        _inputs(), acceptance=_accepted(), final_artifact_bytes=_ARTIFACT
    )
    store = FinishedVideoManifestStore(tmp_path)
    first = store.persist(manifest)
    second = store.persist(manifest)
    assert first == second

    restarted = FinishedVideoManifestStore(tmp_path)
    loaded = restarted.load("episode-001")
    assert loaded == manifest
    assert len(loaded.manifest_sha256) == 64

    changed = replace(manifest, thumbnail_reference="artifact://thumbnail/changed.jpg")
    with pytest.raises(FinishedProductError, match="immutable"):
        restarted.persist(changed)
