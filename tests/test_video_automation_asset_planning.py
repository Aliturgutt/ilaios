"""Tests for canonical M10 Asset Planner."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from src.video_automation.asset_planning import (
    AssetPlanner,
    AssetPlanningError,
)
from src.video_automation.models import MediaType, Shot


def make_shot(
    *,
    shot_id: str = "shot-1",
    scene_id: str = "scene-1",
    capability: str = "text-to-video",
    prompt: str = "Cinematic rover crossing a frozen plain.",
    duration_seconds: float = 5.0,
) -> Shot:
    return Shot(
        shot_id=shot_id,
        scene_id=scene_id,
        shot_type="establishing",
        camera_description="wide camera",
        subject="rover",
        action="crosses the frozen plain",
        environment="frozen plain",
        framing="wide",
        movement="slow push",
        estimated_duration_seconds=duration_seconds,
        generation_prompt=prompt,
        required_provider_capability=capability,
    )


def test_planner_emits_asset_request_from_shot() -> None:
    shot = make_shot()

    requests = AssetPlanner().plan(
        job_id="job-1",
        shots=(shot,),
        media_type_by_capability={"text-to-video": MediaType.VIDEO},
    )

    assert len(requests) == 1

    request = requests[0]

    assert request.job_id == "job-1"
    assert request.shot_id == shot.shot_id
    assert request.media_type is MediaType.VIDEO
    assert request.description == shot.generation_prompt
    assert request.required_capability == shot.required_provider_capability


def test_planner_preserves_explicit_shot_order() -> None:
    requests = AssetPlanner().plan(
        job_id="job-1",
        shots=(
            make_shot(shot_id="shot-1"),
            make_shot(shot_id="shot-2"),
            make_shot(shot_id="shot-3"),
        ),
        media_type_by_capability={"text-to-video": MediaType.VIDEO},
    )

    assert tuple(request.shot_id for request in requests) == (
        "shot-1",
        "shot-2",
        "shot-3",
    )


def test_planner_uses_explicit_media_type_mapping() -> None:
    requests = AssetPlanner().plan(
        job_id="job-1",
        shots=(
            make_shot(
                shot_id="shot-video",
                capability="text-to-video",
            ),
            make_shot(
                shot_id="shot-image",
                capability="text-to-image",
            ),
        ),
        media_type_by_capability={
            "text-to-video": MediaType.VIDEO,
            "text-to-image": MediaType.IMAGE,
        },
    )

    assert requests[0].media_type is MediaType.VIDEO
    assert requests[1].media_type is MediaType.IMAGE


def test_planner_accepts_existing_canonical_media_types() -> None:
    media_types: tuple[MediaType, ...] = (
        MediaType.VIDEO,
        MediaType.IMAGE,
        MediaType.AUDIO,
        MediaType.VOICE,
        MediaType.MUSIC,
        MediaType.SOUND_EFFECT,
        MediaType.SUBTITLE,
        MediaType.OVERLAY,
    )

    for media_type in media_types:
        request = AssetPlanner().plan(
            job_id="job-1",
            shots=(make_shot(capability="explicit-capability"),),
            media_type_by_capability={
                "explicit-capability": media_type,
            },
        )[0]

        assert request.media_type is media_type


def test_request_identity_is_deterministic() -> None:
    planner = AssetPlanner()
    shot = make_shot()

    first = planner.plan(
        job_id="job-1",
        shots=(shot,),
        media_type_by_capability={"text-to-video": MediaType.VIDEO},
    )

    second = planner.plan(
        job_id="job-1",
        shots=(shot,),
        media_type_by_capability={"text-to-video": MediaType.VIDEO},
    )

    assert first[0].asset_request_id == second[0].asset_request_id
    assert (
        first[0].metadata["planning_sha256"]
        == second[0].metadata["planning_sha256"]
    )


def test_prompt_change_changes_asset_request_identity() -> None:
    planner = AssetPlanner()

    first = planner.plan(
        job_id="job-1",
        shots=(make_shot(prompt="First approved prompt."),),
        media_type_by_capability={"text-to-video": MediaType.VIDEO},
    )

    second = planner.plan(
        job_id="job-1",
        shots=(make_shot(prompt="Second approved prompt."),),
        media_type_by_capability={"text-to-video": MediaType.VIDEO},
    )

    assert first[0].asset_request_id != second[0].asset_request_id


def test_media_type_change_changes_asset_request_identity() -> None:
    planner = AssetPlanner()
    shot = make_shot()

    first = planner.plan(
        job_id="job-1",
        shots=(shot,),
        media_type_by_capability={"text-to-video": MediaType.VIDEO},
    )

    second = planner.plan(
        job_id="job-1",
        shots=(shot,),
        media_type_by_capability={"text-to-video": MediaType.IMAGE},
    )

    assert first[0].asset_request_id != second[0].asset_request_id


def test_metadata_preserves_shot_traceability() -> None:
    shot = make_shot(
        scene_id="scene-7",
        duration_seconds=4.5,
    )

    request = AssetPlanner().plan(
        job_id="job-1",
        shots=(shot,),
        media_type_by_capability={"text-to-video": MediaType.VIDEO},
    )[0]

    assert request.metadata["scene_id"] == "scene-7"
    assert request.metadata["shot_type"] == "establishing"
    assert request.metadata["estimated_duration_seconds"] == 4.5
    assert len(str(request.metadata["planning_sha256"])) == 64


def test_asset_request_metadata_remains_immutable() -> None:
    request = AssetPlanner().plan(
        job_id="job-1",
        shots=(make_shot(),),
        media_type_by_capability={"text-to-video": MediaType.VIDEO},
    )[0]

    assert isinstance(request.metadata, MappingProxyType)

    with pytest.raises(TypeError):
        request.metadata["x"] = "y"  # type: ignore[index]


def test_empty_shot_sequence_fails_closed() -> None:
    with pytest.raises(AssetPlanningError, match="shots"):
        AssetPlanner().plan(
            job_id="job-1",
            shots=(),
            media_type_by_capability={"text-to-video": MediaType.VIDEO},
        )


def test_blank_job_id_fails_closed() -> None:
    with pytest.raises(AssetPlanningError, match="job_id"):
        AssetPlanner().plan(
            job_id=" ",
            shots=(make_shot(),),
            media_type_by_capability={"text-to-video": MediaType.VIDEO},
        )


def test_duplicate_shot_ids_fail_closed() -> None:
    with pytest.raises(AssetPlanningError, match="shot_id"):
        AssetPlanner().plan(
            job_id="job-1",
            shots=(
                make_shot(shot_id="shot-1"),
                make_shot(shot_id="shot-1"),
            ),
            media_type_by_capability={"text-to-video": MediaType.VIDEO},
        )


def test_missing_capability_mapping_fails_closed() -> None:
    with pytest.raises(
        AssetPlanningError,
        match="no media type mapping",
    ):
        AssetPlanner().plan(
            job_id="job-1",
            shots=(make_shot(capability="text-to-video"),),
            media_type_by_capability={
                "text-to-image": MediaType.IMAGE,
            },
        )


def test_empty_capability_mapping_fails_closed() -> None:
    with pytest.raises(
        AssetPlanningError,
        match="media_type_by_capability",
    ):
        AssetPlanner().plan(
            job_id="job-1",
            shots=(make_shot(),),
            media_type_by_capability={},
        )


def test_blank_capability_mapping_key_fails_closed() -> None:
    with pytest.raises(
        AssetPlanningError,
        match="capability mapping key",
    ):
        AssetPlanner().plan(
            job_id="job-1",
            shots=(make_shot(),),
            media_type_by_capability={
                " ": MediaType.VIDEO,
            },
        )


def test_invalid_media_type_mapping_value_fails_closed() -> None:
    mapping: dict[str, object] = {
        "text-to-video": "video",
    }

    with pytest.raises(
        AssetPlanningError,
        match="MediaType",
    ):
        AssetPlanner().plan(
            job_id="job-1",
            shots=(make_shot(),),
            media_type_by_capability=mapping,  # type: ignore[arg-type]
        )


def test_planner_does_not_select_or_attach_provider() -> None:
    request = AssetPlanner().plan(
        job_id="job-1",
        shots=(make_shot(),),
        media_type_by_capability={"text-to-video": MediaType.VIDEO},
    )[0]

    assert not hasattr(request, "provider")
    assert not hasattr(request, "provider_name")
    assert not hasattr(request, "provider_id")


def test_planner_does_not_mutate_input_mapping() -> None:
    mapping = {
        "text-to-video": MediaType.VIDEO,
    }

    AssetPlanner().plan(
        job_id="job-1",
        shots=(make_shot(),),
        media_type_by_capability=mapping,
    )

    assert mapping == {
        "text-to-video": MediaType.VIDEO,
    }
