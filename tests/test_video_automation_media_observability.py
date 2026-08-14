from __future__ import annotations

from collections.abc import Mapping

from src.video_automation.media_observability import (
    MediaObservabilityProjector,
    provider_circuit_open_event,
    publication_ambiguous_event,
    repair_exhausted_event,
)


class _Sink:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, str]]] = []

    def emit(self, event_name: str, attributes: Mapping[str, str]) -> None:
        self.events.append((event_name, dict(attributes)))


def test_media_events_are_derived_safe_projections_without_prompt_or_credentials() -> None:
    sink = _Sink()
    projector = MediaObservabilityProjector(sink)
    projector.emit(
        publication_ambiguous_event(
            tenant_id="tenant-001",
            package_id="package-001",
            platform="youtube",
            artifact_sha256="a" * 64,
        )
    )
    projector.emit(
        provider_circuit_open_event(
            tenant_id="tenant-001",
            operation_id="request-001",
            provider_id="managed-provider",
        )
    )
    projector.emit(
        repair_exhausted_event(
            tenant_id="tenant-001",
            operation_id="episode-001",
            artifact_sha256="b" * 64,
        )
    )

    assert [name for name, _ in sink.events] == [
        "media.publication.ambiguous",
        "media.provider.circuit_open",
        "media.repair.exhausted",
    ]
    for _, attributes in sink.events:
        keys = " ".join(attributes).lower()
        assert "prompt" not in keys
        assert "token" not in keys
        assert "secret" not in keys
        assert "api_key" not in keys
