"""Free-only OpenRouter video generation adapters for ILAIOS Video Factory.

This module implements provider-neutral submit, poll, and generated-asset
retrieval against OpenRouter's asynchronous video API. The production safety
policy is intentionally fail-closed: an explicit ``:free`` model ID is only
eligible after authoritative OpenRouter model metadata proves the exact free
variant is zero-priced and the dedicated video catalog proves its base model is
currently video-capable. Terminal provider cost is verified again after
generation before any result can pass.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .generated_asset_retrieval import GeneratedAssetPayload
from .generation_job_polling import ProviderJobObservation, ProviderJobStatus
from .models import MetadataValue, ProviderRequest, ProviderResult
from .providers import ProviderCapabilities

_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
_DEFAULT_OPERATION = "video.generate"
_DEFAULT_PROVIDER_NAME = "openrouter-video-free"
_DEFAULT_RESOLUTION = "480p"
_DEFAULT_SUBMISSION_TIMEOUT_SECONDS = 120.0
_FREE_SUFFIX = ":free"
_VIDEO_CATALOG_PATH = "/videos/models"
SEEDANCE_FREE_MODEL_ID = "bytedance/seedance-2.0-fast:free"


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
    """Injectable HTTP transport for deterministic adapter tests."""

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
    """Standard-library HTTPS transport for OpenRouter video endpoints."""

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        encoded = json.dumps(dict(body), separators=(",", ":")).encode("utf-8")
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
    """Submit one catalog-proven, zero-cost OpenRouter video job."""

    def __init__(
        self,
        api_key: str,
        *,
        provider_name: str = _DEFAULT_PROVIDER_NAME,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = _DEFAULT_SUBMISSION_TIMEOUT_SECONDS,
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
            is_paid=False,
            metadata={
                "backend": "openrouter",
                "modality": "video",
                "cost_policy": "free_only",
            },
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def execute(self, request: ProviderRequest) -> ProviderResult:
        """Submit exactly one async job only after authoritative zero-cost preflight."""

        try:
            self._validate_request(request)
            model_id, item = _parse_single_item_payload(request.payload)
            _require_free_model_id(model_id)
        except OpenRouterVideoProviderError as exc:
            return _failure_result(request, "invalid_request", str(exc))
        except Exception as exc:  # noqa: BLE001
            message = str(exc).strip() or exc.__class__.__name__
            return _failure_result(request, "invalid_request", message)

        try:
            catalog_evidence = self._catalog_zero_cost_evidence(model_id)
        except OpenRouterVideoProviderError as exc:
            code, message = _coded_error(str(exc), "FREE_VIDEO_CATALOG_UNAVAILABLE")
            return _failure_result(request, code, message)
        except Exception as exc:  # noqa: BLE001
            message = str(exc).strip() or exc.__class__.__name__
            return _failure_result(
                request,
                "FREE_VIDEO_CATALOG_UNAVAILABLE",
                f"OpenRouter video catalog preflight failed: {message}",
            )

        try:
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
        except TimeoutError:
            return _failure_result(
                request,
                "submission_timeout_uncertain",
                (
                    "OpenRouter video submission response timed out after "
                    f"{self._timeout_seconds:g}s; provider acceptance is unknown and "
                    "automatic resubmission is forbidden to avoid duplicate generation"
                ),
            )
        except OpenRouterVideoProviderError as exc:
            message = str(exc)
            if "timed out" in message.lower():
                return _failure_result(
                    request,
                    "submission_timeout_uncertain",
                    (
                        "OpenRouter video submission response timed out after "
                        f"{self._timeout_seconds:g}s; provider acceptance is unknown and "
                        "automatic resubmission is forbidden to avoid duplicate generation"
                    ),
                )
            return _failure_result(request, "invalid_request", message)
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
        metadata: dict[str, MetadataValue] = {
            "backend": "openrouter",
            "cost_policy": "free_only",
            "model_id": model_id,
            "submission_status": _string_or_default(
                response.payload.get("status"), "accepted"
            ),
            "catalog_zero_cost": True,
            "catalog_zero_cost_evidence_json": json.dumps(
                dict(catalog_evidence), sort_keys=True, separators=(",", ":")
            ),
            "catalog_zero_cost_evidence_source": str(
                catalog_evidence.get("source", "openrouter_videos_models")
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

    def _catalog_zero_cost_evidence(self, model_id: str) -> Mapping[str, object]:
        """Prove free-variant pricing and current video capability before POST."""

        try:
            response = self._transport.get_json(
                f"{self._base_url}{_VIDEO_CATALOG_PATH}",
                headers=_auth_headers(self._api_key),
                timeout_seconds=self._timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            message = str(exc).strip() or exc.__class__.__name__
            raise OpenRouterVideoProviderError(
                "FREE_VIDEO_CATALOG_UNAVAILABLE: OpenRouter video catalog lookup failed: "
                f"{message}"
            ) from exc
        if not 200 <= response.status_code < 300:
            raise OpenRouterVideoProviderError(
                "FREE_VIDEO_CATALOG_UNAVAILABLE: OpenRouter video catalog returned "
                f"HTTP {response.status_code}"
            )
        data = response.payload.get("data")
        if not isinstance(data, list):
            raise OpenRouterVideoProviderError(
                "FREE_VIDEO_CATALOG_UNAVAILABLE: OpenRouter video catalog did not contain "
                "a data list"
            )

        exact_model: Mapping[str, object] | None = None
        base_model: Mapping[str, object] | None = None
        base_model_id = model_id[: -len(_FREE_SUFFIX)]
        for candidate in data:
            if not isinstance(candidate, Mapping):
                continue
            candidate_id = candidate.get("id")
            if not isinstance(candidate_id, str):
                continue
            if candidate_id == model_id:
                exact_model = cast(Mapping[str, object], candidate)
                break
            if candidate_id == base_model_id:
                base_model = cast(Mapping[str, object], candidate)

        if exact_model is not None:
            pricing = exact_model.get("pricing_skus")
            if not isinstance(pricing, Mapping) or not pricing:
                raise OpenRouterVideoProviderError(
                    "FREE_VIDEO_PRICING_UNKNOWN: exact video model does not expose non-empty "
                    "pricing_skus"
                )
            normalized_pricing: dict[str, object] = {}
            for raw_name, raw_price in pricing.items():
                sku_name = str(raw_name)
                price = _decimal_cost(raw_price)
                if price is None:
                    raise OpenRouterVideoProviderError(
                        "FREE_VIDEO_PRICING_UNKNOWN: video catalog pricing_skus contains a "
                        f"non-numeric or invalid price for {sku_name}"
                    )
                normalized_pricing[sku_name] = _format_decimal(price)
                if price != Decimal("0"):
                    raise OpenRouterVideoProviderError(
                        "FREE_VIDEO_PRICING_NONZERO: authoritative video catalog price for "
                        f"{model_id} / {sku_name} is {_format_decimal(price)} USD"
                    )
            return MappingProxyType(
                {
                    "source": "openrouter_videos_models",
                    "model_id": model_id,
                    "catalog_zero_cost": True,
                    "pricing_skus": normalized_pricing,
                }
            )

        if base_model is None:
            raise OpenRouterVideoProviderError(
                "FREE_VIDEO_MODEL_UNAVAILABLE: neither the requested free variant nor its "
                "base model is present in the authoritative /videos/models catalog: "
                f"{model_id}"
            )

        variant_evidence = self._free_variant_zero_cost_evidence(model_id)
        return MappingProxyType(
            {
                "source": "openrouter_model_variant+videos_models",
                "model_id": model_id,
                "video_catalog_model_id": base_model_id,
                "catalog_zero_cost": True,
                "variant_pricing": variant_evidence["pricing"],
            }
        )

    def _free_variant_zero_cost_evidence(self, model_id: str) -> Mapping[str, object]:
        """Prove the exact ``:free`` variant exists and is zero-priced."""

        try:
            author, slug = model_id.split("/", 1)
        except ValueError as exc:
            raise OpenRouterVideoProviderError(
                "FREE_VIDEO_MODEL_UNAVAILABLE: free model id must contain author/slug"
            ) from exc
        url = (
            f"{self._base_url}/model/{quote(author, safe='')}/"
            f"{quote(slug, safe='')}"
        )
        try:
            response = self._transport.get_json(
                url,
                headers=_auth_headers(self._api_key),
                timeout_seconds=self._timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            message = str(exc).strip() or exc.__class__.__name__
            raise OpenRouterVideoProviderError(
                "FREE_VIDEO_VARIANT_UNAVAILABLE: OpenRouter model-variant lookup failed: "
                f"{message}"
            ) from exc
        if not 200 <= response.status_code < 300:
            raise OpenRouterVideoProviderError(
                "FREE_VIDEO_VARIANT_UNAVAILABLE: OpenRouter exact free-variant lookup "
                f"returned HTTP {response.status_code}: {model_id}"
            )
        data = response.payload.get("data")
        if not isinstance(data, Mapping):
            raise OpenRouterVideoProviderError(
                "FREE_VIDEO_VARIANT_UNAVAILABLE: exact free-variant lookup did not contain "
                "a data object"
            )
        returned_id = data.get("id")
        if returned_id != model_id:
            raise OpenRouterVideoProviderError(
                "FREE_VIDEO_VARIANT_UNAVAILABLE: model lookup did not resolve to the exact "
                f"requested free variant: {model_id}"
            )
        pricing = data.get("pricing")
        if not isinstance(pricing, Mapping) or not pricing:
            raise OpenRouterVideoProviderError(
                "FREE_VIDEO_PRICING_UNKNOWN: exact free variant does not expose non-empty "
                "pricing metadata"
            )
        normalized_pricing: dict[str, object] = {}
        for raw_name, raw_price in pricing.items():
            sku_name = str(raw_name)
            price = _decimal_cost(raw_price)
            if price is None:
                raise OpenRouterVideoProviderError(
                    "FREE_VIDEO_PRICING_UNKNOWN: free-variant pricing contains a "
                    f"non-numeric or invalid price for {sku_name}"
                )
            normalized_pricing[sku_name] = _format_decimal(price)
            if price != Decimal("0"):
                raise OpenRouterVideoProviderError(
                    "FREE_VIDEO_PRICING_NONZERO: authoritative free-variant price for "
                    f"{model_id} / {sku_name} is {_format_decimal(price)} USD"
                )
        return MappingProxyType(
            {
                "source": "openrouter_model_variant",
                "model_id": model_id,
                "pricing": normalized_pricing,
            }
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
    """Normalize OpenRouter video jobs and prove terminal provider cost."""

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
        self._terminal_evidence: dict[str, Mapping[str, object]] = {}

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def terminal_evidence(self) -> Mapping[str, Mapping[str, object]]:
        """Return sanitized authoritative terminal cost evidence by provider job id."""

        return MappingProxyType(dict(self._terminal_evidence))

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
        observation = _normalize_poll_observation(
            self._provider_id,
            provider_job_id,
            self._base_url,
            response.payload,
        )
        if observation.status is not ProviderJobStatus.SUCCEEDED:
            return observation

        evidence = self._resolve_terminal_zero_cost_evidence(response.payload)
        cost = _decimal_cost(evidence.get("cost"))
        if cost is None:
            raise OpenRouterVideoProviderError(
                "ZERO_COST_EVIDENCE_UNKNOWN: authoritative terminal cost is malformed"
            )
        if cost != Decimal("0"):
            raise OpenRouterVideoProviderError(
                f"PROVIDER_COST_NONZERO: authoritative OpenRouter charge was {cost} USD"
            )

        self._terminal_evidence[provider_job_id] = evidence
        metadata = dict(observation.metadata)
        terminal_usage = response.payload.get("usage")
        usage_payload = dict(terminal_usage) if isinstance(terminal_usage, Mapping) else {}
        if _decimal_cost(usage_payload.get("cost")) is None:
            usage_payload["cost"] = float(cost)
        metadata["usage_json"] = json.dumps(
            usage_payload, sort_keys=True, separators=(",", ":")
        )
        metadata["provider_cost_evidence_json"] = json.dumps(
            dict(evidence), sort_keys=True, separators=(",", ":")
        )
        metadata["zero_cost_evidence_source"] = str(evidence["source"])
        generation_id = evidence.get("generation_id")
        if isinstance(generation_id, str) and generation_id.strip():
            metadata["generation_id"] = generation_id
        metadata["terminal_response_json"] = json.dumps(
            evidence["terminal_response"], sort_keys=True, separators=(",", ":")
        )
        accounting_response = evidence.get("generation_accounting_response")
        if isinstance(accounting_response, Mapping):
            metadata["generation_accounting_response_json"] = json.dumps(
                dict(accounting_response), sort_keys=True, separators=(",", ":")
            )
        return ProviderJobObservation(
            provider_id=observation.provider_id,
            provider_job_id=observation.provider_job_id,
            status=observation.status,
            output_asset_ids=observation.output_asset_ids,
            metadata=metadata,
        )

    def _resolve_terminal_zero_cost_evidence(
        self,
        video_payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        sanitized_terminal = _sanitize_payload(video_payload)
        generation_id = video_payload.get("generation_id")
        normalized_generation_id = (
            generation_id.strip()
            if isinstance(generation_id, str) and generation_id.strip()
            else None
        )

        usage = video_payload.get("usage")
        if isinstance(usage, Mapping) and "cost" in usage:
            cost = _decimal_cost(usage.get("cost"))
            if cost is not None:
                return MappingProxyType(
                    {
                        "cost": float(cost),
                        "source": "openrouter_video_poll_usage",
                        "generation_id": normalized_generation_id or "unavailable",
                        "terminal_response": sanitized_terminal,
                    }
                )

        if normalized_generation_id is None:
            if isinstance(usage, Mapping):
                raise OpenRouterVideoProviderError(
                    "ZERO_COST_EVIDENCE_UNKNOWN: terminal usage did not contain a valid cost "
                    "and no generation_id was available for accounting recovery"
                )
            raise OpenRouterVideoProviderError(
                "ZERO_COST_EVIDENCE_MISSING: completed OpenRouter video response contained "
                "neither authoritative usage.cost nor a generation_id"
            )

        encoded_generation_id = quote(normalized_generation_id, safe="")
        response = self._transport.get_json(
            f"{self._base_url}/generation?id={encoded_generation_id}",
            headers=_auth_headers(self._api_key),
            timeout_seconds=self._timeout_seconds,
        )
        sanitized_accounting = _sanitize_payload(response.payload)
        if not 200 <= response.status_code < 300:
            raise OpenRouterVideoProviderError(
                "PROVIDER_USAGE_UNAVAILABLE: OpenRouter generation accounting lookup "
                f"returned HTTP {response.status_code}"
            )
        data = response.payload.get("data")
        if not isinstance(data, Mapping):
            raise OpenRouterVideoProviderError(
                "ZERO_COST_EVIDENCE_UNKNOWN: OpenRouter generation accounting response "
                "did not contain a data object"
            )
        raw_cost = data.get("total_cost")
        if raw_cost is None:
            raw_cost = data.get("usage")
        cost = _decimal_cost(raw_cost)
        if cost is None:
            raise OpenRouterVideoProviderError(
                "ZERO_COST_EVIDENCE_UNKNOWN: OpenRouter generation accounting response "
                "did not contain a valid numeric total_cost/usage"
            )
        return MappingProxyType(
            {
                "cost": float(cost),
                "source": "openrouter_generation_metadata",
                "generation_id": normalized_generation_id,
                "terminal_response": sanitized_terminal,
                "generation_accounting_response": sanitized_accounting,
            }
        )


class OpenRouterGeneratedAssetRetriever:
    """Download video bytes from OpenRouter's authenticated content endpoint."""

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


