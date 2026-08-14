"""Derived Media Factory telemetry that never becomes execution/evidence truth."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol


class MediaObservabilityError(ValueError):
    """Raised when telemetry would expose sensitive or malformed data."""


class MediaTelemetrySink(Protocol):
    """Existing observability implementations may consume these derived events."""

    def emit(self, event_name: str, attributes: Mapping[str, str]) -> None: ...


@dataclass(frozen=True, slots=True)
class MediaOperationalEvent:
    event_name: str
    tenant_id: str
    operation_id: str
    state: str
    provider_or_platform: str | None = None
    artifact_sha256: str | None = None
    reason_code: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("event_name", self.event_name),
            ("tenant_id", self.tenant_id),
            ("operation_id", self.operation_id),
            ("state", self.state),
        ):
            _text(name, value)
        for name, value in (
            ("provider_or_platform", self.provider_or_platform),
            ("reason_code", self.reason_code),
        ):
            if value is not None:
                _text(name, value)
        if self.artifact_sha256 is not None:
            _sha256(self.artifact_sha256)


class MediaObservabilityProjector:
    """Project already-observed state into metrics/log events; never mutate state."""

    def __init__(self, sink: MediaTelemetrySink) -> None:
        self._sink = sink

    def emit(self, event: MediaOperationalEvent) -> None:
        attributes: dict[str, str] = {
            "tenant_id": event.tenant_id,
            "operation_id": event.operation_id,
            "state": event.state,
        }
        provider_or_platform = event.provider_or_platform
        if provider_or_platform is not None:
            attributes["provider_or_platform"] = provider_or_platform
        artifact_sha256 = event.artifact_sha256
        if artifact_sha256 is not None:
            attributes["artifact_sha256"] = artifact_sha256
        reason_code = event.reason_code
        if reason_code is not None:
            attributes["reason_code"] = reason_code
        _assert_safe_attributes(attributes)
        self._sink.emit(event.event_name, attributes)


def publication_ambiguous_event(
    *, tenant_id: str, package_id: str, platform: str, artifact_sha256: str
) -> MediaOperationalEvent:
    return MediaOperationalEvent(
        event_name="media.publication.ambiguous",
        tenant_id=tenant_id,
        operation_id=package_id,
        state="AMBIGUOUS",
        provider_or_platform=platform,
        artifact_sha256=artifact_sha256,
        reason_code="reconciliation_required",
    )


def provider_circuit_open_event(
    *, tenant_id: str, operation_id: str, provider_id: str
) -> MediaOperationalEvent:
    return MediaOperationalEvent(
        event_name="media.provider.circuit_open",
        tenant_id=tenant_id,
        operation_id=operation_id,
        state="OPEN",
        provider_or_platform=provider_id,
        reason_code="canonical_routing_reevaluation_required",
    )


def repair_exhausted_event(
    *, tenant_id: str, operation_id: str, artifact_sha256: str
) -> MediaOperationalEvent:
    return MediaOperationalEvent(
        event_name="media.repair.exhausted",
        tenant_id=tenant_id,
        operation_id=operation_id,
        state="BLOCKED",
        artifact_sha256=artifact_sha256,
        reason_code="quality_floor_not_met",
    )


def _assert_safe_attributes(attributes: Mapping[str, str]) -> None:
    forbidden = ("secret", "token", "api_key", "authorization", "prompt", "credential")
    for key, value in attributes.items():
        normalized_key = key.lower()
        if any(word in normalized_key for word in forbidden):
            raise MediaObservabilityError(f"sensitive telemetry attribute forbidden: {key}")
        _text(key, value)


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise MediaObservabilityError(f"{name} must be non-blank and trimmed")


def _sha256(value: str) -> None:
    if len(value) != 64:
        raise MediaObservabilityError("artifact_sha256 must be SHA-256 hex")
    try:
        int(value, 16)
    except ValueError as exc:
        raise MediaObservabilityError("artifact_sha256 must be SHA-256 hex") from exc
