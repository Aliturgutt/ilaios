from __future__ import annotations

from pathlib import Path

import pytest

from services.integrations.video_series_context import (
    AuthenticatedVideoSeriesContext,
    VideoSeriesContextError,
    bind_series_context_to_objective_resolver,
    resolve_authenticated_video_series_context,
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


def _manifest() -> AcceptedEpisodeManifest:
    return AcceptedEpisodeManifest(
        series_id="series-001",
        episode_id="episode-001",
        episode_number=1,
        episode_objective="Mira recovers the first archive shard.",
        final_acceptance_id="acceptance-001",
        final_artifact_reference="artifact://episode-001/final.mp4",
        final_artifact_sha256="a" * 64,
        duration_seconds=60,
        resolution="1920x1080",
        script_reference="evidence://script/001",
        shot_plan_reference="evidence://shot-plan/001",
        generated_clip_references=("artifact://clip/001",),
        source_reference_assets=("artifact://source/logo",),
        provider_model_evidence_refs=("evidence://provider/001",),
        voice_references=("artifact://voice/mira",),
        music_references=("artifact://music/001",),
        sfx_references=("artifact://sfx/001",),
        caption_artifact_reference="artifact://captions/001.vtt",
        edit_timeline_evidence_ref="evidence://timeline/001",
        technical_validation_ref="evidence://technical/001",
        visual_quality_evidence_ref="evidence://visual/001",
        audio_quality_evidence_ref="evidence://audio/001",
        brand_evidence_ref="evidence://brand/001",
        continuity_evidence_ref="evidence://continuity/001",
        final_frame_reference="artifact://frame/final-001.png",
        character_reference_frames=("artifact://frame/mira-001.png",),
        location_reference_frames=("artifact://frame/location-001.png",),
        visual_style_fingerprint="style-fingerprint-001",
        color_language="cyan practicals with amber highlights",
        episode_summary="Mira secures the shard but learns it is broadcasting.",
        open_narrative_threads=("archive origin", "unknown broadcast recipient"),
        resolved_narrative_threads=("first shard location",),
        accepted_at="2026-09-12T04:00:00+00:00",
        bible_revision=1,
    )


def _store(tmp_path: Path, *, accepted: bool) -> SeriesStateStore:
    store = SeriesStateStore(tmp_path)
    store.create_series(_state(), _bible())
    if accepted:
        store.begin_episode(
            series_id="series-001",
            episode_id="episode-001",
            episode_number=1,
        )
        store.accept_episode(
            _manifest(),
            publication_state=EpisodePublicationState.PENDING_EXTERNAL_AUTHORIZATION,
        )
    return store


def _context(store: SeriesStateStore) -> AuthenticatedVideoSeriesContext:
    return resolve_authenticated_video_series_context(
        store,
        series_id="series-001",
        tenant_id="tenant-001",
        user_id="user-001",
    )


def test_resolver_uses_authenticated_accepted_only_series_truth(tmp_path: Path) -> None:
    context = _context(_store(tmp_path, accepted=True))

    assert context.state.next_episode_number == 2
    assert context.previous_manifest.episode_id == "episode-001"
    assert context.continuity.previous_artifact_sha256 == "a" * 64
    assert context.continuity.previous_final_frame == "artifact://frame/final-001.png"
    assert context.continuity.series_bible_revision == 1
    assert context.continuity.next_scene_constraints == (
        "no impossible camera teleportation",
        "60 second maximum",
        "do not reveal creator before finale",
    )


def test_resolver_denies_cross_tenant_or_cross_user_access(tmp_path: Path) -> None:
    store = _store(tmp_path, accepted=True)

    with pytest.raises(VideoSeriesContextError, match="authenticated tenant/user"):
        resolve_authenticated_video_series_context(
            store,
            series_id="series-001",
            tenant_id="tenant-other",
            user_id="user-001",
        )

    with pytest.raises(VideoSeriesContextError, match="authenticated tenant/user"):
        resolve_authenticated_video_series_context(
            store,
            series_id="series-001",
            tenant_id="tenant-001",
            user_id="user-other",
        )


def test_resolver_requires_previous_accepted_final_truth(tmp_path: Path) -> None:
    store = _store(tmp_path, accepted=False)

    with pytest.raises(VideoSeriesContextError, match="previously accepted final episode"):
        resolve_authenticated_video_series_context(
            store,
            series_id="series-001",
            tenant_id="tenant-001",
            user_id="user-001",
        )


def test_resolver_is_restart_stable_and_idempotent(tmp_path: Path) -> None:
    first = _context(_store(tmp_path, accepted=True))
    restarted = SeriesStateStore(tmp_path)
    second = _context(restarted)

    assert second == first


def test_series_binding_feeds_accepted_continuity_into_runtime_objective(tmp_path: Path) -> None:
    context = _context(_store(tmp_path, accepted=True))
    resolver = bind_series_context_to_objective_resolver(
        lambda job_id: f"Create {job_id} in 16:9",
        lambda job_id: context if job_id == "episode-002" else None,
    )

    standalone = resolver("standalone-job")
    series = resolver("episode-002")

    assert standalone == "Create standalone-job in 16:9"
    assert "Create episode-002 in 16:9" in series
    assert "SERIES CONTINUITY — accepted prior truth only" in series
    assert "series_id=series-001" in series
    assert f"previous_artifact_sha256={'a' * 64}" in series
    assert "previous_final_frame=artifact://frame/final-001.png" in series
    assert "grounded cyberpunk realism" in series
    assert "no impossible camera teleportation" in series
    assert "do not reveal creator before finale" in series


def test_series_binding_fails_closed_on_stale_continuity(tmp_path: Path) -> None:
    context = _context(_store(tmp_path, accepted=True))
    stale = context.__class__(
        state=context.state,
        bible=context.bible,
        previous_manifest=context.previous_manifest,
        continuity=context.continuity.__class__(
            series_id=context.continuity.series_id,
            episode_id=context.continuity.episode_id,
            previous_artifact_sha256="b" * 64,
            previous_final_frame=context.continuity.previous_final_frame,
            character_references=context.continuity.character_references,
            location_references=context.continuity.location_references,
            visual_style_fingerprint=context.continuity.visual_style_fingerprint,
            color_language=context.continuity.color_language,
            voice_references=context.continuity.voice_references,
            audio_references=context.continuity.audio_references,
            previous_episode_summary=context.continuity.previous_episode_summary,
            open_narrative_threads=context.continuity.open_narrative_threads,
            last_scene_reference=context.continuity.last_scene_reference,
            next_scene_constraints=context.continuity.next_scene_constraints,
            series_bible_revision=context.continuity.series_bible_revision,
            privacy_classification=context.continuity.privacy_classification,
            provenance=context.continuity.provenance,
        ),
    )
    resolver = bind_series_context_to_objective_resolver(
        lambda job_id: "Continue the series",
        lambda job_id: stale,
    )

    with pytest.raises(VideoSeriesContextError, match="parent artifact is stale"):
        resolver("episode-002")
