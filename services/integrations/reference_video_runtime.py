"""Reference-image aware provider boundary for Desktop Video Factory."""

from __future__ import annotations

import json
from types import MappingProxyType
from typing import Mapping

from services.reference_assets import (
    current_reference_request_id,
    get_reference_asset_store,
    reference_request_context,
)
from src.video_automation import openrouter_video_provider as _openrouter
from src.video_automation.models import MetadataValue, ProviderRequest, ProviderResult
from src.video_automation.openrouter_video_provider import (
    OpenRouterVideoGenerationProvider,
    OpenRouterVideoProviderError,
)

from .provider_video_runtime import ProviderBackedDesktopVideoRuntime


class ReferenceAwareOpenRouterVideoGenerationProvider(OpenRouterVideoGenerationProvider):
    """Submit governed local references as OpenRouter input_references."""

    def execute(self, request: ProviderRequest) -> ProviderResult:
        try:
            self._validate_request(request)
            model_id, item = _openrouter._parse_single_item_payload(request.payload)
            _openrouter._require_free_model_id(model_id)
        except OpenRouterVideoProviderError as exc:
            return _openrouter._failure_result(request, "invalid_request", str(exc))
        except Exception as exc:  # noqa: BLE001
            message = str(exc).strip() or exc.__class__.__name__
            return _openrouter._failure_result(request, "invalid_request", message)

        try:
            catalog_evidence = self._catalog_zero_cost_evidence(model_id)
        except OpenRouterVideoProviderError as exc:
            code, message = _openrouter._coded_error(
                str(exc), "FREE_VIDEO_CATALOG_UNAVAILABLE"
            )
            return _openrouter._failure_result(request, code, message)
        except Exception as exc:  # noqa: BLE001
            message = str(exc).strip() or exc.__class__.__name__
            return _openrouter._failure_result(
                request,
                "FREE_VIDEO_CATALOG_UNAVAILABLE",
                f"OpenRouter video catalog preflight failed: {message}",
            )

        try:
            body = _build_reference_request_body(
                model_id,
                item,
                default_resolution=self._default_resolution,
                generate_audio=self._generate_audio,
            )
            if body.get("input_references"):
                self._prove_reference_support(model_id)
            response = self._transport.post_json(
                f"{self._base_url}/videos",
                headers=_openrouter._auth_headers(self._api_key, json_content=True),
                body=body,
                timeout_seconds=self._timeout_seconds,
            )
        except TimeoutError:
            return _openrouter._failure_result(
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
                return _openrouter._failure_result(
                    request,
                    "submission_timeout_uncertain",
                    (
                        "OpenRouter video submission response timed out after "
                        f"{self._timeout_seconds:g}s; provider acceptance is unknown and "
                        "automatic resubmission is forbidden to avoid duplicate generation"
                    ),
                )
            return _openrouter._failure_result(request, "invalid_request", message)
        except Exception as exc:  # noqa: BLE001
            message = str(exc).strip() or exc.__class__.__name__
            return _openrouter._failure_result(request, "transport_error", message)

        if not 200 <= response.status_code < 300:
            code, message = _openrouter._normalize_error(response)
            return _openrouter._failure_result(request, code, message)

        provider_job_id = response.payload.get("id")
        if not isinstance(provider_job_id, str) or not provider_job_id.strip():
            return _openrouter._failure_result(
                request,
                "invalid_provider_response",
                "OpenRouter response does not contain a non-empty video job id",
            )
        metadata: dict[str, MetadataValue] = {
            "backend": "openrouter",
            "cost_policy": "free_only",
            "model_id": model_id,
            "submission_status": _openrouter._string_or_default(
                response.payload.get("status"), "accepted"
            ),
            "catalog_zero_cost": True,
            "catalog_zero_cost_evidence_json": json.dumps(
                dict(catalog_evidence), sort_keys=True, separators=(",", ":")
            ),
            "catalog_zero_cost_evidence_source": "openrouter_videos_models",
        }
        reference_count = len(body.get("input_references", ()))
        if reference_count:
            metadata["reference_asset_count"] = reference_count
            metadata["reference_mode"] = "input_references"
        generation_id = response.payload.get("generation_id")
        if isinstance(generation_id, str) and generation_id.strip():
            metadata["generation_id"] = generation_id
        return ProviderResult(
            request_id=request.request_id,
            provider_name=request.provider_name,
            success=True,
            external_id=provider_job_id,
            metadata=metadata,
        )

    def _prove_reference_support(self, model_id: str) -> None:
        response = self._transport.get_json(
            f"{self._base_url}/videos/models",
            headers=_openrouter._auth_headers(self._api_key),
            timeout_seconds=self._timeout_seconds,
        )
        if not 200 <= response.status_code < 300:
            raise OpenRouterVideoProviderError(
                "REFERENCE_VIDEO_CAPABILITY_UNAVAILABLE: video catalog lookup failed"
            )
        data = response.payload.get("data")
        if not isinstance(data, list):
            raise OpenRouterVideoProviderError(
                "REFERENCE_VIDEO_CAPABILITY_UNAVAILABLE: video catalog is malformed"
            )
        for candidate in data:
            if not isinstance(candidate, Mapping) or candidate.get("id") != model_id:
                continue
            description = candidate.get("description")
            if isinstance(description, str) and "reference" in description.lower():
                return
            raise OpenRouterVideoProviderError(
                "REFERENCE_VIDEO_CAPABILITY_UNPROVEN: selected model description does "
                "not prove reference-to-video support"
            )
        raise OpenRouterVideoProviderError(
            "REFERENCE_VIDEO_CAPABILITY_UNAVAILABLE: selected model is absent from "
            "the authoritative video catalog"
        )


class ReferenceAwareProviderBackedDesktopVideoRuntime(ProviderBackedDesktopVideoRuntime):
    """Keep one request-scoped reference context across all generated shots."""

    def __init__(self, *args: object, api_key: str, provider=None, **kwargs: object) -> None:
        if provider is None:
            resolution = str(kwargs.get("resolution", "720p"))
            provider = ReferenceAwareOpenRouterVideoGenerationProvider(
                api_key,
                provider_name=self.PROVIDER_ID,
                default_resolution=resolution,
                generate_audio=True,
            )
        super().__init__(*args, api_key=api_key, provider=provider, **kwargs)

    def execute(
        self,
        *,
        request_id: str,
        job_id: str,
        grant_id: str,
        now,
    ) -> dict[str, object]:
        with reference_request_context(request_id):
            result = dict(
                super().execute(
                    request_id=request_id,
                    job_id=job_id,
                    grant_id=grant_id,
                    now=now,
                )
            )
        references = get_reference_asset_store().for_request(request_id)
        if references:
            result["reference_assets"] = [item.public_metadata() for item in references]
            result["reference_asset_usage"] = "openrouter-input-references"
            qa = result.get("qa")
            if isinstance(qa, dict):
                qa = dict(qa)
                qa["reference_asset_count"] = len(references)
                qa["reference_assets_consumed"] = True
                result["qa"] = qa
        return result


def _build_reference_request_body(
    model_id: str,
    item: Mapping[str, object],
    *,
    default_resolution: str,
    generate_audio: bool,
) -> Mapping[str, object]:
    body = dict(
        _openrouter._build_openrouter_request_body(
            model_id,
            item,
            default_resolution=default_resolution,
            generate_audio=generate_audio,
        )
    )
    request_id = current_reference_request_id()
    if request_id is None:
        return MappingProxyType(body)
    references = get_reference_asset_store().for_request(request_id)
    if not references:
        return MappingProxyType(body)
    body["input_references"] = [
        {
            "type": "image_url",
            "image_url": {"url": get_reference_asset_store().data_url(record)},
        }
        for record in references
    ]
    return MappingProxyType(body)
