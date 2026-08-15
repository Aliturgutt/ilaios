from __future__ import annotations

from collections.abc import Mapping

from src.video_automation.openrouter_video_catalog import (
    OpenRouterCatalogHealth,
    OpenRouterVideoCatalogClient,
)
from src.video_automation.openrouter_video_provider import (
    OpenRouterByteResponse,
    OpenRouterJsonResponse,
    OpenRouterTransport,
)


class _Transport(OpenRouterTransport):
    def __init__(self, payload: Mapping[str, object]) -> None:
        self.payload = payload

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        raise AssertionError("catalog test must not POST")

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        return OpenRouterJsonResponse(200, self.payload)

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        raise AssertionError("catalog test must not download bytes")


def _model(generate_audio: object) -> dict[str, object]:
    return {
        "id": "bytedance/seedance-2.0-fast",
        "canonical_slug": "bytedance/seedance-2.0-fast",
        "name": "Seedance 2.0 Fast",
        "generate_audio": generate_audio,
        "supported_aspect_ratios": ["16:9"],
        "supported_durations": [4],
        "supported_frame_images": [],
        "supported_resolutions": ["480p"],
        "supported_sizes": None,
        "allowed_passthrough_parameters": [],
        "pricing_skus": {"per-video-second": "0.05"},
    }


def test_null_audio_capability_is_conservatively_normalized_false() -> None:
    client = OpenRouterVideoCatalogClient(
        "server-secret",
        transport=_Transport({"data": [_model(None)]}),
    )

    observation = client.refresh()

    assert observation.health is OpenRouterCatalogHealth.CONNECTED
    assert observation.snapshot is not None
    model = observation.snapshot.models[0]
    assert model.generate_audio is False
    assert client.paid_eligible_models() == (model,)


def test_non_null_non_boolean_audio_capability_remains_invalid() -> None:
    client = OpenRouterVideoCatalogClient(
        "server-secret",
        transport=_Transport({"data": [_model("false")]}),
    )

    observation = client.refresh()

    assert observation.health is OpenRouterCatalogHealth.CATALOG_INVALID
    assert observation.snapshot is None
    assert observation.detail == "generate_audio must be boolean or null"
