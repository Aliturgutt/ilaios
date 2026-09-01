from __future__ import annotations

import json

import pytest

from src.video_automation.models import ProviderRequest
from src.video_automation.openrouter_frame_references import (
    FrameReferenceRequest,
    FrameReferenceRoutingError,
    build_openrouter_frame_images,
    capability_bound_frame_fields,
)
from src.video_automation.openrouter_managed_video_gateway import (
    OpenRouterManagedVideoGatewayError,
    _validate_capabilities,
)
from src.video_automation.openrouter_managed_video_provider import _build_request_body
from src.video_automation.openrouter_video_catalog import (
    ManagedVideoFamily,
    OpenRouterVideoModel,
)


def _model(*roles: str) -> OpenRouterVideoModel:
    return OpenRouterVideoModel(
        model_id="kwaivgi/kling-v3.0-pro",
        canonical_slug="kwaivgi/kling-v3.0-pro",
        name="Kling",
        generate_audio=True,
        supported_aspect_ratios=("16:9",),
        supported_durations=(4, 8),
        supported_frame_images=tuple(roles),
        supported_resolutions=("720p",),
        supported_sizes=(),
        allowed_passthrough_parameters=(),
        pricing_skus={"generate": "0.50"},
        family=ManagedVideoFamily.KLING,
    )


def _item(**extra: object) -> dict[str, object]:
    item: dict[str, object] = {
        "request_id": "request-001",
        "shot_id": "shot-001",
        "prompt_text": "cinematic governed scene",
        "duration_seconds": 4,
        "aspect_ratio": "16:9",
        "output_count": 1,
        "resolution": "720p",
        "generate_audio": True,
    }
    item.update(extra)
    return item


def _request(item: dict[str, object]) -> ProviderRequest:
    return ProviderRequest(
        request_id="request-001",
        job_id="job-001",
        provider_name="openrouter-video-managed",
        operation="video.generate",
        payload={
            "model_id": "kwaivgi/kling-v3.0-pro",
            "request_count": 1,
            "items_json": json.dumps([item], separators=(",", ":")),
        },
    )


def test_required_supported_frame_roles_are_bound() -> None:
    fields = capability_bound_frame_fields(
        model=_model("first_frame", "last_frame"),
        references=FrameReferenceRequest(
            first_frame_url="https://assets.example/first.png",
            last_frame_url="https://assets.example/last.png",
            require_first_frame=True,
            require_last_frame=True,
        ),
    )
    assert fields == {
        "first_frame_url": "https://assets.example/first.png",
        "last_frame_url": "https://assets.example/last.png",
    }


def test_required_unsupported_frame_role_fails_closed() -> None:
    with pytest.raises(FrameReferenceRoutingError, match="required last_frame"):
        capability_bound_frame_fields(
            model=_model("first_frame"),
            references=FrameReferenceRequest(
                last_frame_url="https://assets.example/last.png",
                require_last_frame=True,
            ),
        )


def test_optional_unsupported_frame_role_is_omitted() -> None:
    fields = capability_bound_frame_fields(
        model=_model("first_frame"),
        references=FrameReferenceRequest(
            first_frame_url="https://assets.example/first.png",
            last_frame_url="https://assets.example/last.png",
        ),
    )
    assert fields == {"first_frame_url": "https://assets.example/first.png"}


def test_gateway_rejects_supplied_role_not_proven_by_live_catalog() -> None:
    request = _request(
        _item(last_frame_url="https://assets.example/last.png")
    )
    with pytest.raises(OpenRouterManagedVideoGatewayError, match="last_frame"):
        _validate_capabilities(request, _model("first_frame"))


def test_provider_emits_openrouter_frame_images_shape_after_capability_gate() -> None:
    item = _item(
        first_frame_url="https://assets.example/first.png",
        last_frame_url="https://assets.example/last.png",
    )
    body = _build_request_body(
        "kwaivgi/kling-v3.0-pro", item, callback_url=None
    )
    assert body["frame_images"] == [
        {
            "type": "image_url",
            "image_url": {"url": "https://assets.example/first.png"},
            "frame_type": "first_frame",
        },
        {
            "type": "image_url",
            "image_url": {"url": "https://assets.example/last.png"},
            "frame_type": "last_frame",
        },
    ]


def test_text_to_video_payload_stays_frame_free_without_references() -> None:
    body = _build_request_body(
        "kwaivgi/kling-v3.0-pro", _item(), callback_url=None
    )
    assert "frame_images" not in body


def test_non_https_frame_reference_is_rejected() -> None:
    with pytest.raises(FrameReferenceRoutingError, match="HTTPS"):
        build_openrouter_frame_images(
            _item(first_frame_url="http://assets.example/first.png")
        )
