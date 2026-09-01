from __future__ import annotations

import pytest

from src.video_automation.continuity import (
    CharacterContinuity,
    ContinuityError,
    ContinuityState,
    ContinuityTracker,
    ContinuityUpdate,
)


def _character(*, costume: str = "black field suit") -> CharacterContinuity:
    return CharacterContinuity(
        character_id="lead",
        identity="adult expedition commander",
        appearance="short dark hair and a scar above the left eyebrow",
        costume=costume,
    )


def _initial_state() -> ContinuityState:
    return ContinuityState(
        shot_id="episode-001-shot-001",
        characters=(_character(),),
        location="abandoned orbital station corridor",
        objects=("handheld scanner",),
        technology=("sealed bulkhead",),
        timeline="night cycle",
        lighting="cold blue emergency lights",
        visual_style="grounded cinematic science fiction",
        camera_state="slow forward tracking shot",
        scene_state="the commander approaches the sealed bulkhead",
    )


def test_initial_state_preserves_all_structured_continuity_fields() -> None:
    state = ContinuityTracker().start(_initial_state())
    assert state.shot_id == "episode-001-shot-001"
    assert state.characters == (_character(),)
    assert state.location == "abandoned orbital station corridor"
    assert state.objects == ("handheld scanner",)
    assert state.technology == ("sealed bulkhead",)
    assert state.timeline == "night cycle"
    assert state.lighting == "cold blue emergency lights"
    assert state.visual_style == "grounded cinematic science fiction"
    assert state.camera_state == "slow forward tracking shot"
    assert state.scene_state == "the commander approaches the sealed bulkhead"
    assert state.previous_shot_id is None


def test_advance_preserves_every_unspecified_field() -> None:
    previous = _initial_state()
    transition = ContinuityTracker().advance(
        previous,
        shot_id="episode-001-shot-002",
    )
    current = transition.current
    assert current.characters == previous.characters
    assert current.location == previous.location
    assert current.objects == previous.objects
    assert current.technology == previous.technology
    assert current.timeline == previous.timeline
    assert current.lighting == previous.lighting
    assert current.visual_style == previous.visual_style
    assert current.camera_state == previous.camera_state
    assert current.scene_state == previous.scene_state
    assert current.previous_shot_id == previous.shot_id
    assert transition.changed_fields == ()


def test_explicit_update_changes_only_authorized_fields() -> None:
    previous = _initial_state()
    transition = ContinuityTracker().advance(
        previous,
        shot_id="episode-001-shot-002",
        update=ContinuityUpdate(
            camera_state="locked close-up",
            scene_state="the bulkhead indicator turns red",
        ),
    )
    assert transition.current.camera_state == "locked close-up"
    assert transition.current.scene_state == "the bulkhead indicator turns red"
    assert transition.current.location == previous.location
    assert transition.current.characters == previous.characters
    assert transition.changed_fields == ("camera_state", "scene_state")


def test_character_costume_change_is_explicit_and_auditable() -> None:
    transition = ContinuityTracker().advance(
        _initial_state(),
        shot_id="episode-001-shot-002",
        update=ContinuityUpdate(characters=(_character(costume="pressure suit"),)),
    )
    assert transition.current.characters[0].costume == "pressure suit"
    assert transition.changed_fields == ("characters",)


def test_objects_and_technology_can_be_replaced_deterministically() -> None:
    transition = ContinuityTracker().advance(
        _initial_state(),
        shot_id="episode-001-shot-002",
        update=ContinuityUpdate(
            objects=("handheld scanner", "access key"),
            technology=("sealed bulkhead", "biometric lock"),
        ),
    )
    assert transition.current.objects == ("handheld scanner", "access key")
    assert transition.current.technology == ("sealed bulkhead", "biometric lock")
    assert transition.changed_fields == ("objects", "technology")


