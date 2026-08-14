"""OpenRouter video generation adapters for the canonical Video Factory.

The module implements provider-neutral submit, poll, and generated-asset retrieval
against OpenRouter's asynchronous ``/api/v1/videos`` API.  It intentionally does
not select models, bypass the canonical provider registry, perform retries, or
claim production success without external provider evidence.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .generated_asset_retrieval import GeneratedAssetPayload
from .generation_job_polling import ProviderJobObservation, ProviderJobStatus
from .models import ProviderRequest, ProviderResult
from .providers import ProviderCapabilities

_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
_DEFAULT_OPERATION = "video.generate"
_DEFAULT_PROVIDER_NAME = "openrouter-video"
_DEFAULT_RESOLUTION = "480p"


class OpenRouterVideoProviderError(ValueError):
    """Raised when an OpenRouter video request cannot be handled safely."""


@dataclass(frozen=True, slots=True)
class OpenRouterJsonResponse:
    """Minimal immutable JSON response used by submit/poll transports."""

    status_code: int
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.status_code <= 0:
            raise OpenRouterVideoProviderError("status_code must be greater than zero")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


@dataclass(frozen=True, slots=True)
class OpenRouterByteResponse:
    """Immutable media response returned by the content endpoint."""

    status_code: int
    body: bytes
    content_type: str
    final_url: str

    def __post_init__(self) -> None:
        if self.status_code <= 0:
            raise OpenRouterVideoProviderError("status_code must be greater than zero")
        if not self.body:
            raise OpenRouterVideoProviderError("body must not be empty")
        _require_non_blank("content_type", self.content_type)
        _require_non_blank("final_url", self.final_url)


class OpenRouterTransport(Protocol):
    """Injectable HTTP transport for deterministic OpenRouter adapter tests."""

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        """POST one JSON object."""

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        """GET one JSON object."""

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        """GET one media payload."""


class UrllibOpenRouterTransport:
    """Standard-library HTTPS transport for the OpenRouter video API."""

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        encoded = json.dumps(body, separators=(",", ":")).encode("utf-8")
        request = Request(url, data=encoded, headers=dict(headers), method="POST")
        return self._json_request(request, timeout_seconds)

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        request = Request(url, headers=dict(headers), method="GET")
        return self._json_request(request, timeout_seconds)

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        request = Request(url, headers=dict(headers), method="GET")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                status = int(response.status)
                body = response.read()
                content_type = response.headers.get_content_type()
                final_url = response.geturl()
        except HTTPError as exc:
            raise OpenRouterVideoProviderError(
                f"OpenRouter content request failed with status {exc.code}"
            ) from exc
        except URLError as exc:
            raise OpenRouterVideoProviderError(
                f"OpenRouter transport error: {exc.reason}"
            ) from exc
        return OpenRouterByteResponse(status, body, content_type, final_url)

    @staticmethod
    def _json_request(
        request: Request,
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                status = int(response.status)
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            return OpenRouterJsonResponse(int(exc.code), _decode_json_object(raw))
        except URLError as exc:
            raise OpenRouterVideoProviderError(
                f"OpenRouter transport error: {exc.reason}"
            ) from exc
        return OpenRouterJsonResponse(status, _decode_json_object(raw))


class OpenRouterVideoGenerationProvider:
    """Submit one provider-neutral Video Factory request to OpenRouter."""

    def __init__(
        self,
        api_key: str,
        *,
        provider_name: str = _DEFAULT_PROVIDER_NAME,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 30.0,
        default_resolution: str = _DEFAULT_RESOLUTION,
        generate_audio: bool = False,
        transport: OpenRouterTransport | None = None,
    ) -> None:
        _require_non_blank("api_key", api_key)
        _require_non_blank("provider_name", provider_name)
        _require_non_blank("base_url", base_url)
        _require_non_blank("default_resolution", default_resolution)
        if timeout_seconds <= 0:
            raise OpenRouterVideoProviderError(
                "timeout_seconds must be greater than zero"
            )
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._default_resolution = default_resolution
        self._generate_audio = generate_audio
        self._transport = transport or UrllibOpenRouterTransport()
        self._capabilities = ProviderCapabilities(
            provider_name=provider_name,
            operations=(_DEFAULT_OPERATION,),
            is_paid=True,
            metadata={"backend": "openrouter", "modality": "video"},
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def execute(self, request: ProviderRequest) -> ProviderResult:
        """Submit exactly one asynchronous OpenRouter video generation job."""

        try:
            self._validate_request(request)
            model_id, item = _parse_single_item_payload(request.payload)
            body = _build_openrouter_request_body(
                model_id,
                item,
                default_resolution=self._default_resolution,
                generate_audio=self._generate_audio,
            )
            response = self._transport.post_json(
                f"{self._base_url}/videos",
                headers=_auth_headers(self._api_key, json_content=True),
                body=body,
                timeout_seconds=self._timeout_seconds,
            )
        except OpenRouterVideoProviderError as exc:
            return _failure_result(request, "invalid_request", str(exc))
        except Exception as exc:  # noqa: BLE001
            message = str(exc).strip() or exc.__class__.__name__
            return _failure_result(request, "transport_error", message)

        if not 200 <= response.status_code < 300:
            code, message = _normalize_error(response)
            return _failure_result(request, code, message)

        job_id = response.payload.get("id")
        if not isinstance(job_id, str) or not job_id.strip():
            return _failure_result(
                request,
                "invalid_provider_response",
                "OpenRouter response does not contain a non-empty video job id",
            )
        metadata = {
            "backend": "openrouter",
            "submission_status": _string_or_default(
                response.payload.get("status"), "accepted"
            ),
        }
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
            raise OpenRouterVideoProviderError(
                "request provider_name does not match OpenRouter provider name"
            )
        if request.operation != _DEFAULT_OPERATION:
            raise OpenRouterVideoProviderError(
                f"unsupported operation for OpenRouter video adapter: {request.operation}"
            )


class OpenRouterVideoGenerationJobPoller:
    """Normalize OpenRouter video job status into the canonical polling contract."""

    def __init__(
        self,
        api_key: str,
        *,
        provider_id: str = _DEFAULT_PROVIDER_NAME,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 30.0,
        transport: OpenRouterTransport | None = None,
    ) -> None:
        _require_non_blank("api_key", api_key)
        _require_non_blank("provider_id", provider_id)
        _require_non_blank("base_url", base_url)
        if timeout_seconds <= 0:
            raise OpenRouterVideoProviderError(
                "timeout_seconds must be greater than zero"
            )
        self._api_key = api_key
        self._provider_id = provider_id
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._transport = transport or UrllibOpenRouterTransport()

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def poll(self, provider_job_id: str) -> ProviderJobObservation:
        _require_non_blank("provider_job_id", provider_job_id)
        encoded_id = quote(provider_job_id, safe="")
        response = self._transport.get_json(
            f"{self._base_url}/videos/{encoded_id}",
            headers=_auth_headers(self._api_key),
            timeout_seconds=self._timeout_seconds,
        )
        if not 200 <= response.status_code < 300:
            code, message = _normalize_error(response)
            raise OpenRouterVideoProviderError(f"{code}: {message}")
        return _normalize_poll_observation(
            self._provider_id,
            provider_job_id,
            self._base_url,
            response.payload,
        )


class OpenRouterGeneratedAssetRetriever:
    """Download generated video bytes from OpenRouter's authenticated content endpoint."""

    def __init__(
        self,
        api_key: str,
        *,
        provider_id: str = _DEFAULT_PROVIDER_NAME,
        timeout_seconds: float = 120.0,
        transport: OpenRouterTransport | None = None,
    ) -> None:
        _require_non_blank("api_key", api_key)
        _require_non_blank("provider_id", provider_id)
        if timeout_seconds <= 0:
            raise OpenRouterVideoProviderError(
                "timeout_seconds must be greater than zero"
            )
        self._api_key = api_key
        self._provider_id = provider_id
        self._timeout_seconds = timeout_seconds
        self._transport = transport or UrllibOpenRouterTransport()

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def retrieve(self, asset_id: str) -> GeneratedAssetPayload:
        if not asset_id.startswith("https://openrouter.ai/api/v1/videos/"):
            raise OpenRouterVideoProviderError(
                "OpenRouter generated asset id must use the canonical HTTPS content endpoint"
            )
        response = self._transport.get_bytes(
            asset_id,
            headers=_auth_headers(self._api_key),
            timeout_seconds=self._timeout_seconds,
        )
        if not 200 <= response.status_code < 300:
            raise OpenRouterVideoProviderError(
                f"OpenRouter content request failed with status {response.status_code}"
            )
        normalized_type = response.content_type.split(";", 1)[0].strip().lower()
        if normalized_type != "video/mp4":
            raise OpenRouterVideoProviderError(
                f"unsupported OpenRouter video content type: {normalized_type}"
            )
        return GeneratedAssetPayload(
            source_asset_id=asset_id,
            body=response.body,
            content_type="video/mp4",
            file_extension=".mp4",
            metadata={"final_url": response.final_url, "backend": "openrouter"},
        )


