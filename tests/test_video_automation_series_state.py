from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.runtime.scheduler import WorkerProfile, WorkerScheduler
from services.runtime.series_scheduler_adapter import GovernedSeriesSchedulerAdapter
from src.video_automation.series_scheduler import (
    SERIES_EPISODE_CAPABILITY,
    SeriesEpisodeScheduler,
    SeriesSchedulingUnavailableError,
)
from src.video_automation.series_state import (
    AcceptedEpisodeManifest,
    CharacterBibleEntry,
    EpisodeProgressState,
    EpisodePublicationState,
    SeriesBible,
    SeriesState,
    SeriesStateError,
    SeriesStateStore,
)


def _state(*, series_id: str = "series-001", tenant_id: str = "tenant-001") -> SeriesState:
    return SeriesState(
        series_id=series_id,
        tenant_id=tenant_id,
        user_id="user-001",
        title="Neon Continuum",
        objective="Create one accepted continuation per episode",
        premise="A courier protects a memory archive in a cyberpunk city.",
        schedule_spec="daily@19:00 Europe/Istanbul",
        bible_revision=1,
        open_story_threads=("archive origin",),
    )


def _bible(*, series_id: str = "series-001") -> SeriesBible:
    return SeriesBible(
        series_id=series_id,
        revision=1,
        premise="A courier protects a memory archive in a cyberpunk city.",
        world_rules=("memories are physical keys",),
        characters=(
            CharacterBibleEntry(
                character_id="mira",
                name="Mira",
                appearance="short dark hair, amber cybernetic eye",
                wardrobe_constraints=("black courier jacket",),
                personality="calm and observant",
                voice_identity="voice:mira:v1",
                character_arc="learn who created the archive",
            ),
        ),
        cinematography="controlled handheld with deliberate closeups",
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
    series_id: str = "series-001",
    episode_id: str = "episode-001",
    episode_number: int = 1,
    artifact_sha: str = "a" * 64,
) -> AcceptedEpisodeManifest:
    return AcceptedEpisodeManifest(
        series_id=series_id,
        episode_id=episode_id,
        episode_number=episode_number,
        episode_objective="Mira recovers the first archive shard.",
        final_acceptance_id="acceptance-001",
        final_artifact_reference="artifact://episode-001/final.mp4",
        final_artifact_sha256=artifact_sha,
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
        accepted_at="2026-08-14T12:00:00+00:00",
        bible_revision=1,
    )


def _store(tmp_path: Path) -> SeriesStateStore:
    store = SeriesStateStore(tmp_path)
    store.create_series(_state(), _bible())
    return store


