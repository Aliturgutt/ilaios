from __future__ import annotations

import pytest

from src.video_automation.video_provider_capabilities import (
    ProviderVideoCapabilities,
    ShotCapabilityRequirements,
    resolve_capability,
    resolve_compatible_providers,
)


def _capabilities(**overrides: object) -> ProviderVideoCapabilities:
    values: dict[str, object] = {
        "provider_id": "provider-a",
        "model_id": "model-a",
        "supported_durations": (4.0, 5.0, 6.0, 8.0),
        "supported_resolutions": ("720p", "1080p"),
        "native_audio": True,
        "first_frame": True,
        "last_frame": True,
        "input_references": True,
    }
    values.update(overrides)
    return ProviderVideoCapabilities(**values)  # type: ignore[arg-type]


def test_exact_capabilities_pass() -> None:
    result = resolve_capability(
        _capabilities(),
        ShotCapabilityRequirements(
            duration_seconds=6,
            resolution="1080p",
            native_audio=True,
            first_frame=True,
            last_frame=True,
            input_references=True,
        ),
    )

    assert result.compatible
    assert result.reason_code == "COMPATIBLE"


@pytest.mark.parametrize(
    ("capability_overrides", "requirements", "reason"),
    [
        ({"supported_durations": ()}, ShotCapabilityRequirements(6), "DURATION_UNSUPPORTED_OR_UNKNOWN"),
        ({}, ShotCapabilityRequirements(7), "DURATION_UNSUPPORTED_OR_UNKNOWN"),
        ({"supported_resolutions": ()}, ShotCapabilityRequirements(6, resolution="720p"), "RESOLUTION_UNKNOWN"),
        ({}, ShotCapabilityRequirements(6, resolution="4k"), "RESOLUTION_UNSUPPORTED"),
        ({"native_audio": False}, ShotCapabilityRequirements(6, native_audio=True), "NATIVE_AUDIO_UNSUPPORTED"),
        ({"first_frame": False}, ShotCapabilityRequirements(6, first_frame=True), "FIRST_FRAME_UNSUPPORTED"),
        ({"last_frame": False}, ShotCapabilityRequirements(6, last_frame=True), "LAST_FRAME_UNSUPPORTED"),
        ({"input_references": False}, ShotCapabilityRequirements(6, input_references=True), "INPUT_REFERENCES_UNSUPPORTED"),
    ],
)
def test_missing_or_unknown_required_capability_fails_closed(
    capability_overrides: dict[str, object],
    requirements: ShotCapabilityRequirements,
    reason: str,
) -> None:
    result = resolve_capability(_capabilities(**capability_overrides), requirements)

    assert not result.compatible
    assert result.reason_code == reason


def test_compatible_provider_filter_preserves_router_ranking() -> None:
    candidates = (
        _capabilities(provider_id="cheap", model_id="cheap-model"),
        _capabilities(provider_id="wrong", model_id="wrong-model", native_audio=False),
        _capabilities(provider_id="premium", model_id="premium-model"),
    )

    compatible = resolve_compatible_providers(
        candidates,
        ShotCapabilityRequirements(duration_seconds=6, native_audio=True),
    )

    assert [candidate.provider_id for candidate in compatible] == ["cheap", "premium"]
