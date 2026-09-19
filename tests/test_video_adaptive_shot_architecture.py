from __future__ import annotations

from src.video_automation.openrouter_video_catalog import (
    ManagedVideoFamily,
    OpenRouterVideoModel,
)
from src.video_automation.request_manifest import (
    CaptionMode,
    EpisodeRequestManifestBuilder,
)
from src.video_automation.scene_planning import EpisodeBeat, ShotPlanner
from src.video_automation.shot_request_planning import ShotGenerationRequest


def _words(count: int) -> str:
    return " ".join(f"word{index}" for index in range(count))


def _request() -> ShotGenerationRequest:
    return ShotGenerationRequest(
        request_id="request-001",
        idempotency_key="a" * 64,
        shot_id="shot-001",
        source_beat_id="beat-001",
        prompt_text="cinematic product reveal",
        duration_seconds=5.0,
        aspect_ratio="16:9",
        frames_per_second=24,
        output_count=1,
        seed=None,
        metadata={"source": "test"},
    )


def _model(*, durations: tuple[int, ...], frames: tuple[str, ...] = ()) -> OpenRouterVideoModel:
    return OpenRouterVideoModel(
        model_id="bytedance/seedance-test",
        canonical_slug="bytedance/seedance-test",
        name="Seedance Test",
        generate_audio=True,
        supported_aspect_ratios=("16:9",),
        supported_durations=durations,
        supported_frame_images=frames,
        supported_resolutions=("720p",),
        supported_sizes=(),
        allowed_passthrough_parameters=(),
        pricing_skus={"video_second": "0.02"},
        family=ManagedVideoFamily.SEEDANCE,
    )


def test_default_cinematic_timing_remains_four_to_six_seconds() -> None:
    plan = ShotPlanner().plan(
        [EpisodeBeat("beat-001", _words(30), 20.0)],
        episode_id="episode-001",
    )

    assert plan.total_duration_seconds == 20.0
    assert len(plan.shots) == 4
    assert all(4.0 <= shot.duration_seconds <= 6.0 for shot in plan.shots)


def test_dialogue_uses_longer_semantic_shots_without_changing_final_duration() -> None:
    plan = ShotPlanner().plan(
        [
            EpisodeBeat(
                "beat-dialogue",
                _words(30),
                20.0,
                shot_type="dialogue",
            )
        ],
        episode_id="episode-dialogue",
    )

    assert plan.total_duration_seconds == 20.0
    assert len(plan.shots) == 3
    assert all(5.0 <= shot.duration_seconds <= 10.0 for shot in plan.shots)


def test_action_uses_shorter_semantic_shots() -> None:
    plan = ShotPlanner().plan(
        [EpisodeBeat("beat-action", _words(40), 20.0, shot_type="action")],
        episode_id="episode-action",
    )

    assert plan.total_duration_seconds == 20.0
    assert len(plan.shots) == 5
    assert all(3.0 <= shot.duration_seconds <= 5.0 for shot in plan.shots)


def test_caption_mode_defaults_off() -> None:
    manifest = EpisodeRequestManifestBuilder().build(
        "episode-default-captions",
        [_request()],
    )

    assert manifest.caption_mode is CaptionMode.OFF
    assert manifest.captions_explicitly_disabled
    assert not manifest.captions_explicitly_required
    assert manifest.metadata["caption_mode"] == "off"


def test_caption_mode_off_is_explicit_and_not_forced() -> None:
    manifest = EpisodeRequestManifestBuilder().build(
        "episode-no-captions",
        [_request()],
        caption_mode=CaptionMode.OFF,
    )

    assert manifest.caption_mode is CaptionMode.OFF
    assert manifest.captions_explicitly_disabled
    assert not manifest.captions_explicitly_required
    assert manifest.metadata["caption_mode"] == "off"


def test_caption_mode_on_is_an_explicit_deliverable() -> None:
    manifest = EpisodeRequestManifestBuilder().build(
        "episode-captions",
        [_request()],
        caption_mode=CaptionMode.ON,
    )

    assert manifest.captions_explicitly_required
    assert not manifest.captions_explicitly_disabled
    assert manifest.metadata["caption_mode"] == "on"


def test_caption_mode_changes_manifest_identity() -> None:
    builder = EpisodeRequestManifestBuilder()
    off_manifest = builder.build(
        "episode-caption-identity",
        [_request()],
        caption_mode=CaptionMode.OFF,
    )
    on_manifest = builder.build(
        "episode-caption-identity",
        [_request()],
        caption_mode=CaptionMode.ON,
    )

    assert off_manifest.manifest_id != on_manifest.manifest_id


def test_live_capability_resolves_nearest_duration_and_ties_choose_shorter() -> None:
    model = _model(durations=(4, 6, 8))

    assert model.resolve_supported_duration(5.0) == 4
    assert model.resolve_supported_duration(7.4) == 8


def test_first_last_frame_capability_is_explicit() -> None:
    model = _model(durations=(4, 6), frames=("first_frame", "last_frame"))

    assert model.supports_frame_role("first-frame")
    assert model.supports_frame_role("last_frame")
    assert not model.supports_frame_role("reference_frame")
