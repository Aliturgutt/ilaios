from __future__ import annotations

from pathlib import Path

import pytest

from services.integrations.video_series_context import (
    VideoSeriesContextError,
    resolve_authenticated_video_series_context,
)
from services.integrations.video_series_execution import (
    accept_authenticated_video_series_result,
    begin_authenticated_video_series_execution,
)
from src.video_automation.series_state import (
    AcceptedEpisodeManifest,
    CharacterBibleEntry,
    EpisodePublicationState,
    SeriesBible,
    SeriesState,
    SeriesStateStore,
)


def _state() -> SeriesState:
    return SeriesState(
        series_id="series-001",
        tenant_id="tenant-001",
        user_id="user-001",
        title="Neon Continuum",
        objective="Create accepted continuation episodes",
        premise="A courier protects a memory archive.",
        schedule_spec="daily@19:00 Europe/Istanbul",
        bible_revision=1,
        open_story_threads=("archive origin",),
    )


def _bible() -> SeriesBible:
    return SeriesBible(
        series_id="series-001",
        revision=1,
        premise="A courier protects a memory archive.",
        world_rules=("memories are physical keys",),
        characters=(
            CharacterBibleEntry(
                character_id="mira",
                name="Mira",
                appearance="short dark hair, amber cybernetic eye",
                wardrobe_constraints=("black courier jacket",),
                personality="calm and observant",
                voice_identity="voice:mira:v1",
            ),
        ),
        cinematography="controlled handheld",
        visual_style="grounded cyberpunk realism",
        color_language="cyan practicals with amber highlights",
        lighting="motivated night lighting",
        locations=("Lower Arcology",),
        camera_rules=("no impossible camera teleportation",),
        aspect_ratio="16:9",
        format_constraints=("60 second maximum",),
        music_language="restrained electronic pulse",
        ambience="dense urban night ambience",
        sfx_language="tactile mechanical detail",
        mixing_constraints=("dialogue remains intelligible",),
        story_arc="discover the archive creator",
        season_constraints=("do not reveal creator before finale",),
    )


def _manifest(
    *,
    episode_id: str,
    episode_number: int,
    artifact_sha256: str,
    summary: str,
) -> AcceptedEpisodeManifest:
    return AcceptedEpisodeManifest(
        series_id="series-001",
        episode_id=episode_id,
        episode_number=episode_number,
        episode_objective=summary,
        final_acceptance_id=f"acceptance-{episode_number:03d}",
        final_artifact_reference=f"artifact://{episode_id}/final.mp4",
        final_artifact_sha256=artifact_sha256,
        duration_seconds=60,
        resolution="1920x1080",
        script_reference=f"evidence://script/{episode_number:03d}",
        shot_plan_reference=f"evidence://shot-plan/{episode_number:03d}",
        generated_clip_references=(f"artifact://clip/{episode_number:03d}",),
        source_reference_assets=("artifact://source/logo",),
        provider_model_evidence_refs=(f"evidence://provider/{episode_number:03d}",),
        voice_references=("artifact://voice/mira",),
        music_references=(f"artifact://music/{episode_number:03d}",),
        sfx_references=(f"artifact://sfx/{episode_number:03d}",),
        caption_artifact_reference=f"artifact://captions/{episode_number:03d}.vtt",
        edit_timeline_evidence_ref=f"evidence://timeline/{episode_number:03d}",
        technical_validation_ref=f"evidence://technical/{episode_number:03d}",
        visual_quality_evidence_ref=f"evidence://visual/{episode_number:03d}",
        audio_quality_evidence_ref=f"evidence://audio/{episode_number:03d}",
        brand_evidence_ref=f"evidence://brand/{episode_number:03d}",
        continuity_evidence_ref=f"evidence://continuity/{episode_number:03d}",
        final_frame_reference=f"artifact://frame/final-{episode_number:03d}.png",
        character_reference_frames=(f"artifact://frame/mira-{episode_number:03d}.png",),
        location_reference_frames=(f"artifact://frame/location-{episode_number:03d}.png",),
        visual_style_fingerprint="style-fingerprint-001",
        color_language="cyan practicals with amber highlights",
        episode_summary=summary,
        open_narrative_threads=("archive origin", "unknown broadcast recipient"),
        resolved_narrative_threads=(f"episode-{episode_number}-objective",),
        accepted_at="2026-09-12T06:00:00+00:00",
        bible_revision=1,
    )


