from __future__ import annotations

from collections.abc import Mapping

import pytest

from src.video_automation.openrouter_video_catalog import (
    ManagedVideoFamily,
    OpenRouterCatalogError,
    OpenRouterCatalogHealth,
    OpenRouterVideoCatalogClient,
)
from src.video_automation.openrouter_video_provider import (
    OpenRouterByteResponse,
    OpenRouterJsonResponse,
    OpenRouterTransport,
)


class _Clock:
    def __init__(self, value: float = 1_000.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


class _Transport(OpenRouterTransport):
    def __init__(self, responses: list[OpenRouterJsonResponse]) -> None:
        self.responses = responses
        self.get_calls: list[str] = []

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        raise AssertionError("catalog must not POST")

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        self.get_calls.append(url)
        if not self.responses:
            raise AssertionError("unexpected catalog refresh")
        return self.responses.pop(0)

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        raise AssertionError("catalog must not download bytes")


def _model(
    model_id: str,
    *,
    price: str | None = "0.50",
    audio: bool = True,
) -> dict[str, object]:
    return {
        "id": model_id,
        "canonical_slug": model_id,
        "name": model_id.rsplit("/", 1)[-1],
        "generate_audio": audio,
        "supported_aspect_ratios": ["16:9", "9:16"],
        "supported_durations": [4, 5, 8],
        "supported_frame_images": ["first_frame", "last_frame"],
        "supported_resolutions": ["480p", "720p"],
        "supported_sizes": None,
        "allowed_passthrough_parameters": [],
        "pricing_skus": None if price is None else {"generate": price},
    }


def _catalog_response() -> OpenRouterJsonResponse:
    return OpenRouterJsonResponse(
        200,
        {
            "data": [
                _model("bytedance/seedance-2.0"),
                _model("kwaivgi/kling-v3.0-pro"),
                _model("minimax/hailuo-2.3"),
                _model("alibaba/wan-2.7"),
                _model("google/veo-3.1"),
            ]
        },
    )


def test_authenticated_catalog_discovers_governed_candidate_families() -> None:
    transport = _Transport([_catalog_response()])
    client = OpenRouterVideoCatalogClient("server-secret", transport=transport)

    observation = client.refresh()

    assert observation.health is OpenRouterCatalogHealth.CONNECTED
    assert observation.snapshot is not None
    assert len(observation.snapshot.catalog_digest) == 64
    families = {model.family for model in client.paid_eligible_models()}
    assert families == {
        ManagedVideoFamily.SEEDANCE,
        ManagedVideoFamily.KLING,
        ManagedVideoFamily.HAILUO,
        ManagedVideoFamily.WAN,
    }
    ids = {model.model_id for model in client.paid_eligible_models()}
    assert "google/veo-3.1" not in ids
    assert transport.get_calls == ["https://openrouter.ai/api/v1/videos/models"]


def test_catalog_ttl_prevents_provider_hammering() -> None:
    clock = _Clock()
    transport = _Transport([_catalog_response(), _catalog_response()])
    client = OpenRouterVideoCatalogClient(
        "server-secret",
        transport=transport,
        clock=clock,
        ttl_seconds=60,
        max_paid_staleness_seconds=600,
    )

    first = client.observe()
    second = client.observe()
    assert first.snapshot == second.snapshot
    assert len(transport.get_calls) == 1

    clock.value += 61
    client.observe()
    assert len(transport.get_calls) == 2


def test_last_known_good_can_bridge_bounded_temporary_outage() -> None:
    clock = _Clock()
    transport = _Transport(
        [
            _catalog_response(),
            OpenRouterJsonResponse(503, {"error": "temporary"}),
        ]
    )
    client = OpenRouterVideoCatalogClient(
        "server-secret",
        transport=transport,
        clock=clock,
        ttl_seconds=60,
        max_paid_staleness_seconds=600,
    )
    client.refresh()
    clock.value += 61

    eligible = client.paid_eligible_models()

    assert eligible
    assert client.last_good_snapshot is not None
    assert len(transport.get_calls) == 2


def test_stale_pricing_fails_closed_even_with_last_known_good() -> None:
    clock = _Clock()
    transport = _Transport([_catalog_response(), OpenRouterJsonResponse(503, {})])
    client = OpenRouterVideoCatalogClient(
        "server-secret",
        transport=transport,
        clock=clock,
        ttl_seconds=60,
        max_paid_staleness_seconds=120,
    )
    client.refresh()
    clock.value += 121

    with pytest.raises(OpenRouterCatalogError, match="pricing is stale"):
        client.paid_eligible_models()


def test_unknown_or_invalid_pricing_never_becomes_paid_eligible() -> None:
    transport = _Transport(
        [
            OpenRouterJsonResponse(
                200,
                {
                    "data": [
                        _model("bytedance/seedance-2.0", price=None),
                        _model("kwaivgi/kling-v3.0-pro", price="not-a-number"),
                        _model("minimax/hailuo-2.3", price="-0.1"),
                    ]
                },
            )
        ]
    )
    client = OpenRouterVideoCatalogClient("server-secret", transport=transport)

    with pytest.raises(OpenRouterCatalogError, match="valid pricing"):
        client.paid_eligible_models()


def test_catalog_health_classifies_auth_rate_limit_and_invalid_schema() -> None:
    auth = OpenRouterVideoCatalogClient(
        "server-secret",
        transport=_Transport([OpenRouterJsonResponse(401, {})]),
    ).refresh()
    assert auth.health is OpenRouterCatalogHealth.AUTH_FAILED

    limited = OpenRouterVideoCatalogClient(
        "server-secret",
        transport=_Transport([OpenRouterJsonResponse(429, {})]),
    ).refresh()
    assert limited.health is OpenRouterCatalogHealth.RATE_LIMITED

    invalid = OpenRouterVideoCatalogClient(
        "server-secret",
        transport=_Transport([OpenRouterJsonResponse(200, {"data": "wrong"})]),
    ).refresh()
    assert invalid.health is OpenRouterCatalogHealth.CATALOG_INVALID
