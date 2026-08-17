from __future__ import annotations

import pytest

from src.video_automation.models import Scene, ScriptSection, VideoScript
from src.video_automation.scene_planning import (
    EpisodeBeat,
    ScenePlanner,
    ScenePlanningError,
    ShotPlanner,
    ShotPlannerConfig,
    ShotPlanningError,
)


def _script() -> VideoScript:
    return VideoScript(
        job_id="job-m08",
        hook="Opening hook.",
        introduction="Introduction.",
        sections=(
            ScriptSection(
                section_id="section-001",
                title="Opening",
                narration="Opening narration.",
                on_screen_text="Ancient city at sunrise",
                estimated_duration_seconds=12,
            ),
            ScriptSection(
                section_id="section-002",
                title="Discovery",
                narration="Discovery narration.",
                on_screen_text=None,
                estimated_duration_seconds=18,
            ),
        ),
        cta="Continue.",
        ending="Ending.",
        estimated_duration_seconds=30,
    )


def test_m08_creates_one_scene_per_script_section() -> None:
    scenes = ScenePlanner().plan(_script())
    assert len(scenes) == 2
    assert tuple(scene.script_reference for scene in scenes) == (
        "section-001",
        "section-002",
    )


def test_m08_scene_ids_are_stable_and_ordered() -> None:
    planner = ScenePlanner()
    first = planner.plan(_script())
    second = planner.plan(_script())
    assert first == second
    assert tuple(scene.scene_id for scene in first) == (
        "job-m08-scene-001",
        "job-m08-scene-002",
    )


def test_m08_maps_required_scene_contract() -> None:
    first, second = ScenePlanner().plan(_script())
    assert first.script_reference == "section-001"
    assert first.purpose == "Opening"
    assert first.duration_seconds == 12.0
    assert first.visual_description == "Ancient city at sunrise"
    assert first.narration_reference == "section-001"
    assert first.transition_intent == "continue"
    assert first.required_asset_ids == ()
    assert second.visual_description == "Discovery"
    assert second.transition_intent == "cut"


def test_m08_rejects_non_positive_section_duration() -> None:
    script = VideoScript(
        job_id="job-invalid",
        hook="Hook.",
        introduction="Introduction.",
        sections=(
            ScriptSection(
                section_id="section-zero",
                title="Zero",
                narration="Narration.",
                estimated_duration_seconds=0,
            ),
        ),
        cta=None,
        ending="Ending.",
        estimated_duration_seconds=10,
    )
    with pytest.raises(ScenePlanningError, match="estimated_duration_seconds"):
        ScenePlanner().plan(script)


def test_m09_plan_scenes_emits_all_canonical_shot_fields() -> None:
    scene = Scene(
        scene_id="scene-001",
        script_reference="section-001",
        purpose="Opening",
        duration_seconds=5.0,
        visual_description="Sentinel enters an ancient chamber",
        narration_reference="section-001",
        transition_intent="cut",
    )
    shot = ShotPlanner().plan_scenes((scene,))[0]
    assert shot.scene_id == "scene-001"
    assert shot.shot_type == "cinematic"
    assert shot.subject == "Opening"
    assert shot.action == "depict Opening"
    assert shot.environment == "Sentinel enters an ancient chamber"
    assert shot.framing == "medium shot"
    assert shot.movement == "static"
    assert shot.estimated_duration_seconds == 5.0
    assert shot.generation_prompt == "Sentinel enters an ancient chamber"
    assert shot.required_provider_capability == "video.generate"


def test_m09_plan_scenes_rejects_empty_input() -> None:
    with pytest.raises(ShotPlanningError, match="at least one scene"):
        ShotPlanner().plan_scenes(())


def test_default_config_targets_short_generation_clips() -> None:
    config = ShotPlannerConfig()
    assert config.min_shot_seconds == 4.0
    assert config.target_shot_seconds == 5.0
    assert config.max_shot_seconds == 6.0


def test_forty_second_episode_becomes_eight_five_second_shots() -> None:
    text = " ".join(f"word{i}" for i in range(1, 25))
    plan = ShotPlanner().plan(
        [EpisodeBeat("episode", text, 40.0)],
        episode_id="film-a-episode-001",
    )
    assert len(plan.shots) == 8
    assert all(shot.duration_seconds == pytest.approx(5.0) for shot in plan.shots)
    assert plan.total_duration_seconds == pytest.approx(40.0)


def test_timing_window_is_project_configurable() -> None:
    planner = ShotPlanner(
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
    plan = ShotPlanner().plan(
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
    plan = ShotPlanner().plan(
        [EpisodeBeat("beat", "one two three four five six", 10.0)],
        episode_id="ep-007",
    )
    assert [shot.shot_id for shot in plan.shots] == [
        "ep-007-shot-001",
        "ep-007-shot-002",
    ]


def test_neighbor_links_form_continuity_chain() -> None:
    plan = ShotPlanner().plan(
        [EpisodeBeat("beat", "one two three four five six", 10.0)],
        episode_id="ep-008",
    )
    first, second = plan.shots
    assert first.previous_shot_id is None
    assert first.next_shot_id == second.shot_id
    assert second.previous_shot_id == first.shot_id
    assert second.next_shot_id is None


def test_text_is_preserved_across_split() -> None:
    source = "one two three four five six seven eight nine ten"
    plan = ShotPlanner().plan(
        [EpisodeBeat("beat", source, 10.0)],
        episode_id="text",
    )
    assert " ".join(shot.text for shot in plan.shots) == source


def test_default_gap_uses_absolute_safety_envelope() -> None:
    plan = ShotPlanner().plan(
        [EpisodeBeat("beat", "one two three four", 7.0)],
        episode_id="safety-envelope",
    )
    assert plan.total_duration_seconds == pytest.approx(7.0)
    assert [shot.duration_seconds for shot in plan.shots] == [7.0]


def test_duplicate_beat_ids_fail_closed() -> None:
    with pytest.raises(ShotPlanningError, match="unique"):
        ShotPlanner().plan(
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


def test_structured_visual_intent_is_preserved() -> None:
    beat = EpisodeBeat(
        beat_id="scene-002",
        text="one two three four five six seven eight nine ten eleven twelve",
        duration_seconds=10.0,
        shot_type="action",
        subject="the sentinel",
        action="crosses the collapsing bridge",
        environment="a volcanic abyss",
        framing="tracking medium shot",
        movement="lateral tracking",
        required_provider_capability="video.generate",
    )
    shots = ShotPlanner().plan((beat,), episode_id="split-intent").shots
    assert len(shots) == 2
    assert all(shot.scene_id == "scene-002" for shot in shots)
    assert all(shot.shot_type == "action" for shot in shots)
    assert all(shot.subject == "the sentinel" for shot in shots)
    assert all(shot.action == "crosses the collapsing bridge" for shot in shots)
    assert all(shot.environment == "a volcanic abyss" for shot in shots)
    assert all(shot.framing == "tracking medium shot" for shot in shots)
    assert all(shot.movement == "lateral tracking" for shot in shots)
