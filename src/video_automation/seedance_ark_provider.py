"""Volcengine Ark Seedance adapter for provider-neutral video generation requests.

The adapter submits one text-to-video task to the official Volcengine Ark video
creation endpoint and normalizes the returned task identifier into ProviderResult.
It does not poll tasks, download assets, retry requests, select providers, or
modify execution-tracking state.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import ProviderRequest, ProviderResult
from .providers import ProviderCapabilities

_DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
_DEFAULT_OPERATION = "video.generate"


class SeedanceArkProviderError(ValueError):
    """Raised when a provider-neutral request cannot be submitted to Ark."""


@dataclass(frozen=True, slots=True)
class ArkJsonResponse:
    """Minimal immutable HTTP response used by the adapter transport."""

    status_code: int
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.status_code <= 0:
            raise SeedanceArkProviderError("status_code must be greater than zero")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


class ArkJsonTransport(Protocol):
    """Injectable JSON transport used for deterministic provider tests."""

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> ArkJsonResponse:
        """POST one JSON document and return a normalized JSON response."""


class UrllibArkJsonTransport:
    """Standard-library HTTPS transport for Volcengine Ark."""

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> ArkJsonResponse:
        encoded = json.dumps(body, separators=(",", ":")).encode("utf-8")
        request = Request(
            url,
            data=encoded,
            headers=dict(headers),
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                status = int(response.status)
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            return ArkJsonResponse(int(exc.code), _decode_json_object(raw))
        except URLError as exc:
            raise SeedanceArkProviderError(f"Ark transport error: {exc.reason}") from exc
        return ArkJsonResponse(status, _decode_json_object(raw))


class SeedanceArkVideoGenerationProvider:
    """Submit provider-neutral single-shot requests to Volcengine Ark Seedance."""

    def __init__(
        self,
        api_key: str,
        *,
        provider_name: str = "volcengine-seedance",
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 30.0,
        callback_url: str | None = None,
        return_last_frame: bool = False,
        transport: ArkJsonTransport | None = None,
    ) -> None:
        _require_non_blank("api_key", api_key)
        _require_non_blank("provider_name", provider_name)
        _require_non_blank("base_url", base_url)
        if timeout_seconds <= 0:
            raise SeedanceArkProviderError("timeout_seconds must be greater than zero")
        if callback_url is not None:
            _require_non_blank("callback_url", callback_url)
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._callback_url = callback_url
        self._return_last_frame = return_last_frame
        self._transport = transport or UrllibArkJsonTransport()
        self._capabilities = ProviderCapabilities(
            provider_name=provider_name,
            operations=(_DEFAULT_OPERATION,),
            is_paid=True,
            metadata={"backend": "volcengine-ark", "model_family": "seedance"},
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Return the canonical provider capabilities used by the registry."""

        return self._capabilities

    def execute(self, request: ProviderRequest) -> ProviderResult:
        """Create exactly one asynchronous Ark Seedance generation task."""

        try:
            self._validate_request(request)
            model_id, item = _parse_single_item_payload(request.payload)
            body = _build_ark_request_body(
                model_id,
                item,
                callback_url=self._callback_url,
                return_last_frame=self._return_last_frame,
            )
            response = self._transport.post_json(
                f"{self._base_url}/contents/generations/tasks",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                body=body,
                timeout_seconds=self._timeout_seconds,
            )
        except SeedanceArkProviderError as exc:
            return _failure_result(request, "invalid_request", str(exc))
        except Exception as exc:  # noqa: BLE001
            message = str(exc).strip() or exc.__class__.__name__
            return _failure_result(request, "transport_error", message)

        if not 200 <= response.status_code < 300:
            error_code, error_message = _normalize_ark_error(response)
            return _failure_result(request, error_code, error_message)

        task_id = response.payload.get("id")
        if not isinstance(task_id, str) or not task_id.strip():
            return _failure_result(
                request,
                "invalid_provider_response",
                "Ark response does not contain a non-empty task id",
            )

        return ProviderResult(
            request_id=request.request_id,
            provider_name=request.provider_name,
            success=True,
            external_id=task_id,
            metadata={
                "backend": "volcengine-ark",
                "submission_status": "accepted",
            },
        )

    def _validate_request(self, request: ProviderRequest) -> None:
        if request.provider_name != self.capabilities.provider_name:
            raise SeedanceArkProviderError(
                "request provider_name does not match Seedance provider name"
            )
        if request.operation != _DEFAULT_OPERATION:
            raise SeedanceArkProviderError(
                f"unsupported operation for Seedance adapter: {request.operation}"
            )