def _parse_single_item_payload(
    payload: Mapping[str, object],
) -> tuple[str, Mapping[str, object]]:
    model_id = payload.get("model_id")
    if not isinstance(model_id, str) or not model_id.strip():
        raise OpenRouterVideoProviderError("payload model_id must be a non-empty string")
    if payload.get("request_count") != 1:
        raise OpenRouterVideoProviderError(
            "OpenRouter video adapter requires exactly one generation item per dispatch"
        )
    items_json = payload.get("items_json")
    if not isinstance(items_json, str) or not items_json:
        raise OpenRouterVideoProviderError("payload items_json must be a non-empty string")
    try:
        parsed = json.loads(items_json)
    except json.JSONDecodeError as exc:
        raise OpenRouterVideoProviderError("payload items_json is not valid JSON") from exc
    if not isinstance(parsed, list) or len(parsed) != 1:
        raise OpenRouterVideoProviderError(
            "items_json must contain exactly one generation item"
        )
    item = parsed[0]
    if not isinstance(item, dict):
        raise OpenRouterVideoProviderError("generation item must be an object")
    return model_id, cast(Mapping[str, object], item)


def _build_openrouter_request_body(
    model_id: str,
    item: Mapping[str, object],
    *,
    default_resolution: str,
    generate_audio: bool,
) -> Mapping[str, object]:
    prompt = _required_string(item, "prompt_text")
    aspect_ratio = _required_string(item, "aspect_ratio")
    duration = _required_integral_duration(item, "duration_seconds")
    output_count = item.get("output_count")
    if output_count != 1:
        raise OpenRouterVideoProviderError(
            "OpenRouter video adapter requires output_count=1 per generation item"
        )
    resolution = item.get("resolution")
    if resolution is None:
        normalized_resolution = default_resolution
    elif isinstance(resolution, str) and resolution.strip():
        normalized_resolution = resolution
    else:
        raise OpenRouterVideoProviderError("generation item resolution must be non-empty")

    body: dict[str, object] = {
        "model": model_id,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "duration": duration,
        "resolution": normalized_resolution,
        "generate_audio": generate_audio,
    }
    seed = item.get("seed")
    if seed is not None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise OpenRouterVideoProviderError("generation item seed must be an integer")
        body["seed"] = seed
    return MappingProxyType(body)