def _require_free_model_id(model_id: str) -> None:
    """Reject paid/non-explicitly-free model IDs before any provider call."""

    if not model_id.endswith(_FREE_SUFFIX):
        raise OpenRouterVideoProviderError(
            "OpenRouter Video Factory policy requires an explicit :free model; "
            "paid or unpriced model IDs are forbidden"
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
    if item.get("output_count") != 1:
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
        "in_progress": ProviderJobStatus.RUNNING,
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
        content_url = f"{base_url}/videos/{quote(provider_job_id, safe='')}/content"
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


def _decimal_cost(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if not isinstance(value, (int, float, str)):
        return None
    try:
        cost = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not cost.is_finite() or cost < Decimal("0"):
        return None
    return cost


def _format_decimal(value: Decimal) -> str:
    normalized = format(value, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def _sanitize_payload(value: object) -> object:
    if isinstance(value, Mapping):
        sanitized: dict[str, object] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            if _sensitive_key(key):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = _sanitize_payload(raw_value)
        return sanitized
    if isinstance(value, (list, tuple)):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(
        marker in normalized
        for marker in (
            "authorization",
            "api_key",
            "apikey",
            "access_token",
            "refresh_token",
            "secret",
            "password",
        )
    )


def _coded_error(message: str, default_code: str) -> tuple[str, str]:
    code, separator, detail = message.partition(":")
    if separator and code and code.replace("_", "").isalnum() and code.upper() == code:
        return code, detail.strip() or message
    return default_code, message


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
        metadata={"backend": "openrouter", "cost_policy": "free_only"},
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