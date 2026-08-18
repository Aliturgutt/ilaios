from __future__ import annotations

import pytest

from services.integrations.video_product_intelligence import (
    VideoProductIntentError,
    derive_video_product_spec,
    validate_video_product_inputs,
)


def test_vertical_request_fails_before_current_16_9_runtime_can_misdeliver() -> None:
    spec = derive_video_product_spec("Create a vertical 9:16 launch video.")
    with pytest.raises(VideoProductIntentError, match="mismatched video"):
        validate_video_product_inputs(
            spec,
            source_video_present=False,
            supported_aspect_ratios=("16:9",),
        )


def test_current_native_shape_is_admitted() -> None:
    spec = derive_video_product_spec("Create a cinematic 16:9 launch video.")
    validate_video_product_inputs(
        spec,
        source_video_present=False,
        supported_aspect_ratios=("16:9",),
    )
