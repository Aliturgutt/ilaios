"""Managed-credit OpenRouter/Seedance provider for ILAIOS Video Factory.

The normal ILAIOS user never supplies an OpenRouter or Seedance credential. This
adapter is instantiated server-side with the ILAIOS-owned ``OPENROUTER_API_KEY``
and requires immutable ILAIOS credit-authorization evidence before any paid
network side effect.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from types import MappingProxyType
from typing import cast

from .models import MetadataValue, ProviderRequest, ProviderResult
from .openrouter_video_provider import (
    OpenRouterJsonResponse,
    OpenRouterTransport,
    UrllibOpenRouterTransport,
)
from .providers import ProviderCapabilities

OPENROUTER_MANAGED_PROVIDER_NAME = "openrouter-video-managed"
SEEDANCE_MANAGED_MODEL_IDS = (
    "bytedance/seedance-1-5-pro",
    "bytedance/seedance-2.0-fast",
    "bytedance/seedance-2.0",
)
_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
_DEFAULT_OPERATION = "video.generate"


class OpenRouterManagedVideoProviderError(ValueError):
    """Raised when managed provider execution fails before an external side effect."""


class OpenRouterManagedVideoGenerationProvider:
    """Submit a credit-authorized paid Seedance request through OpenRouter."""

    def __init__(
        self,
        api_key: str,
        *,
        provider_name: str = OPENROUTER_MANAGED_PROVIDER_NAME,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 30.0,
        transport: OpenRouterTransport | None = None,
    ) -> None:
        _require_text("api_key", api_key)
        _require_text("provider_name", provider_name)
        _require_text("base_url", base_url)
        if timeout_seconds <= 0:
            raise OpenRouterManagedVideoProviderError(
                "timeout_seconds must be greater than zero"
            )
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._transport = transport or UrllibOpenRouterTransport()
        self._capabilities = ProviderCapabilities(
            provider_name=provider_name,
            operations=(_DEFAULT_OPERATION,),
            is_paid=True,
            metadata={
                "backend": "openrouter",
                "credential_owner": "ILAIOS",
                "billing_authority": "managed_credits",
                "modality": "video",
            },
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def execute(self, request: ProviderRequest) -> ProviderResult:
        """Submit exactly one authorized paid video job."""

        try:
            self._validate_request(request)
            model_id, item = _parse_payload(request.payload)
            _require_seedance_model(model_id)
            authorization_id = _required_sha256(
                request.payload, "credit_authorization_id"
            )
            reserved_microusd = _required_positive_int(
                request.payload, "credit_reserved_microusd"
            )
            tenant_id = _required_string(request.payload, "tenant_id")
            user_id = _required_string(request.payload, "user_id")
            body = _build_request_body(model_id, item)
            response = self._transport.post_json(
                f"{self._base_url}/videos",
                headers=_auth_headers(self._api_key),
                body=body,
                timeout_seconds=self._timeout_seconds,
            )
        except OpenRouterManagedVideoProviderError as exc:
            return _failure(request, "invalid_request", str(exc))
        except Exception as exc:  # noqa: BLE001
            message = str(exc).strip() or exc.__class__.__name__
            return _failure(request, "transport_error", message)

        if not 200 <= response.status_code < 300:
            code, message = _normalize_error(response)
            return _failure(request, code, message)

        job_id = response.payload.get("id")
        if not isinstance(job_id, str) or not job_id.strip():
            return _failure(
                request,
                "invalid_provider_response",
                "OpenRouter response does not contain a non-empty video job id",
            )

        metadata: dict[str, MetadataValue] = {
            "backend": "openrouter",
            "billing_authority": "managed_credits",
            "credit_authorization_id": authorization_id,
            "credit_reserved_microusd": reserved_microusd,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "model_id": model_id,
        }
        provider_status = response.payload.get("status")
        if isinstance(provider_status, str) and provider_status.strip():
            metadata["submission_status"] = provider_status
        generation_id = response.payload.get("generation_id")
        if isinstance(generation_id, str) and generation_id.strip():
            metadata["generation_id"] = generation_id

        return ProviderResult(
            request_id=request.request_id,
            provider_name=request.provider_name,
            success=True,
            external_id=job_id,
            metadata=metadata,
        )

    def _validate_request(self, request: ProviderRequest) -> None:
        if request.provider_name != self.capabilities.provider_name:
            raise OpenRouterManagedVideoProviderError(
                "request provider_name does not match managed OpenRouter provider"
            )
        if request.operation != _DEFAULT_OPERATION:
            raise OpenRouterManagedVideoProviderError(
                f"unsupported operation: {request.operation}"
            )


def _parse_payload(
    payload: Mapping[str, MetadataValue],
) -> tuple[str, Mapping[str, object]]:
    model_id = _required_string(payload, "model_id")
    if payload.get("request_count") != 1:
        raise OpenRouterManagedVideoProviderError(
            "managed provider requires exactly one generation item per dispatch"
        )
    items_json = _required_string(payload, "items_json")
    try:
        parsed = json.loads(items_json)
    except json.JSONDecodeError as exc:
        raise OpenRouterManagedVideoProviderError("items_json is not valid JSON") from exc
    if not isinstance(parsed, list) or len(parsed) != 1:
        raise OpenRouterManagedVideoProviderError(
            "items_json must contain exactly one generation item"
        )
    item = parsed[0]
    if not isinstance(item, dict):
        raise OpenRouterManagedVideoProviderError("generation item must be an object")
    return model_id, cast(Mapping[str, object], item)


def _build_request_body(
    model_id: str,
    item: Mapping[str, object],
) -> Mapping[str, object]:
    prompt = _item_string(item, "prompt_text")
    aspect_ratio = _item_string(item, "aspect_ratio")
    duration = _item_positive_whole_number(item, "duration_seconds")
    if item.get("output_count") != 1:
        raise OpenRouterManagedVideoProviderError("output_count must equal 1")
    resolution = item.get("resolution", "480p")
    if not isinstance(resolution, str) or not resolution.strip():
        raise OpenRouterManagedVideoProviderError("resolution must be non-empty")
    generate_audio = item.get("generate_audio", False)
    if not isinstance(generate_audio, bool):
        raise OpenRouterManagedVideoProviderError("generate_audio must be boolean")

    # Deliberately return a normal dict: urllib transport JSON-serializes this body.
    body: dict[str, object] = {
        "model": model_id,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "duration": duration,
        "resolution": resolution,
        "generate_audio": generate_audio,
    }
    seed = item.get("seed")
    if seed is not None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise OpenRouterManagedVideoProviderError("seed must be an integer")
        body["seed"] = seed
    return body


def _require_seedance_model(model_id: str) -> None:
    if model_id not in SEEDANCE_MANAGED_MODEL_IDS:
        raise OpenRouterManagedVideoProviderError(
            "model is not in the governed paid Seedance allowlist"
        )


def _required_string(payload: Mapping[str, MetadataValue], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise OpenRouterManagedVideoProviderError(f"{name} must be a non-empty string")
    return value


def _required_positive_int(payload: Mapping[str, MetadataValue], name: str) -> int:
    value = payload.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise OpenRouterManagedVideoProviderError(f"{name} must be a positive integer")
    return value


def _required_sha256(payload: Mapping[str, MetadataValue], name: str) -> str:
    value = _required_string(payload, name)
    if len(value) != 64:
        raise OpenRouterManagedVideoProviderError(f"{name} must be a SHA-256 digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise OpenRouterManagedVideoProviderError(
            f"{name} must be hexadecimal"
        ) from exc
    return value


def _item_string(item: Mapping[str, object], name: str) -> str:
    value = item.get(name)
    if not isinstance(value, str) or not value.strip():
        raise OpenRouterManagedVideoProviderError(
            f"generation item {name} must be non-empty"
        )
    return value


def _item_positive_whole_number(item: Mapping[str, object], name: str) -> int:
    value = item.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OpenRouterManagedVideoProviderError(
            f"generation item {name} must be numeric"
        )
    normalized = float(value)
    if normalized <= 0 or not normalized.is_integer():
        raise OpenRouterManagedVideoProviderError(
            f"generation item {name} must be a positive whole number"
        )
    return int(normalized)


def _auth_headers(api_key: str) -> Mapping[str, str]:
    return MappingProxyType(
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    )


def _normalize_error(response: OpenRouterJsonResponse) -> tuple[str, str]:
    error = response.payload.get("error")
    if isinstance(error, Mapping):
        code = error.get("code")
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return str(code or f"http_{response.status_code}"), message
    if isinstance(error, str) and error.strip():
        return f"http_{response.status_code}", error
    message = response.payload.get("message")
    if isinstance(message, str) and message.strip():
        return f"http_{response.status_code}", message
    return (
        f"http_{response.status_code}",
        f"OpenRouter request failed with HTTP status {response.status_code}",
    )


def _failure(
    request: ProviderRequest,
    error_code: str,
    error_message: str,
) -> ProviderResult:
    return ProviderResult(
        request_id=request.request_id,
        provider_name=request.provider_name,
        success=False,
        error_code=error_code,
        error_message=error_message,
        metadata={"backend": "openrouter", "billing_authority": "managed_credits"},
    )


def _require_text(name: str, value: str) -> None:
    if not value or not value.strip():
        raise OpenRouterManagedVideoProviderError(f"{name} must not be blank")
