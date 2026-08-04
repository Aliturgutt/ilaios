from __future__ import annotations

import pytest

from src.video_automation.scene_planning import (
    EpisodeBeat,
    ScenePlanner,
    ShotPlannerConfig,
    ShotPlanningError,
)


def test_default_config_targets_short_generation_clips() -> None:
    config = ShotPlannerConfig()
    assert config.min_shot_seconds == 4.0
    assert config.target_shot_seconds == 5.0
    assert config.max_shot_seconds == 6.0


def test_forty_second_episode_becomes_eight_five_second_shots() -> None:
    text = " ".join(f"word{i}" for i in range(1, 25))
    plan = ScenePlanner().plan(
        [EpisodeBeat("episode", text, 40.0)],
        episode_id="film-a-episode-001",
    )
    assert len(plan.shots) == 8
    assert all(shot.duration_seconds == pytest.approx(5.0) for shot in plan.shots)
    assert plan.total_duration_seconds == pytest.approx(40.0)


def test_fifty_second_episode_becomes_ten_five_second_shots() -> None:
    text = " ".join(f"word{i}" for i in range(1, 31))
    plan = ScenePlanner().plan(
        [EpisodeBeat("episode", text, 50.0)],
        episode_id="film-b-episode-001",
    )
    assert len(plan.shots) == 10
    assert plan.total_duration_seconds == pytest.approx(50.0)


def test_timing_window_is_project_configurable() -> None:
    planner = ScenePlanner(
        ShotPlannerConfig(
            min_shot_seconds=6.0,
            target_shot_seconds=7.0,
            max_shot_seconds=8.0,
        )
    )
    plan = planner.plan(
        [EpisodeBeat("beat", "one two three four five six", 14.0)],
        episode_id="another-film",
    )
    assert [shot.duration_seconds for shot in plan.shots] == [7.0, 7.0]


def test_multiple_beats_preserve_story_order() -> None:
    plan = ScenePlanner().plan(
        [
            EpisodeBeat("opening", "one two three four", 4.0),
            EpisodeBeat("event", "five six seven eight", 4.0),
            EpisodeBeat("ending", "nine ten eleven twelve", 4.0),
        ],
        episode_id="ordered",
    )
    assert [shot.source_beat_id for shot in plan.shots] == [
        "opening",
        "event",
        "ending",
    ]


def test_shot_ids_are_deterministic() -> None:
    plan = ScenePlanner().plan(
        [EpisodeBeat("beat", "one two three four five six", 10.0)],
        episode_id="ep-007",
    )
    assert [shot.shot_id for shot in plan.shots] == [
        "ep-007-shot-001",
        "ep-007-shot-002",
    ]


def test_neighbor_links_form_continuity_chain() -> None:
    plan = ScenePlanner().plan(
        [EpisodeBeat("beat", "one two three four five six", 10.0)],
        episode_id="ep-008",
    )
    first, second = plan.shots
    assert first.previous_shot_id is None
    assert first.next_shot_id == second.shot_id
    assert second.previous_shot_id == first.shot_id
    assert second.next_shot_id is None


def test_continuity_note_is_preserved_for_split_shots() -> None:
    note = "Preserve character identity, costume, location, and held object."
    plan = ScenePlanner().plan(
        [EpisodeBeat("beat", "one two three four five six", 10.0, note)],
        episode_id="continuity",
    )
    assert all(shot.continuity_note == note for shot in plan.shots)


def test_text_is_preserved_across_split() -> None:
    source = "one two three four five six seven eight nine ten"
    plan = ScenePlanner().plan(
        [EpisodeBeat("beat", source, 10.0)],
        episode_id="text",
    )
    assert " ".join(shot.text for shot in plan.shots) == source


def test_valid_single_shot_durations_remain_single() -> None:
    for duration in (4.0, 5.0, 6.0):
        plan = ScenePlanner().plan(
            [EpisodeBeat("beat", "one two three four", duration)],
            episode_id="single",
        )
        assert len(plan.shots) == 1
        assert plan.shots[0].duration_seconds == pytest.approx(duration)


def test_unpartitionable_duration_fails_closed() -> None:
    with pytest.raises(ShotPlanningError, match="cannot be partitioned"):
        ScenePlanner().plan(
            [EpisodeBeat("beat", "one two three four", 7.0)],
            episode_id="invalid",
        )


def test_too_few_words_for_required_shots_fails_closed() -> None:
    with pytest.raises(ShotPlanningError, match="fewer words"):
        ScenePlanner().plan(
            [EpisodeBeat("beat", "one two", 20.0)],
            episode_id="invalid",
        )


def test_empty_episode_fails_closed() -> None:
    with pytest.raises(ShotPlanningError, match="at least one"):
        ScenePlanner().plan([], episode_id="empty")


