from __future__ import annotations

import pytest

from services.integrations.desktop_video_composition import _reference_relay_from_environment
from services.integrations.video_runtime import VideoRuntimeError
from services.reference_relay import HttpReferenceRelayClient
from services.source_media_desktop import _native_frame_relay_configured


def _clear(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ILAIOS_REFERENCE_RELAY_UPLOAD_URL", raising=False)
    monkeypatch.delenv("ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN", raising=False)
    monkeypatch.delenv("ILAIOS_VIDEO_PROVIDER_MODE", raising=False)


def test_native_relay_is_off_when_no_relay_configuration_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear(monkeypatch)

    assert _reference_relay_from_environment("managed-bounded") is None
    assert not _native_frame_relay_configured()


def test_native_relay_requires_both_url_and_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("ILAIOS_REFERENCE_RELAY_UPLOAD_URL", "https://relay.example/v1/reference-relay")

    with pytest.raises(VideoRuntimeError, match="both upload URL and upload token"):
        _reference_relay_from_environment("managed-bounded")


def test_native_relay_is_forbidden_in_verified_free_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("ILAIOS_REFERENCE_RELAY_UPLOAD_URL", "https://relay.example/v1/reference-relay")
    monkeypatch.setenv("ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN", "secret-token")

    with pytest.raises(VideoRuntimeError, match="only in explicit managed-bounded mode"):
        _reference_relay_from_environment("verified-free")


def test_native_relay_rejects_non_https_upload_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("ILAIOS_REFERENCE_RELAY_UPLOAD_URL", "http://relay.example/v1/reference-relay")
    monkeypatch.setenv("ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN", "secret-token")

    with pytest.raises(VideoRuntimeError, match="configuration is invalid"):
        _reference_relay_from_environment("managed-bounded")


def test_managed_https_relay_enables_same_frame_admission_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("ILAIOS_VIDEO_PROVIDER_MODE", "managed-bounded")
    monkeypatch.setenv("ILAIOS_REFERENCE_RELAY_UPLOAD_URL", "https://relay.example/v1/reference-relay")
    monkeypatch.setenv("ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN", "secret-token")

    relay = _reference_relay_from_environment("managed-bounded")

    assert isinstance(relay, HttpReferenceRelayClient)
    assert _native_frame_relay_configured()
