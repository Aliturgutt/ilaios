from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from pathlib import Path

from services.integrations.reference_video_runtime import (
    ReferenceAwareOpenRouterVideoGenerationProvider,
)
from services.reference_assets import (
    configure_reference_asset_store,
    reference_request_context,
)
from src.video_automation.models import ProviderRequest
from src.video_automation.openrouter_video_provider import (
    OpenRouterByteResponse,
    OpenRouterJsonResponse,
)


def _png(width: int = 320, height: int = 180) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + (13).to_bytes(4, "big")
        + b"IHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x06\x00\x00\x00"
        + b"\x00" * 32
    )


class _FrameTransport:
    def __init__(self, *, supported: tuple[str, ...]) -> None:
        self.supported = supported
        self.submitted_body: Mapping[str, object] | None = None

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        assert headers["Authorization"].startswith("Bearer ")
        if url.endswith("/videos/models"):
            return OpenRouterJsonResponse(
                200,
                {
                    "data": [
                        {
                            "id": "bytedance/seedance-2.0-fast:free",
                            "description": "Video model with reference guidance.",
                            "pricing_skus": {"generate": "0"},
                            "supported_frame_images": list(self.supported),
                        }
                    ]
                },
            )
        raise AssertionError(f"unexpected GET: {url}")

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        assert url.endswith("/videos")
        self.submitted_body = body
        return OpenRouterJsonResponse(202, {"id": "frame-job-1", "status": "pending"})

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        raise AssertionError("not used")


def _request(
    provider: ReferenceAwareOpenRouterVideoGenerationProvider,
    prompt: str,
) -> ProviderRequest:
    return ProviderRequest(
        request_id="dispatch-frame-1",
        job_id="dispatch-plan-1",
        provider_name=provider.capabilities.provider_name,
        operation="video.generate",
        payload={
            "model_id": "bytedance/seedance-2.0-fast:free",
            "request_count": 1,
            "items_json": json.dumps(
                [
                    {
                        "prompt_text": prompt,
                        "duration_seconds": 4,
                        "aspect_ratio": "16:9",
                        "output_count": 1,
                    }
                ]
            ),
        },
    )


def _bind_one(tmp_path: Path) -> bytes:
    content = _png()
    store = configure_reference_asset_store(
        tmp_path / "assets.sqlite3", tmp_path / "objects"
    )
    record = store.ingest(
        principal_id="user-1",
        tenant_id="tenant-1",
        original_name="first.png",
        media_type="image/png",
        content=content,
    )
    store.bind_request(
        "exec-frame",
        [record.asset_id],
        principal_id="user-1",
        tenant_id="tenant-1",
    )
    return content


def test_exact_first_frame_uses_frame_images_not_general_references(tmp_path: Path) -> None:
    content = _bind_one(tmp_path)
    transport = _FrameTransport(supported=("first_frame", "last_frame"))
    provider = ReferenceAwareOpenRouterVideoGenerationProvider(
        "test-key", transport=transport, default_resolution="720p"
    )
    with reference_request_context("exec-frame"):
        result = provider.execute(
            _request(provider, "Use my uploaded image as the first frame of the video.")
        )

    assert result.success is True
    assert transport.submitted_body is not None
    assert "input_references" not in transport.submitted_body
    raw_frames = transport.submitted_body.get("frame_images")
    assert isinstance(raw_frames, list)
    assert len(raw_frames) == 1
    frame = raw_frames[0]
    assert isinstance(frame, Mapping)
    assert frame.get("frame_type") == "first_frame"
    raw_image_url = frame.get("image_url")
    assert isinstance(raw_image_url, Mapping)
    url = raw_image_url.get("url")
    assert isinstance(url, str)
    assert base64.b64decode(url.split(",", 1)[1]) == content
    assert result.metadata["reference_mode"] == "frame_images"


def test_exact_frame_request_fails_before_post_when_catalog_does_not_prove_support(
    tmp_path: Path,
) -> None:
    _bind_one(tmp_path)
    transport = _FrameTransport(supported=())
    provider = ReferenceAwareOpenRouterVideoGenerationProvider(
        "test-key", transport=transport, default_resolution="720p"
    )
    with reference_request_context("exec-frame"):
        result = provider.execute(
            _request(provider, "Use my uploaded image as the first frame of the video.")
        )

    assert result.success is False
    assert "FRAME_VIDEO_CAPABILITY_UNPROVEN" in (result.error_message or "")
    assert transport.submitted_body is None