def _store_with_episode_one(tmp_path: Path) -> SeriesStateStore:
    store = SeriesStateStore(tmp_path)
    store.create_series(_state(), _bible())
    first = _manifest(
        episode_id="episode-001",
        episode_number=1,
        artifact_sha256="a" * 64,
        summary="Mira recovers the first archive shard.",
    )
    store.begin_episode(series_id="series-001", episode_id="episode-001", episode_number=1)
    store.accept_episode(
        first,
        publication_state=EpisodePublicationState.PENDING_EXTERNAL_AUTHORIZATION,
    )
    return store


def _context(store: SeriesStateStore):
    return resolve_authenticated_video_series_context(
        store,
        series_id="series-001",
        tenant_id="tenant-001",
        user_id="user-001",
    )


def test_series_execution_promotes_only_matching_accepted_final_artifact(tmp_path: Path) -> None:
    store = _store_with_episode_one(tmp_path)
    execution = begin_authenticated_video_series_execution(
        store,
        _context(store),
        episode_id="episode-002",
    )
    manifest = _manifest(
        episode_id="episode-002",
        episode_number=2,
        artifact_sha256="b" * 64,
        summary="Mira follows the broadcast trace.",
    )

    state = accept_authenticated_video_series_result(
        store,
        execution,
        manifest,
        {
            "final_stage": "completed",
            "qa": {"passed": True},
            "artifact_digest": "b" * 64,
        },
    )

    assert state.next_episode_number == 3
    assert state.latest_accepted_episode_id == "episode-002"
    assert state.latest_artifact_sha256 == "b" * 64


def test_series_execution_denies_failed_qa_or_digest_substitution(tmp_path: Path) -> None:
    store = _store_with_episode_one(tmp_path)
    execution = begin_authenticated_video_series_execution(
        store,
        _context(store),
        episode_id="episode-002",
    )
    manifest = _manifest(
        episode_id="episode-002",
        episode_number=2,
        artifact_sha256="b" * 64,
        summary="Mira follows the broadcast trace.",
    )

    with pytest.raises(VideoSeriesContextError, match="QA acceptance"):
        accept_authenticated_video_series_result(
            store,
            execution,
            manifest,
            {"final_stage": "completed", "qa": {"passed": False}, "artifact_digest": "b" * 64},
        )
    with pytest.raises(VideoSeriesContextError, match="does not match accepted manifest"):
        accept_authenticated_video_series_result(
            store,
            execution,
            manifest,
            {"final_stage": "completed", "qa": {"passed": True}, "artifact_digest": "c" * 64},
        )

    assert store.load_series("series-001").next_episode_number == 2


def test_series_execution_restart_recovers_manifest_without_duplicate_promotion(tmp_path: Path) -> None:
    store = _store_with_episode_one(tmp_path)
    execution = begin_authenticated_video_series_execution(
        store,
        _context(store),
        episode_id="episode-002",
    )
    manifest = _manifest(
        episode_id="episode-002",
        episode_number=2,
        artifact_sha256="b" * 64,
        summary="Mira follows the broadcast trace.",
    )
    store.persist_accepted_manifest(
        manifest,
        publication_state=EpisodePublicationState.PENDING_EXTERNAL_AUTHORIZATION,
    )

    restarted = SeriesStateStore(tmp_path)
    recovered = restarted.recover_series_from_manifests("series-001")

    assert recovered.next_episode_number == 3
    assert recovered.latest_accepted_episode_id == execution.episode_id
    assert restarted.recover_series_from_manifests("series-001") == recovered


def test_series_execution_rejects_stale_context_after_other_acceptance(tmp_path: Path) -> None:
    store = _store_with_episode_one(tmp_path)
    stale_context = _context(store)
    first_execution = begin_authenticated_video_series_execution(
        store,
        stale_context,
        episode_id="episode-002",
    )
    manifest = _manifest(
        episode_id="episode-002",
        episode_number=2,
        artifact_sha256="b" * 64,
        summary="Mira follows the broadcast trace.",
    )
    accept_authenticated_video_series_result(
        store,
        first_execution,
        manifest,
        {"final_stage": "completed", "qa": {"passed": True}, "artifact_digest": "b" * 64},
    )

    with pytest.raises(VideoSeriesContextError):
        begin_authenticated_video_series_execution(
            store,
            stale_context,
            episode_id="episode-003",
        )
