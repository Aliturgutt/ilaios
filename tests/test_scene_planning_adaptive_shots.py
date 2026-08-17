from __future__ import annotations

import pytest

from src.video_automation.scene_planning import (
    EpisodeBeat,
    ShotKind,
    ShotPlanner,
    ShotValue,
)


@pytest.mark.parametrize(
    ("shot_kind", "total", "minimum", "maximum"),
    [
        (ShotKind.GENERAL, 20.0, 4.0, 6.0),
        (ShotKind.ESTABLISHING, 24.0, 5.0, 8.0),
        (ShotKind.ACTION, 16.0, 3.0, 5.0),
        (ShotKind.DIALOGUE, 24.0, 5.0, 10.0),
        (ShotKind.REACTION_INSERT, 12.0, 2.0, 4.0),
        (ShotKind.HERO, 24.0, 4.0, 8.0),
        (ShotKind.TRANSITION, 12.0, 2.0, 4.0),
    ],
)
def test_directorial_shot_class_uses_adaptive_bounds(
    shot_kind: ShotKind,
    total: float,
    minimum: float,
    maximum: float,
) -> None:
    plan = ShotPlanner().plan(
        [
            EpisodeBeat(
                beat_id="beat-1",
                text="A deliberate cinematic beat with enough descriptive words for adaptive splitting across shots",
                duration_seconds=total,
                shot_kind=shot_kind,
            )
        ],
        episode_id="episode-a",
    )

    assert sum(shot.duration_seconds for shot in plan.shots) == pytest.approx(total)
    assert all(minimum <= shot.duration_seconds <= maximum for shot in plan.shots)


def test_shot_duration_is_not_hardcoded_to_five_seconds() -> None:
    plan = ShotPlanner().plan(
        [
            EpisodeBeat(
                beat_id="dialogue",
                text="One character delivers a continuous emotional dialogue while the camera slowly moves closer",
                duration_seconds=18.0,
                shot_kind=ShotKind.DIALOGUE,
            )
        ],
        episode_id="episode-dialogue",
    )

    assert plan.total_duration_seconds == pytest.approx(18.0)
    assert any(shot.duration_seconds != 5.0 for shot in plan.shots)


def test_continuity_references_audio_and_frame_chaining_survive_planning() -> None:
    plan = ShotPlanner().plan(
        [
            EpisodeBeat(
                beat_id="hero",
                text="The same protagonist crosses the storm-lit observatory with the same wardrobe and prop",
                duration_seconds=12.0,
                shot_kind=ShotKind.HERO,
                value=ShotValue.HERO,
                reference_asset_ids=("maya-ref", "wardrobe-ref", "location-ref"),
                capability_requirements=("input_references",),
                requires_native_audio=True,
                requires_frame_chaining=True,
                continuity_note="Preserve identity, wardrobe, prop and lens language",
            )
        ],
        episode_id="episode-continuity",
    )

    assert len(plan.shots) >= 2
    for shot in plan.shots:
        assert shot.value is ShotValue.HERO
        assert shot.reference_asset_ids == ("maya-ref", "wardrobe-ref", "location-ref")
        assert "input_references" in shot.capability_requirements
        assert "native_audio" in shot.capability_requirements
        assert "first_frame" in shot.capability_requirements
        assert "last_frame" in shot.capability_requirements
        assert shot.continuity_note is not None

    assert plan.shots[0].previous_shot_id is None
    assert plan.shots[-1].next_shot_id is None
    for previous, current in zip(plan.shots, plan.shots[1:], strict=True):
        assert previous.next_shot_id == current.shot_id
        assert current.previous_shot_id == previous.shot_id