def test_series_state_and_bible_survive_restart(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.load_series("series-001") == _state()
    assert store.load_bible("series-001") == _bible()

    restarted = SeriesStateStore(tmp_path)
    assert restarted.load_series("series-001") == _state()
    assert restarted.load_bible("series-001") == _bible()


def test_previous_incomplete_episode_blocks_next_episode(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.begin_episode(
        series_id="series-001", episode_id="episode-001", episode_number=1
    )
    store.checkpoint_episode(
        series_id="series-001",
        episode_id="episode-001",
        checkpoint="SHOT_GENERATION",
        incomplete=True,
    )

    with pytest.raises(SeriesStateError, match="resume it first"):
        store.begin_episode(
            series_id="series-001", episode_id="episode-002", episode_number=1
        )

    state, checkpoint = store.episode_progress(
        series_id="series-001", episode_id="episode-001"
    )
    assert state is EpisodeProgressState.INCOMPLETE
    assert checkpoint == "SHOT_GENERATION"


def test_accepted_manifest_is_durable_before_series_advancement(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.begin_episode(
        series_id="series-001", episode_id="episode-001", episode_number=1
    )
    manifest = _manifest()

    digest = store.persist_accepted_manifest(
        manifest,
        publication_state=EpisodePublicationState.PENDING_EXTERNAL_AUTHORIZATION,
    )

    assert len(digest) == 64
    assert store.load_manifest("episode-001") == manifest
    assert store.load_series("series-001").next_episode_number == 1
    assert (
        store.publication_state("episode-001")
        is EpisodePublicationState.PENDING_EXTERNAL_AUTHORIZATION
    )


def test_recovery_advances_series_from_immutable_manifest_after_restart(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    store.begin_episode(
        series_id="series-001", episode_id="episode-001", episode_number=1
    )
    store.persist_accepted_manifest(
        _manifest(), publication_state=EpisodePublicationState.PENDING
    )

    restarted = SeriesStateStore(tmp_path)
    recovered = restarted.recover_series_from_manifests("series-001")

    assert recovered.next_episode_number == 2
    assert recovered.latest_accepted_episode_id == "episode-001"
    assert recovered.latest_artifact_sha256 == "a" * 64
    progress, checkpoint = restarted.episode_progress(
        series_id="series-001", episode_id="episode-001"
    )
    assert progress is EpisodeProgressState.ACCEPTED
    assert checkpoint == "ACCEPTED_EPISODE_MANIFEST"


def test_accepted_manifest_cannot_be_overwritten(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.begin_episode(
        series_id="series-001", episode_id="episode-001", episode_number=1
    )
    original = _manifest()
    store.persist_accepted_manifest(original, publication_state=EpisodePublicationState.PENDING)

    changed = _manifest(artifact_sha="b" * 64)
    with pytest.raises(SeriesStateError, match="immutable"):
        store.persist_accepted_manifest(changed, publication_state=EpisodePublicationState.PENDING)


def test_continuity_package_is_bound_only_to_accepted_artifact_sha(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.begin_episode(
        series_id="series-001", episode_id="episode-001", episode_number=1
    )
    store.accept_episode(
        _manifest(),
        publication_state=EpisodePublicationState.PENDING_EXTERNAL_AUTHORIZATION,
    )

    package = store.create_continuity_package(
        episode_id="episode-001",
        privacy_classification="TENANT_PRIVATE",
        provenance="accepted-episode-manifest",
        last_scene_reference="artifact://scene/last-001",
        next_scene_constraints=("continue from the broadcast discovery",),
    )

    assert package.previous_artifact_sha256 == "a" * 64
    assert package.previous_final_frame == "artifact://frame/final-001.png"
    assert package.character_references == ("artifact://frame/mira-001.png",)
    assert package.open_narrative_threads == (
        "archive origin",
        "unknown broadcast recipient",
    )


def test_cross_series_manifest_cannot_advance_another_series(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create_series(
        _state(series_id="series-002", tenant_id="tenant-002"),
        _bible(series_id="series-002"),
    )
    store.begin_episode(
        series_id="series-001", episode_id="episode-001", episode_number=1
    )
    store.persist_accepted_manifest(_manifest(), publication_state=EpisodePublicationState.PENDING)

    with pytest.raises(SeriesStateError, match="another series"):
        store.advance_series_from_manifest(
            series_id="series-002", episode_id="episode-001"
        )


def test_series_scheduler_uses_existing_scheduler_and_never_invokes_provider(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    scheduler = WorkerScheduler(lease_duration=timedelta(minutes=5))
    scheduler.register(
        WorkerProfile(
            worker_id="worker-001",
            capabilities=frozenset({SERIES_EPISODE_CAPABILITY}),
            max_concurrent_tasks=1,
        )
    )
    orchestrator = SeriesEpisodeScheduler(
        state_store=store,
        scheduler=GovernedSeriesSchedulerAdapter(scheduler),
    )
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)

    scheduled = orchestrator.schedule_next(
        series_id="series-001", episode_id="episode-001", now=now
    )

    assert scheduled.episode_number == 1
    assert scheduled.lease.worker_id == "worker-001"
    progress, checkpoint = store.episode_progress(
        series_id="series-001", episode_id="episode-001"
    )
    assert progress is EpisodeProgressState.IN_PROGRESS
    assert checkpoint == "GOVERNED_JOB_LEASED"


def test_scheduler_failure_marks_same_episode_incomplete_for_resume(tmp_path: Path) -> None:
    store = _store(tmp_path)
    scheduler = WorkerScheduler(lease_duration=timedelta(minutes=5))
    orchestrator = SeriesEpisodeScheduler(
        state_store=store,
        scheduler=GovernedSeriesSchedulerAdapter(scheduler),
    )
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)

    with pytest.raises(SeriesSchedulingUnavailableError, match="no worker"):
        orchestrator.schedule_next(
            series_id="series-001", episode_id="episode-001", now=now
        )

    progress, checkpoint = store.episode_progress(
        series_id="series-001", episode_id="episode-001"
    )
    assert progress is EpisodeProgressState.INCOMPLETE
    assert checkpoint == "SCHEDULER_UNAVAILABLE"