def test_blank_episode_id_fails_closed() -> None:
    with pytest.raises(ShotPlanningError, match="episode_id"):
        ScenePlanner().plan(
            [EpisodeBeat("beat", "one two three four", 4.0)],
            episode_id=" ",
        )


def test_duplicate_beat_ids_fail_closed() -> None:
    with pytest.raises(ShotPlanningError, match="unique"):
        ScenePlanner().plan(
            [
                EpisodeBeat("same", "one two three four", 4.0),
                EpisodeBeat("same", "five six seven eight", 4.0),
            ],
            episode_id="duplicate",
        )


def test_invalid_config_fails_closed() -> None:
    with pytest.raises(ShotPlanningError):
        ShotPlannerConfig(min_shot_seconds=0.0)
    with pytest.raises(ShotPlanningError):
        ShotPlannerConfig(min_shot_seconds=6.0, max_shot_seconds=4.0)
    with pytest.raises(ShotPlanningError):
        ShotPlannerConfig(target_shot_seconds=7.0)


def test_invalid_beat_fails_closed() -> None:
    with pytest.raises(ShotPlanningError):
        EpisodeBeat("", "valid text", 5.0)
    with pytest.raises(ShotPlanningError):
        EpisodeBeat("beat", "", 5.0)
    with pytest.raises(ShotPlanningError):
        EpisodeBeat("beat", "valid text", 0.0)
    with pytest.raises(ShotPlanningError):
        EpisodeBeat("beat", "valid text", 5.0, "")

def test_shots_define_all_canonical_m09_fields() -> None:
    beat = EpisodeBeat(
        beat_id="scene-001",
        text="The sentinel enters the ancient chamber.",
        duration_seconds=5.0,
        shot_type="establishing",
        subject="the sentinel",
        action="enters the ancient chamber",
        environment="an ancient subterranean chamber",
        framing="wide shot",
        movement="slow dolly forward",
        generation_prompt=(
            "Wide cinematic view of the sentinel entering "
            "an ancient subterranean chamber."
        ),
        required_provider_capability="video.generate",
    )

    shot = ScenePlanner().plan(
        (beat,),
        episode_id="canonical-m09",
    ).shots[0]

    assert shot.scene_id == "scene-001"
    assert shot.source_beat_id == "scene-001"
    assert shot.shot_type == "establishing"
    assert shot.subject == "the sentinel"
    assert shot.action == "enters the ancient chamber"
    assert (
        shot.environment
        == "an ancient subterranean chamber"
    )
    assert shot.framing == "wide shot"
    assert shot.movement == "slow dolly forward"
    assert shot.generation_prompt == (
        "Wide cinematic view of the sentinel entering "
        "an ancient subterranean chamber."
    )
    assert (
        shot.required_provider_capability
        == "video.generate"
    )


def test_split_shots_preserve_structured_visual_intent() -> None:
    beat = EpisodeBeat(
        beat_id="scene-002",
        text=(
            "one two three four five six seven eight "
            "nine ten eleven twelve"
        ),
        duration_seconds=10.0,
        shot_type="action",
        subject="the sentinel",
        action="crosses the collapsing bridge",
        environment="a volcanic abyss",
        framing="tracking medium shot",
        movement="lateral tracking",
        required_provider_capability="video.generate",
    )

    shots = ScenePlanner().plan(
        (beat,),
        episode_id="split-intent",
    ).shots

    assert len(shots) == 2
    assert all(
        shot.scene_id == "scene-002"
        for shot in shots
    )
    assert all(
        shot.shot_type == "action"
        for shot in shots
    )
    assert all(
        shot.subject == "the sentinel"
        for shot in shots
    )
    assert all(
        shot.action == "crosses the collapsing bridge"
        for shot in shots
    )
    assert all(
        shot.environment == "a volcanic abyss"
        for shot in shots
    )
    assert all(
        shot.framing == "tracking medium shot"
        for shot in shots
    )
    assert all(
        shot.movement == "lateral tracking"
        for shot in shots
    )
    assert all(
        shot.required_provider_capability
        == "video.generate"
        for shot in shots
    )


def test_generation_prompt_defaults_to_split_shot_text() -> None:
    plan = ScenePlanner().plan(
        (
            EpisodeBeat(
                "scene-003",
                "one two three four five six",
                10.0,
            ),
        ),
        episode_id="prompt-default",
    )

    assert all(
        shot.generation_prompt == shot.text
        for shot in plan.shots
    )


def test_invalid_structured_shot_intent_fails_closed() -> None:
    with pytest.raises(
        ShotPlanningError,
        match="shot_type",
    ):
        EpisodeBeat(
            "scene",
            "valid narrative text",
            5.0,
            shot_type=" ",
        )

    with pytest.raises(
        ShotPlanningError,
        match="required_provider_capability",
    ):
        EpisodeBeat(
            "scene",
            "valid narrative text",
            5.0,
            required_provider_capability=" ",
        )
