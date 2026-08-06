from __future__ import annotations

import json
from collections.abc import Mapping

import pytest

from src.video_automation.models import ProviderRequest
from src.video_automation.seedance_ark_provider import (
    ArkJsonResponse,
    SeedanceArkProviderError,
    SeedanceArkVideoGenerationProvider,
)


class _Transport:
    def __init__(self, response: ArkJsonResponse | None = None) -> None:
        self.response = response or ArkJsonResponse(200, {"id": "cgt-001"})
        self.calls: list[
            tuple[str, Mapping[str, str], Mapping[str, object], float]
        ] = []

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> ArkJsonResponse:
        self.calls.append((url, headers, body, timeout_seconds))
        return self.response


def _request(
    *,
    provider_name: str = "volcengine-seedance",
    operation: str = "video.generate",
    request_count: int = 1,
    output_count: int = 1,
    items_json: str | None = None,
) -> ProviderRequest:
    if items_json is None:
        items_json = json.dumps(
            [
                {
                    "sequence_number": 1,
                    "request_id": "request-01",
                    "idempotency_key": "a" * 64,
                    "shot_id": "shot-01",
                    "prompt_text": "cinematic astronaut walking on the moon",
                    "duration_seconds": 5.0,
                    "aspect_ratio": "16:9",
                    "frames_per_second": 24,
                    "output_count": output_count,
                    "seed": None,
                }
            ],
            sort_keys=True,
            separators=(",", ":"),
        )
    return ProviderRequest(
        request_id="dispatch-001",
        job_id="dispatch-plan-001",
        provider_name=provider_name,
        operation=operation,
        payload={
            "model_id": "doubao-seedance-1-0-pro-250528",
            "batch_id": "batch-001",
            "batch_number": 1,
            "max_parallel_requests": 1,
            "request_count": request_count,
            "items_json": items_json,
        },
    )


def _provider(
    transport: _Transport,
    *,
    base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
    callback_url: str | None = None,
    return_last_frame: bool = False,
) -> SeedanceArkVideoGenerationProvider:
    return SeedanceArkVideoGenerationProvider(
        "secret-key",
        transport=transport,
        base_url=base_url,
        callback_url=callback_url,
        return_last_frame=return_last_frame,
    )


def test_capabilities_advertise_video_generation() -> None:
    provider = _provider(_Transport())
    assert provider.capabilities.provider_name == "volcengine-seedance"
    assert provider.capabilities.operations == ("video.generate",)
    assert provider.capabilities.is_paid


def test_execute_posts_to_official_ark_generation_endpoint() -> None:
    transport = _Transport()
    result = _provider(transport).execute(_request())
    assert result.success
    assert transport.calls[0][0] == (
        "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
    )


def test_execute_uses_bearer_auth_without_exposing_key_in_result() -> None:
    transport = _Transport()
    result = _provider(transport).execute(_request())
    headers = transport.calls[0][1]
    assert headers["Authorization"] == "Bearer secret-key"
    assert "secret-key" not in str(result.metadata)


def test_execute_maps_model_and_prompt_controls() -> None:
    transport = _Transport()
    _provider(transport).execute(_request())
    body = transport.calls[0][2]
    assert body["model"] == "doubao-seedance-1-0-pro-250528"
    content = body["content"]
    assert isinstance(content, tuple)
    text = content[0]["text"]
    assert "cinematic astronaut walking on the moon" in text
    assert "--ratio 16:9" in text
    assert "--dur 5" in text


def test_execute_returns_provider_task_id_as_external_id() -> None:
    result = _provider(_Transport()).execute(_request())
    assert result.external_id == "cgt-001"
    assert result.request_id == "dispatch-001"


def test_optional_callback_and_last_frame_are_forwarded() -> None:
    transport = _Transport()
    provider = _provider(
        transport,
        callback_url="https://example.test/callback",
        return_last_frame=True,
    )
    provider.execute(_request())
    body = transport.calls[0][2]
    assert body["callback_url"] == "https://example.test/callback"
    assert body["return_last_frame"] is True


def test_custom_base_url_is_normalized() -> None:
    transport = _Transport()
    provider = _provider(transport, base_url="https://ark.example.test/api/v3/")
    provider.execute(_request())
    assert transport.calls[0][0] == (
        "https://ark.example.test/api/v3/contents/generations/tasks"
    )


def test_provider_name_mismatch_returns_failed_result() -> None:
    result = _provider(_Transport()).execute(_request(provider_name="other"))
    assert not result.success
    assert result.error_code == "invalid_request"


def test_unsupported_operation_returns_failed_result() -> None:
    result = _provider(_Transport()).execute(_request(operation="image.generate"))
    assert not result.success
    assert result.error_code == "invalid_request"


def test_multiple_items_are_rejected_for_one_ark_submission() -> None:
    item = json.loads(str(_request().payload["items_json"]))[0]
    items_json = json.dumps([item, item])
    result = _provider(_Transport()).execute(
        _request(request_count=2, items_json=items_json)
    )
    assert not result.success
    assert "exactly one" in (result.error_message or "")


def test_output_count_greater_than_one_is_rejected() -> None:
    result = _provider(_Transport()).execute(_request(output_count=2))
    assert not result.success
    assert "output_count=1" in (result.error_message or "")


def test_invalid_items_json_is_rejected() -> None:
    result = _provider(_Transport()).execute(_request(items_json="not-json"))
    assert not result.success
    assert result.error_code == "invalid_request"


def test_http_error_is_normalized_from_ark_error_object() -> None:
    transport = _Transport(
        ArkJsonResponse(
            400,
            {"error": {"code": "InputTextSensitiveContentDetected", "message": "blocked"}},
        )
    )
    result = _provider(transport).execute(_request())
    assert not result.success
    assert result.error_code == "InputTextSensitiveContentDetected"
    assert result.error_message == "blocked"


def test_http_error_without_structured_error_uses_status_code() -> None:
    transport = _Transport(ArkJsonResponse(429, {"message": "quota exceeded"}))
    result = _provider(transport).execute(_request())
    assert not result.success
    assert result.error_code == "http_429"
    assert result.error_message == "quota exceeded"


def test_success_without_task_id_is_rejected() -> None:
    result = _provider(_Transport(ArkJsonResponse(200, {}))).execute(_request())
    assert not result.success
    assert result.error_code == "invalid_provider_response"


def test_transport_exception_is_normalized() -> None:
    class _FailingTransport(_Transport):
        def post_json(
            self,
            url: str,
            *,
            headers: Mapping[str, str],
            body: Mapping[str, object],
            timeout_seconds: float,
        ) -> ArkJsonResponse:
            raise RuntimeError("network unavailable")

    result = _provider(_FailingTransport()).execute(_request())
    assert not result.success
    assert result.error_code == "transport_error"
    assert result.error_message == "network unavailable"


def test_invalid_constructor_values_are_rejected() -> None:
    with pytest.raises(SeedanceArkProviderError, match="api_key"):
        SeedanceArkVideoGenerationProvider("  ")
    with pytest.raises(SeedanceArkProviderError, match="timeout_seconds"):
        SeedanceArkVideoGenerationProvider("key", timeout_seconds=0)