def _normalize_poll_observation(
    provider_id: str,
    provider_job_id: str,
    base_url: str,
    payload: Mapping[str, object],
) -> ProviderJobObservation:
    status_value = payload.get("status")
    if not isinstance(status_value, str) or not status_value.strip():
        raise OpenRouterVideoProviderError(
            "OpenRouter video status response requires string status"
        )
    normalized = status_value.strip().lower()
    status_map = {
        "pending": ProviderJobStatus.QUEUED,
        "queued": ProviderJobStatus.QUEUED,
        "processing": ProviderJobStatus.RUNNING,
        "running": ProviderJobStatus.RUNNING,
        "completed": ProviderJobStatus.SUCCEEDED,
        "succeeded": ProviderJobStatus.SUCCEEDED,
        "failed": ProviderJobStatus.FAILED,
        "cancelled": ProviderJobStatus.CANCELLED,
        "canceled": ProviderJobStatus.CANCELLED,
    }
    try:
        status = status_map[normalized]
    except KeyError as exc:
        raise OpenRouterVideoProviderError(
            f"unsupported OpenRouter video job status: {status_value}"
        ) from exc

    metadata: dict[str, str] = {"provider_status": normalized}
    generation_id = payload.get("generation_id")
    if isinstance(generation_id, str) and generation_id.strip():
        metadata["generation_id"] = generation_id
    usage = payload.get("usage")
    if isinstance(usage, Mapping):
        metadata["usage_json"] = json.dumps(
            dict(usage), sort_keys=True, separators=(",", ":")
        )

    if status is ProviderJobStatus.SUCCEEDED:
        content_url = (
            f"{base_url}/videos/{quote(provider_job_id, safe='')}/content"
        )
        return ProviderJobObservation(
            provider_id=provider_id,
            provider_job_id=provider_job_id,
            status=status,
            output_asset_ids=(content_url,),
            metadata=metadata,
        )
    if status is ProviderJobStatus.FAILED:
        error = payload.get("error")
        error_code = "provider_failed"
        error_message: str | None = None
        if isinstance(error, str) and error.strip():
            error_message = error
        elif isinstance(error, Mapping):
            raw_code = error.get("code")
            raw_message = error.get("message")
            if isinstance(raw_code, str) and raw_code.strip():
                error_code = raw_code
            if isinstance(raw_message, str) and raw_message.strip():
                error_message = raw_message
        return ProviderJobObservation(
            provider_id=provider_id,
            provider_job_id=provider_job_id,
            status=status,
            error_code=error_code,
            error_message=error_message,
            metadata=metadata,
        )
    return ProviderJobObservation(
        provider_id=provider_id,
        provider_job_id=provider_job_id,
        status=status,
        metadata=metadata,
    )


