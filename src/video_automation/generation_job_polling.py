"""Provider-independent generation job polling and status normalization.

This module polls already-submitted generation jobs through provider-specific
poller adapters and converts explicit provider observations into existing
GenerationExecutionUpdate contracts. The core polling coordinator is provider
independent: Seedance Ark is only the first concrete poller implementation.

The module does not submit generation work, select providers, retry jobs,
download media, inspect media, or mutate execution state.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .generation_dispatch_planning import EpisodeGenerationDispatchPlan
from .generation_execution_tracking import (
    EpisodeGenerationExecutionState,
    GenerationExecutionStatus,
    GenerationExecutionUpdate,
)


class GenerationJobPollingError(ValueError):
    """Raised when a generation job cannot be polled deterministically."""


class ProviderJobStatus(StrEnum):
    """Provider-neutral status reported by one provider poller."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class ProviderJobObservation:
    """Immutable provider-neutral observation for one submitted provider job."""

    provider_id: str
    provider_job_id: str
    status: ProviderJobStatus
    output_asset_ids: tuple[str, ...] = ()
    error_code: str | None = None
    error_message: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_blank("provider_id", self.provider_id)
        _require_non_blank("provider_job_id", self.provider_job_id)
        _validate_unique_non_blank_values("output_asset_ids", self.output_asset_ids)
        _validate_optional_non_blank("error_code", self.error_code)
        _validate_optional_non_blank("error_message", self.error_message)
        if self.status is ProviderJobStatus.SUCCEEDED:
            if not self.output_asset_ids:
                raise GenerationJobPollingError(
                    "succeeded observation requires output_asset_ids"
                )
            if self.error_code is not None or self.error_message is not None:
                raise GenerationJobPollingError(
                    "succeeded observation must not contain error details"
                )
        elif self.status is ProviderJobStatus.FAILED:
            if self.error_code is None:
                raise GenerationJobPollingError(
                    "failed observation requires error_code"
                )
            if self.output_asset_ids:
                raise GenerationJobPollingError(
                    "failed observation must not contain output_asset_ids"
                )
        elif self.output_asset_ids:
            raise GenerationJobPollingError(
                "output_asset_ids are allowed only for succeeded observations"
            )
        elif self.error_code is not None or self.error_message is not None:
            raise GenerationJobPollingError(
                "error details are allowed only for failed observations"
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


class GenerationJobPoller(Protocol):
    """Provider-specific adapter contract for one asynchronous generation job."""

    @property
    def provider_id(self) -> str:
        """Return the canonical provider identifier handled by this poller."""

    def poll(self, provider_job_id: str) -> ProviderJobObservation:
        """Return one explicit provider-neutral observation for a provider job."""


class GenerationJobPollerRegistry:
    """Deterministic registry for provider-specific generation job pollers."""

    def __init__(self, pollers: tuple[GenerationJobPoller, ...] = ()) -> None:
        self._pollers: dict[str, GenerationJobPoller] = {}
        for poller in pollers:
            self.register(poller)

    def register(self, poller: GenerationJobPoller) -> None:
        provider_id = poller.provider_id
        _require_non_blank("provider_id", provider_id)
        if provider_id in self._pollers:
            raise GenerationJobPollingError(
                f"poller already registered for provider: {provider_id}"
            )
        self._pollers[provider_id] = poller

    def get(self, provider_id: str) -> GenerationJobPoller:
        _require_non_blank("provider_id", provider_id)
        try:
            return self._pollers[provider_id]
        except KeyError as exc:
            raise GenerationJobPollingError(
                f"poller not registered for provider: {provider_id}"
            ) from exc

    def list_provider_ids(self) -> tuple[str, ...]:
        """Return registered provider ids in deterministic order."""

        return tuple(sorted(self._pollers))


class GenerationJobPollingCoordinator:
    """Poll active dispatch jobs without mutating execution state."""

    def __init__(self, registry: GenerationJobPollerRegistry) -> None:
        self._registry = registry

    def poll(
        self,
        dispatch_plan: EpisodeGenerationDispatchPlan,
        execution_state: EpisodeGenerationExecutionState,
    ) -> tuple[GenerationExecutionUpdate, ...]:
        """Return explicit execution updates for changed provider job states."""

        _validate_state_matches_plan(dispatch_plan, execution_state)
        dispatch_by_id = {
            dispatch.dispatch_id: dispatch for dispatch in dispatch_plan.dispatches
        }
        updates: list[GenerationExecutionUpdate] = []
        for record in execution_state.records:
            if record.status in {
                GenerationExecutionStatus.PENDING,
                GenerationExecutionStatus.SUCCEEDED,
                GenerationExecutionStatus.FAILED,
                GenerationExecutionStatus.CANCELLED,
            }:
                continue
            if record.provider_job_id is None:
                raise GenerationJobPollingError(
                    "active execution record requires provider_job_id"
                )
            dispatch = dispatch_by_id[record.dispatch_id]
            poller = self._registry.get(dispatch.provider_id)
            observation = poller.poll(record.provider_job_id)
            _validate_observation_identity(
                dispatch.provider_id,
                record.provider_job_id,
                observation,
            )
            update = _observation_to_update(record.status, record.dispatch_id, observation)
            if update is not None:
                updates.append(update)
        return tuple(updates)


@dataclass(frozen=True, slots=True)
class ArkTaskJsonResponse:
    """Minimal immutable JSON response for Ark task-status queries."""

    status_code: int
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.status_code <= 0:
            raise GenerationJobPollingError("status_code must be greater than zero")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


class ArkTaskJsonTransport(Protocol):
    """Injectable GET transport for deterministic Ark polling tests."""

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> ArkTaskJsonResponse:
        """GET one Ark JSON resource."""


class UrllibArkTaskJsonTransport:
    """Standard-library HTTPS transport for Ark task polling."""

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> ArkTaskJsonResponse:
        request = Request(url, headers=dict(headers), method="GET")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                status = int(response.status)
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            return ArkTaskJsonResponse(int(exc.code), _decode_json_object(raw))
        except URLError as exc:
            raise GenerationJobPollingError(
                f"Ark polling transport error: {exc.reason}"
            ) from exc
        return ArkTaskJsonResponse(status, _decode_json_object(raw))


class SeedanceArkGenerationJobPoller:
    """Normalize Volcengine Ark Seedance task status into the generic poll contract."""

    def __init__(
        self,
        api_key: str,
        *,
        provider_id: str = "volcengine-seedance",
        base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
        timeout_seconds: float = 30.0,
        transport: ArkTaskJsonTransport | None = None,
    ) -> None:
        _require_non_blank("api_key", api_key)
        _require_non_blank("provider_id", provider_id)
        _require_non_blank("base_url", base_url)
        if timeout_seconds <= 0:
            raise GenerationJobPollingError(
                "timeout_seconds must be greater than zero"
            )
        self._api_key = api_key
        self._provider_id = provider_id
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._transport = transport or UrllibArkTaskJsonTransport()

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def poll(self, provider_job_id: str) -> ProviderJobObservation:
        _require_non_blank("provider_job_id", provider_job_id)
        response = self._transport.get_json(
            f"{self._base_url}/contents/generations/tasks/{quote(provider_job_id, safe='')}",
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout_seconds=self._timeout_seconds,
        )
        if not 200 <= response.status_code < 300:
            code, message = _normalize_ark_error(response)
            raise GenerationJobPollingError(f"{code}: {message}")
        return _normalize_seedance_observation(
            self._provider_id,
            provider_job_id,
            response.payload,
        )


def _normalize_seedance_observation(
    provider_id: str,
    provider_job_id: str,
    payload: Mapping[str, object],
) -> ProviderJobObservation:
    status_value = payload.get("status")
    if not isinstance(status_value, str):
        raise GenerationJobPollingError("Ark task response requires string status")
    try:
        status = ProviderJobStatus(status_value)
    except ValueError as exc:
        raise GenerationJobPollingError(
            f"unsupported Ark task status: {status_value}"
        ) from exc

    if status is ProviderJobStatus.SUCCEEDED:
        content = payload.get("content")
        if not isinstance(content, Mapping):
            raise GenerationJobPollingError(
                "succeeded Ark task requires content object"
            )
        video_url = content.get("video_url")
        if not isinstance(video_url, str) or not video_url.strip():
            raise GenerationJobPollingError(
                "succeeded Ark task requires non-empty content.video_url"
            )
        metadata = {"provider_status": status.value}
        last_frame_url = content.get("last_frame_url")
        if isinstance(last_frame_url, str) and last_frame_url.strip():
            metadata["last_frame_url"] = last_frame_url
        return ProviderJobObservation(
            provider_id=provider_id,
            provider_job_id=provider_job_id,
            status=status,
            output_asset_ids=(video_url,),
            metadata=metadata,
        )

    if status is ProviderJobStatus.FAILED:
        error = payload.get("error")
        code = "provider_failed"
        message: str | None = None
        if isinstance(error, Mapping):
            raw_code = error.get("code")
            raw_message = error.get("message")
            if isinstance(raw_code, str) and raw_code.strip():
                code = raw_code
            if isinstance(raw_message, str) and raw_message.strip():
                message = raw_message
        return ProviderJobObservation(
            provider_id=provider_id,
            provider_job_id=provider_job_id,
            status=status,
            error_code=code,
            error_message=message,
            metadata={"provider_status": status.value},
        )

    return ProviderJobObservation(
        provider_id=provider_id,
        provider_job_id=provider_job_id,
        status=status,
        metadata={"provider_status": status.value},
    )


def _observation_to_update(
    current_status: GenerationExecutionStatus,
    dispatch_id: str,
    observation: ProviderJobObservation,
) -> GenerationExecutionUpdate | None:
    target = {
        ProviderJobStatus.QUEUED: GenerationExecutionStatus.SUBMITTED,
        ProviderJobStatus.RUNNING: GenerationExecutionStatus.RUNNING,
        ProviderJobStatus.SUCCEEDED: GenerationExecutionStatus.SUCCEEDED,
        ProviderJobStatus.FAILED: GenerationExecutionStatus.FAILED,
        ProviderJobStatus.CANCELLED: GenerationExecutionStatus.CANCELLED,
    }[observation.status]
    if target is current_status:
        return None
    if (
        current_status is GenerationExecutionStatus.RUNNING
        and target is GenerationExecutionStatus.SUBMITTED
    ):
        raise GenerationJobPollingError(
            "provider observation would regress running execution to submitted"
        )
    return GenerationExecutionUpdate(
        dispatch_id=dispatch_id,
        status=target,
        provider_job_id=(
            observation.provider_job_id
            if target
            in {
                GenerationExecutionStatus.SUBMITTED,
                GenerationExecutionStatus.RUNNING,
                GenerationExecutionStatus.SUCCEEDED,
            }
            else None
        ),
        output_asset_ids=observation.output_asset_ids,
        error_code=observation.error_code,
        error_message=observation.error_message,
        metadata=observation.metadata,
    )


def _validate_state_matches_plan(
    dispatch_plan: EpisodeGenerationDispatchPlan,
    execution_state: EpisodeGenerationExecutionState,
) -> None:
    if execution_state.dispatch_plan_id != dispatch_plan.dispatch_plan_id:
        raise GenerationJobPollingError(
            "execution state does not belong to dispatch plan"
        )
    expected = tuple(dispatch.dispatch_id for dispatch in dispatch_plan.dispatches)
    actual = tuple(record.dispatch_id for record in execution_state.records)
    if actual != expected:
        raise GenerationJobPollingError(
            "execution records must match dispatch plan order"
        )


def _validate_observation_identity(
    provider_id: str,
    provider_job_id: str,
    observation: ProviderJobObservation,
) -> None:
    if observation.provider_id != provider_id:
        raise GenerationJobPollingError(
            "poll observation provider_id does not match dispatch provider"
        )
    if observation.provider_job_id != provider_job_id:
        raise GenerationJobPollingError(
            "poll observation provider_job_id does not match execution record"
        )


def _normalize_ark_error(response: ArkTaskJsonResponse) -> tuple[str, str]:
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
        f"Ark polling request failed with HTTP status {response.status_code}",
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


def _freeze_metadata(metadata: Mapping[str, str]) -> Mapping[str, str]:
    normalized = dict(metadata)
    for key, value in normalized.items():
        _require_non_blank("metadata key", key)
        _require_non_blank(f"metadata value for {key}", value)
    return MappingProxyType(normalized)


def _validate_unique_non_blank_values(name: str, values: tuple[str, ...]) -> None:
    for value in values:
        _require_non_blank(name, value)
    if len(values) != len(set(values)):
        raise GenerationJobPollingError(f"{name} must be unique")


def _validate_optional_non_blank(name: str, value: str | None) -> None:
    if value is not None:
        _require_non_blank(name, value)


def _require_non_blank(name: str, value: str) -> None:
    if not value.strip():
        raise GenerationJobPollingError(f"{name} must not be blank")