def test_optional_fields_can_be_cleared_explicitly() -> None:
    transition = ContinuityTracker().advance(
        _initial_state(),
        shot_id="episode-001-shot-002",
        update=ContinuityUpdate(
            clear_location=True,
            clear_camera_state=True,
            clear_scene_state=True,
        ),
    )
    assert transition.current.location is None
    assert transition.current.camera_state is None
    assert transition.current.scene_state is None
    assert transition.changed_fields == (
        "location",
        "camera_state",
        "scene_state",
    )


def test_character_map_uses_stable_character_identifiers() -> None:
    second = CharacterContinuity(
        character_id="guide",
        identity="maintenance android",
        appearance="weathered white shell with amber optics",
        costume="integrated utility harness",
    )
    state = ContinuityState(
        shot_id="shot-001",
        characters=(_character(), second),
    )
    assert state.character_map() == {"lead": _character(), "guide": second}


def test_rebind_shot_preserves_facts_and_updates_links() -> None:
    state = _initial_state()
    rebound = ContinuityTracker().rebind_shot(
        state,
        shot_id="episode-002-shot-001",
        previous_shot_id="episode-001-shot-010",
    )
    assert rebound.shot_id == "episode-002-shot-001"
    assert rebound.previous_shot_id == "episode-001-shot-010"
    assert rebound.characters == state.characters
    assert rebound.location == state.location


def test_initial_state_with_predecessor_fails_closed() -> None:
    invalid = ContinuityState(
        shot_id="shot-002",
        previous_shot_id="shot-001",
    )
    with pytest.raises(ContinuityError, match="initial continuity state"):
        ContinuityTracker().start(invalid)


def test_reused_shot_identifier_fails_closed() -> None:
    previous = _initial_state()
    with pytest.raises(ContinuityError, match="must differ"):
        ContinuityTracker().advance(previous, shot_id=previous.shot_id)


def test_blank_required_values_fail_closed() -> None:
    with pytest.raises(ContinuityError, match="character_id"):
        CharacterContinuity(" ", "identity", "appearance", "costume")
    with pytest.raises(ContinuityError, match="shot_id"):
        ContinuityState(shot_id=" ")


def test_blank_optional_values_fail_closed() -> None:
    with pytest.raises(ContinuityError, match="location"):
        ContinuityState(shot_id="shot-001", location=" ")
    with pytest.raises(ContinuityError, match="camera_state"):
        ContinuityUpdate(camera_state="")


def test_duplicate_character_identifiers_fail_closed() -> None:
    with pytest.raises(ContinuityError, match="character_id values must be unique"):
        ContinuityState(
            shot_id="shot-001",
            characters=(_character(), _character(costume="pressure suit")),
        )


def test_duplicate_or_blank_collection_values_fail_closed() -> None:
    with pytest.raises(ContinuityError, match="objects values must be unique"):
        ContinuityState(shot_id="shot-001", objects=("scanner", "scanner"))
    with pytest.raises(ContinuityError, match="technology must not be blank"):
        ContinuityState(shot_id="shot-001", technology=(" ",))


def test_state_cannot_reference_itself_as_previous_shot() -> None:
    with pytest.raises(ContinuityError, match="must differ"):
        ContinuityState(shot_id="shot-001", previous_shot_id="shot-001")


def test_update_cannot_set_and_clear_same_field() -> None:
    with pytest.raises(ContinuityError, match="location cannot be set and cleared"):
        ContinuityUpdate(location="new location", clear_location=True)


def test_transition_order_is_deterministic_across_multiple_shots() -> None:
    tracker = ContinuityTracker()
    first = tracker.start(_initial_state())
    second = tracker.advance(first, shot_id="episode-001-shot-002").current
    third = tracker.advance(
        second,
        shot_id="episode-001-shot-003",
        update=ContinuityUpdate(lighting="pulsing red alarm lights"),
    ).current
    assert second.previous_shot_id == first.shot_id
    assert third.previous_shot_id == second.shot_id
    assert third.characters == first.characters
    assert third.lighting == "pulsing red alarm lights"
