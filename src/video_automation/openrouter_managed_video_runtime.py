"""Runtime polling and cost evidence for ILAIOS-managed OpenRouter video jobs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from urllib.parse import quote

from .generation_job_polling import ProviderJobObservation, ProviderJobStatus
from .managed_credits import ManagedCreditError, usd_to_microusd
from .openrouter_managed_video_provider import OPENROUTER_MANAGED_PROVIDER_NAME
from .openrouter_video_provider import (
    OpenRouterTransport,
    UrllibOpenRouterTransport,
)

_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
_TERMINAL_PROVIDER_STATUSES = frozenset(
    {"completed", "succeeded", "failed", "cancelled", "canceled"}
)


class OpenRouterManagedVideoRuntimeError(ValueError):
    """Raised when managed provider runtime evidence is invalid."""


class OpenRouterManagedVideoGenerationJobPoller:
    """Poll an ILAIOS-managed OpenRouter video job without exposing credentials."""

    def __init__(
        self,
        api_key: str,
        *,
        provider_id: str = OPENROUTER_MANAGED_PROVIDER_NAME,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 30.0,
        transport: OpenRouterTransport | None = None,
    ) -> None:
        _require_text("api_key", api_key)
        _require_text("provider_id", provider_id)
        _require_text("base_url", base_url)
        if timeout_seconds <= 0:
            raise OpenRouterManagedVideoRuntimeError(
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
        _require_text("provider_job_id", provider_job_id)
        encoded_id = quote(provider_job_id, safe="")
        response = self._transport.get_json(
            f"{self._base_url}/videos/{encoded_id}",
            headers=_auth_headers(self._api_key),
            timeout_seconds=self._timeout_seconds,
        )
        if not 200 <= response.status_code < 300:
            raise OpenRouterManagedVideoRuntimeError(
                f"OpenRouter poll failed with HTTP status {response.status_code}"
            )
        payload, usage_source = self._with_terminal_cost_evidence(response.payload)
        return _normalize_observation(
            provider_id=self._provider_id,
            provider_job_id=provider_job_id,
            base_url=self._base_url,
            payload=payload,
            usage_source=usage_source,
        )

    def _with_terminal_cost_evidence(
        self,
        payload: Mapping[str, object],
    ) -> tuple[Mapping[str, object], str | None]:
        """Recover provider-reported cost from generation metadata when needed."""
        usage = payload.get("usage")
        if isinstance(usage, Mapping):
            return payload, "video-poll"

        raw_status = payload.get("status")
        if not isinstance(raw_status, str):
            return payload, None
        if raw_status.strip().lower() not in _TERMINAL_PROVIDER_STATUSES:
            return payload, None

        generation_id = payload.get("generation_id")
        if not isinstance(generation_id, str) or not generation_id.strip():
            return payload, None

        metadata_response = self._transport.get_json(
            f"{self._base_url}/generation?id={quote(generation_id, safe='')}",
            headers=_auth_headers(self._api_key),
            timeout_seconds=self._timeout_seconds,
        )
        if not 200 <= metadata_response.status_code < 300:
            return payload, None
        data = metadata_response.payload.get("data")
        if not isinstance(data, Mapping):
            return payload, None
        total_cost = data.get("total_cost")
        if isinstance(total_cost, bool) or not isinstance(total_cost, (int, float, str)):
            return payload, None
        try:
            decimal_cost = Decimal(str(total_cost))
            usd_to_microusd(decimal_cost)
        except (InvalidOperation, ManagedCreditError):
            return payload, None

        enriched = dict(payload)
        enriched["usage"] = {"cost": total_cost}
        return MappingProxyType(enriched), "generation-metadata"


def actual_cost_microusd_from_observation(
    observation: ProviderJobObservation,
) -> int:
    """Extract provider-reported actual USD cost as integer micro-USD."""
    if observation.status not in {
        ProviderJobStatus.SUCCEEDED,
        ProviderJobStatus.FAILED,
        ProviderJobStatus.CANCELLED,
    }:
        raise OpenRouterManagedVideoRuntimeError(
            "provider cost cannot be settled before terminal job status"
        )
    usage_json = observation.metadata.get("usage_json")
    if not isinstance(usage_json, str) or not usage_json.strip():
        raise OpenRouterManagedVideoRuntimeError(
            "terminal provider observation is missing usage cost evidence"
        )
    try:
        usage = json.loads(usage_json)
    except json.JSONDecodeError as exc:
        raise OpenRouterManagedVideoRuntimeError(
            "provider usage evidence is not valid JSON"
        ) from exc
    if not isinstance(usage, dict):
        raise OpenRouterManagedVideoRuntimeError(
            "provider usage evidence must be a JSON object"
        )
    cost = usage.get("cost")
    if isinstance(cost, bool) or not isinstance(cost, (int, float, str)):
        raise OpenRouterManagedVideoRuntimeError(
            "provider usage evidence is missing numeric cost"
        )
    try:
        decimal_cost = Decimal(str(cost))
        return usd_to_microusd(decimal_cost)
    except (InvalidOperation, ManagedCreditError) as exc:
        raise OpenRouterManagedVideoRuntimeError(
            "provider usage cost is invalid"
        ) from exc


def _normalize_observation(
    *,
    provider_id: str,
    provider_job_id: str,
    base_url: str,
    payload: Mapping[str, object],
    usage_source: str | None = None,
) -> ProviderJobObservation:
    raw_status = payload.get("status")
    if not isinstance(raw_status, str) or not raw_status.strip():
        raise OpenRouterManagedVideoRuntimeError(
            "OpenRouter video poll response requires string status"
        )
    normalized = raw_status.strip().lower()
    status_map = {
        "pending": ProviderJobStatus.QUEUED,
        "queued": ProviderJobStatus.QUEUED,
        "in_progress": ProviderJobStatus.RUNNING,
        "processing": ProviderJobStatus.RUNNING,
        "running": ProviderJobStatus.RUNNING,
        "completed": ProviderJobStatus.SUCCEEDED,
        "succeeded": ProviderJobStatus.SUCCEEDED,
        "failed": ProviderJobStatus.FAILED,
        "cancelled": ProviderJobStatus.CANCELLED,
        "canceled": ProviderJobStatus.CANCELLED,
    }
    status = status_map.get(normalized)
    if status is None:
        raise OpenRouterManagedVideoRuntimeError(
            f"unsupported OpenRouter video job status: {raw_status}"
        )

    metadata: dict[str, str] = {"provider_status": normalized}
    generation_id = payload.get("generation_id")
    if isinstance(generation_id, str) and generation_id.strip():
        metadata["generation_id"] = generation_id
    usage = payload.get("usage")
    if isinstance(usage, Mapping):
        metadata["usage_json"] = json.dumps(
            dict(usage), sort_keys=True, separators=(",", ":")
        )
        if usage_source is not None:
            metadata["usage_evidence_source"] = usage_source

    if status is ProviderJobStatus.SUCCEEDED:
        return ProviderJobObservation(
            provider_id=provider_id,
            provider_job_id=provider_job_id,
            status=status,
            output_asset_ids=(
                f"{base_url}/videos/{quote(provider_job_id, safe='')}/content",
            ),
            metadata=metadata,
        )

    error_code: str | None = None
    error_message: str | None = None
    if status is ProviderJobStatus.FAILED:
        error = payload.get("error")
        error_code = "provider_failed"
        if isinstance(error, str) and error.strip():
            error_message = error
        elif isinstance(error, Mapping):
            raw_code = error.get("code")
            raw_message = error.get("message")
            if raw_code is not None:
                error_code = str(raw_code)
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


def _auth_headers(api_key: str) -> Mapping[str, str]:
    return MappingProxyType({"Authorization": f"Bearer {api_key}"})


def _require_text(name: str, value: str) -> None:
    if not value or not value.strip():
        raise OpenRouterManagedVideoRuntimeError(f"{name} must not be blank")