def _parse_single_item_payload(
    payload: Mapping[str, object],
) -> tuple[str, Mapping[str, object]]:
    model_id = payload.get("model_id")
    if not isinstance(model_id, str) or not model_id.strip():
        raise SeedanceArkProviderError("payload model_id must be a non-empty string")

    request_count = payload.get("request_count")
    if request_count != 1:
        raise SeedanceArkProviderError(
            "Seedance Ark adapter requires exactly one generation item per dispatch"
        )

    items_json = payload.get("items_json")
    if not isinstance(items_json, str) or not items_json:
        raise SeedanceArkProviderError("payload items_json must be a non-empty string")
    try:
        parsed = json.loads(items_json)
    except json.JSONDecodeError as exc:
        raise SeedanceArkProviderError("payload items_json is not valid JSON") from exc
    if not isinstance(parsed, list) or len(parsed) != 1:
        raise SeedanceArkProviderError(
            "items_json must contain exactly one generation item"
        )
    item = parsed[0]
    if not isinstance(item, dict):
        raise SeedanceArkProviderError("generation item must be an object")
    return model_id, cast(Mapping[str, object], item)


def _build_ark_request_body(
    model_id: str,
    item: Mapping[str, object],
    *,
    callback_url: str | None,
    return_last_frame: bool,
) -> Mapping[str, object]:
    prompt = _required_string(item, "prompt_text")
    aspect_ratio = _required_string(item, "aspect_ratio")
    duration = _required_positive_number(item, "duration_seconds")
    output_count = item.get("output_count")
    if output_count != 1:
        raise SeedanceArkProviderError(
            "Seedance Ark adapter requires output_count=1 per generation item"
        )

    prompt_with_controls = (
        f"{prompt} --ratio {aspect_ratio} --dur {_format_number(duration)}"
    )
    body: dict[str, object] = {
        "model": model_id,
        "content": ({"type": "text", "text": prompt_with_controls},),
    }
    if callback_url is not None:
        body["callback_url"] = callback_url
    if return_last_frame:
        body["return_last_frame"] = True
    return MappingProxyType(body)


def _required_string(item: Mapping[str, object], name: str) -> str:
    value = item.get(name)
    if not isinstance(value, str) or not value.strip():
        raise SeedanceArkProviderError(f"generation item {name} must be non-empty")
    return value


def _required_positive_number(item: Mapping[str, object], name: str) -> float:
    value = item.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SeedanceArkProviderError(f"generation item {name} must be numeric")
    normalized = float(value)
    if normalized <= 0:
        raise SeedanceArkProviderError(
            f"generation item {name} must be greater than zero"
        )
    return normalized


def _format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return format(value, "g")


def _normalize_ark_error(response: ArkJsonResponse) -> tuple[str, str]:
    error = response.payload.get("error")
    if isinstance(error, Mapping):
        code = error.get("code")
        message = error.get("message")
        normalized_code = code if isinstance(code, str) and code.strip() else None
        normalized_message = (
            message if isinstance(message, str) and message.strip() else None
        )
        if normalized_message is not None:
            return normalized_code or f"http_{response.status_code}", normalized_message
    message = response.payload.get("message")
    if isinstance(message, str) and message.strip():
        return f"http_{response.status_code}", message
    return (
        f"http_{response.status_code}",
        f"Ark request failed with HTTP status {response.status_code}",
    )


def _failure_result(
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
        metadata={"backend": "volcengine-ark"},
    )


def _decode_json_object(raw: str) -> Mapping[str, object]:
    if not raw.strip():
        return MappingProxyType({})
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return MappingProxyType({"message": raw.strip()})
    if not isinstance(parsed, dict):
        return MappingProxyType({"message": "Ark response is not a JSON object"})
    return MappingProxyType(cast(dict[str, object], parsed))


def _require_non_blank(name: str, value: str) -> None:
    if not value.strip():
        raise SeedanceArkProviderError(f"{name} must not be blank")