def _normalize_error(response: OpenRouterJsonResponse) -> tuple[str, str]:
    error = response.payload.get("error")
    if isinstance(error, Mapping):
        code = error.get("code")
        message = error.get("message")
        normalized_code = str(code) if code is not None else None
        if isinstance(message, str) and message.strip():
            return normalized_code or f"http_{response.status_code}", message
    if isinstance(error, str) and error.strip():
        return f"http_{response.status_code}", error
    message = response.payload.get("message")
    if isinstance(message, str) and message.strip():
        return f"http_{response.status_code}", message
    return (
        f"http_{response.status_code}",
        f"OpenRouter request failed with HTTP status {response.status_code}",
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
        metadata={"backend": "openrouter"},
    )


def _auth_headers(api_key: str, *, json_content: bool = False) -> Mapping[str, str]:
    headers = {"Authorization": f"Bearer {api_key}"}
    if json_content:
        headers["Content-Type"] = "application/json"
    return MappingProxyType(headers)


def _required_string(item: Mapping[str, object], name: str) -> str:
    value = item.get(name)
    if not isinstance(value, str) or not value.strip():
        raise OpenRouterVideoProviderError(
            f"generation item {name} must be non-empty"
        )
    return value


def _required_integral_duration(item: Mapping[str, object], name: str) -> int:
    value = item.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OpenRouterVideoProviderError(
            f"generation item {name} must be numeric"
        )
    normalized = float(value)
    if normalized <= 0 or not normalized.is_integer():
        raise OpenRouterVideoProviderError(
            f"generation item {name} must be a positive whole number of seconds"
        )
    return int(normalized)


def _string_or_default(value: object, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value
    return default


def _decode_json_object(raw: str) -> Mapping[str, object]:
    if not raw.strip():
        return MappingProxyType({})
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return MappingProxyType({"message": raw.strip()})
    if not isinstance(parsed, dict):
        return MappingProxyType({"message": "OpenRouter response is not a JSON object"})
    return MappingProxyType(cast(dict[str, object], parsed))


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip():
        raise OpenRouterVideoProviderError(f"{name} must not be blank")
