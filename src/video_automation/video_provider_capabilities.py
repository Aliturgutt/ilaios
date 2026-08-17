"""Provider-neutral capability resolution for adaptive Video Factory shots.

Catalog facts are runtime evidence. This module never promotes a named model by
assumption; callers must construct candidates from an authoritative live
provider catalog and exact model identifiers.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderVideoCapabilities:
    provider_id: str
    model_id: str
    supported_durations: tuple[float, ...] = ()
    supported_resolutions: tuple[str, ...] = ()
    native_audio: bool = False
    first_frame: bool = False
    last_frame: bool = False
    input_references: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id.strip() or not self.model_id.strip():
            raise ValueError("provider_id and model_id must not be blank")
        if any(value <= 0 for value in self.supported_durations):
            raise ValueError("supported durations must be positive")

    def supports_duration(self, duration_seconds: float, *, tolerance: float = 0.01) -> bool:
        if duration_seconds <= 0:
            return False
        if not self.supported_durations:
            return False
        return any(abs(value - duration_seconds) <= tolerance for value in self.supported_durations)


@dataclass(frozen=True, slots=True)
class ShotCapabilityRequirements:
    duration_seconds: float
    resolution: str | None = None
    native_audio: bool = False
    first_frame: bool = False
    last_frame: bool = False
    input_references: bool = False

    def __post_init__(self) -> None:
        if self.duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        if self.resolution is not None and not self.resolution.strip():
            raise ValueError("resolution must not be blank")


@dataclass(frozen=True, slots=True)
class CapabilityResolution:
    compatible: bool
    reason_code: str
    provider_id: str
    model_id: str


def resolve_capability(
    capabilities: ProviderVideoCapabilities,
    requirements: ShotCapabilityRequirements,
) -> CapabilityResolution:
    """Fail closed when a required video capability is absent or unknown."""

    reason = _incompatibility_reason(capabilities, requirements)
    return CapabilityResolution(
        compatible=reason is None,
        reason_code="COMPATIBLE" if reason is None else reason,
        provider_id=capabilities.provider_id,
        model_id=capabilities.model_id,
    )


def resolve_compatible_providers(
    candidates: tuple[ProviderVideoCapabilities, ...],
    requirements: ShotCapabilityRequirements,
) -> tuple[ProviderVideoCapabilities, ...]:
    """Return only exact compatible candidates, preserving caller ranking."""

    return tuple(
        candidate
        for candidate in candidates
        if resolve_capability(candidate, requirements).compatible
    )


def _incompatibility_reason(
    capabilities: ProviderVideoCapabilities,
    requirements: ShotCapabilityRequirements,
) -> str | None:
    if not capabilities.supports_duration(requirements.duration_seconds):
        return "DURATION_UNSUPPORTED_OR_UNKNOWN"
    if requirements.resolution is not None:
        if not capabilities.supported_resolutions:
            return "RESOLUTION_UNKNOWN"
        if requirements.resolution not in capabilities.supported_resolutions:
            return "RESOLUTION_UNSUPPORTED"
    if requirements.native_audio and not capabilities.native_audio:
        return "NATIVE_AUDIO_UNSUPPORTED"
    if requirements.first_frame and not capabilities.first_frame:
        return "FIRST_FRAME_UNSUPPORTED"
    if requirements.last_frame and not capabilities.last_frame:
        return "LAST_FRAME_UNSUPPORTED"
    if requirements.input_references and not capabilities.input_references:
        return "INPUT_REFERENCES_UNSUPPORTED"
    return None
