from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import pytest

from services.integrations.reference_video_runtime import (
    ReferenceAwareOpenRouterVideoGenerationProvider,
)
from services.reference_assets import (
    ReferenceAssetError,
    ReferenceAssetStore,
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


def test_reference_asset_store_scopes_and_binds_content(tmp_path: Path) -> None:
    store = ReferenceAssetStore(tmp_path / "assets.sqlite3", tmp_path / "objects")
    record = store.ingest(
        principal_id="user-1",
        tenant_id="tenant-1",
        original_name="product.png",
        media_type="image/png",
        content=_png(),
    )
    assert record.asset_id.startswith("ref-")
    assert record.width == 320
    assert record.height == 180
    assert store.read_bytes(record) == _png()

    bound = store.bind_request(
        "exec-1",
        [record.asset_id],
        principal_id="user-1",
        tenant_id="tenant-1",
    )
    assert bound == (record,)
    assert store.for_request("exec-1") == (record,)

    with pytest.raises(ReferenceAssetError, match="not owned"):
        store.bind_request(
            "exec-2",
            [record.asset_id],
            principal_id="user-2",
            tenant_id="tenant-1",
        )


def test_reference_asset_store_rejects_spoofed_media(tmp_path: Path) -> None:
    store = ReferenceAssetStore(tmp_path / "assets.sqlite3", tmp_path / "objects")
    with pytest.raises(ReferenceAssetError, match="does not match"):
        store.ingest(
            principal_id="user-1",
            tenant_id="tenant-1",
            original_name="fake.jpg",
            media_type="image/jpeg",
            content=_png(),
        )


class _Transport:
    def __init__(self) -> None:
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
                            "description": "Supports multimodal reference-to-video.",
                            "pricing_skus": {"generate": "0"},
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
        return OpenRouterJsonResponse(202, {"id": "video-job-1", "status": "pending"})

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        raise AssertionError("not used")


def test_video_provider_consumes_bound_reference_images(tmp_path: Path) -> None:
    store = configure_reference_asset_store(
        tmp_path / "assets.sqlite3", tmp_path / "objects"
    )
    record = store.ingest(
        principal_id="user-1",
        tenant_id="tenant-1",
        original_name="reference.png",
        media_type="image/png",
        content=_png(),
    )
    store.bind_request(
        "exec-video",
        [record.asset_id],
        principal_id="user-1",
        tenant_id="tenant-1",
    )

    transport = _Transport()
    provider = ReferenceAwareOpenRouterVideoGenerationProvider(
        "test-key",
        transport=transport,
        default_resolution="720p",
    )
    item = {
        "prompt_text": "Keep the product identity consistent with the reference.",
        "duration_seconds": 4,
        "aspect_ratio": "16:9",
        "output_count": 1,
    }
    request = ProviderRequest(
        request_id="dispatch-1",
        job_id="dispatch-plan-1",
        provider_name=provider.capabilities.provider_name,
        operation="video.generate",
        payload={
            "model_id": "bytedance/seedance-2.0-fast:free",
            "request_count": 1,
            "items_json": json.dumps([item]),
        },
    )

    with reference_request_context("exec-video"):
        result = provider.execute(request)

    assert result.success is True
    assert transport.submitted_body is not None
    references = transport.submitted_body["input_references"]
    assert isinstance(references, list)
    assert len(references) == 1
    reference = cast(dict[str, object], references[0])
    image_url = cast(dict[str, object], reference["image_url"])
    url = image_url["url"]
    assert isinstance(url, str)
    assert url.startswith("data:image/png;base64,")
    assert base64.b64decode(url.split(",", 1)[1]) == _png()
    assert result.metadata["reference_asset_count"] == 1


class _NoReferenceCapabilityTransport(_Transport):
    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        if url.endswith("/videos/models"):
            return OpenRouterJsonResponse(
                200,
                {
                    "data": [
                        {
                            "id": "bytedance/seedance-2.0-fast:free",
                            "description": "Text-to-video only.",
                            "pricing_skus": {"generate": "0"},
                        }
                    ]
                },
            )
        raise AssertionError(f"unexpected GET: {url}")


def test_video_provider_fails_closed_when_reference_support_is_unproven(
    tmp_path: Path,
) -> None:
    store = configure_reference_asset_store(
        tmp_path / "assets.sqlite3", tmp_path / "objects"
    )
    record = store.ingest(
        principal_id="user-1",
        tenant_id="tenant-1",
        original_name="reference.png",
        media_type="image/png",
        content=_png(),
    )
    store.bind_request(
        "exec-video",
        [record.asset_id],
        principal_id="user-1",
        tenant_id="tenant-1",
    )
    transport = _NoReferenceCapabilityTransport()
    provider = ReferenceAwareOpenRouterVideoGenerationProvider(
        "test-key",
        transport=transport,
        default_resolution="720p",
    )
    request = ProviderRequest(
        request_id="dispatch-1",
        job_id="dispatch-plan-1",
        provider_name=provider.capabilities.provider_name,
        operation="video.generate",
        payload={
            "model_id": "bytedance/seedance-2.0-fast:free",
            "request_count": 1,
            "items_json": json.dumps(
                [
                    {
                        "prompt_text": "Use the reference.",
                        "duration_seconds": 4,
                        "aspect_ratio": "16:9",
                        "output_count": 1,
                    }
                ]
            ),
        },
    )
    with reference_request_context("exec-video"):
        result = provider.execute(request)
    assert result.success is False
    assert "REFERENCE_VIDEO_CAPABILITY_UNPROVEN" in (result.error_message or "")
    assert transport.submitted_body is None
