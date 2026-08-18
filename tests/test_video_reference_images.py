from __future__ import annotations

import json

import pytest

from src.video_automation.models import ProviderRequest
from src.video_automation.openrouter_managed_video_gateway import (
    OpenRouterManagedVideoGatewayError,
    _validate_capabilities,
)
from src.video_automation.openrouter_managed_video_provider import _build_request_body
from src.video_automation.openrouter_video_catalog import (
    ManagedVideoFamily,
    OpenRouterVideoModel,
)
from src.video_automation.reference_images import (
    DEFAULT_PROVIDER_REFERENCE_IMAGES,
    MAX_USER_REFERENCE_IMAGES,
    ReferenceImageError,
    ReferenceImageRole,
    VideoReferenceImage,
    select_provider_references,
    validate_reference_pool,
)


def _reference(index: int, role: ReferenceImageRole) -> VideoReferenceImage:
    return VideoReferenceImage(
        asset_id=f"asset-{index}",
        sha256_digest=f"{index:064x}",
        https_url=f"https://assets.example/reference-{index}.jpg",
        role=role,
    )


def _seedance_model(model_id: str = "bytedance/seedance-2.0-fast") -> OpenRouterVideoModel:
    return OpenRouterVideoModel(
        model_id=model_id,
        canonical_slug=model_id,
        name="Seedance",
        generate_audio=True,
        supported_aspect_ratios=("16:9",),
        supported_durations=(4, 8),
        supported_frame_images=("first_frame", "last_frame"),
        supported_resolutions=("720p",),
        supported_sizes=(),
        allowed_passthrough_parameters=(),
        pricing_skus={"per-video-second-720p": "0.10"},
        family=ManagedVideoFamily.SEEDANCE,
    )


def _item(references: tuple[VideoReferenceImage, ...]) -> dict[str, object]:
    return {
        "request_id": "request-001",
        "shot_id": "shot-001",
        "prompt_text": "keep the referenced product visually consistent",
        "duration_seconds": 4,
        "aspect_ratio": "16:9",
        "output_count": 1,
        "resolution": "720p",
        "generate_audio": False,
        "reference_images": [reference.to_wire() for reference in references],
    }


def _request(model_id: str, item: dict[str, object]) -> ProviderRequest:
    return ProviderRequest(
        request_id="request-001",
        job_id="job-001",
        provider_name="openrouter-video-managed",
        operation="video.generate",
        payload={
            "model_id": model_id,
            "request_count": 1,
            "items_json": json.dumps([item], separators=(",", ":")),
        },
    )


def test_user_reference_pool_accepts_eight_and_rejects_nine() -> None:
    eight = tuple(
        _reference(index, ReferenceImageRole.SUBJECT_SECONDARY)
        for index in range(1, MAX_USER_REFERENCE_IMAGES + 1)
    )
    assert validate_reference_pool(eight) == eight
    with pytest.raises(ReferenceImageError, match="at most 8"):
        validate_reference_pool(eight + (_reference(9, ReferenceImageRole.STYLE),))


def test_duplicate_reference_content_fails_closed() -> None:
    first = _reference(1, ReferenceImageRole.SUBJECT_PRIMARY)
    duplicate = VideoReferenceImage(
        asset_id="different-asset",
        sha256_digest=first.sha256_digest,
        https_url="https://assets.example/duplicate.jpg",
        role=ReferenceImageRole.STYLE,
    )
    with pytest.raises(ReferenceImageError, match="duplicate reference image content"):
        validate_reference_pool((first, duplicate))


def test_provider_selection_is_bounded_and_quality_prioritized() -> None:
    references = (
        _reference(1, ReferenceImageRole.ENVIRONMENT),
        _reference(2, ReferenceImageRole.STYLE),
        _reference(3, ReferenceImageRole.SUBJECT_SECONDARY),
        _reference(4, ReferenceImageRole.DETAIL),
        _reference(5, ReferenceImageRole.SUBJECT_PRIMARY),
    )
    selection = select_provider_references(references)
    assert selection.selected_count == DEFAULT_PROVIDER_REFERENCE_IMAGES
    assert [item.asset_id for item in selection.selected] == [
        "asset-5",
        "asset-3",
        "asset-4",
    ]
    assert selection.omitted_asset_ids == ("asset-1", "asset-2")


def test_openrouter_emits_three_reference_images_from_larger_user_pool() -> None:
    references = tuple(
        _reference(index, ReferenceImageRole.SUBJECT_SECONDARY)
        for index in range(1, 6)
    )
    body = _build_request_body(
        "bytedance/seedance-2.0-fast",
        _item(references),
        callback_url=None,
    )
    assert len(body["input_references"]) == 3
    assert body["input_references"] == [
        {
            "type": "image_url",
            "image_url": {"url": f"https://assets.example/reference-{index}.jpg"},
        }
        for index in (1, 2, 3)
    ]
    assert "frame_images" not in body


def test_reference_images_and_exact_frame_anchor_never_mix_silently() -> None:
    item = _item((_reference(1, ReferenceImageRole.SUBJECT_PRIMARY),))
    item["first_frame_url"] = "https://assets.example/first.jpg"
    with pytest.raises(ValueError, match="mutually exclusive"):
        _build_request_body(
            "bytedance/seedance-2.0-fast",
            item,
            callback_url=None,
        )


def test_unverified_reference_model_fails_before_paid_post() -> None:
    item = _item((_reference(1, ReferenceImageRole.SUBJECT_PRIMARY),))
    with pytest.raises(
        OpenRouterManagedVideoGatewayError,
        match="no verified reference-to-video capability evidence",
    ):
        _validate_capabilities(
            _request("bytedance/seedance-1-5-pro", item),
            _seedance_model("bytedance/seedance-1-5-pro"),
        )


def test_verified_reference_model_passes_gateway_capability_gate() -> None:
    item = _item((_reference(1, ReferenceImageRole.SUBJECT_PRIMARY),))
    _validate_capabilities(
        _request("bytedance/seedance-2.0-fast", item),
        _seedance_model(),
    )


def test_non_https_reference_url_is_rejected() -> None:
    with pytest.raises(ReferenceImageError, match="absolute HTTPS"):
        VideoReferenceImage(
            asset_id="asset-insecure",
            sha256_digest="1" * 64,
            https_url="http://assets.example/reference.jpg",
        )
