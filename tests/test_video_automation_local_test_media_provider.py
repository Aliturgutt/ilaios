"""Tests for canonical M11 Local Test Media Provider."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.video_automation.configuration import VideoAutomationPolicy
from src.video_automation.local_test_media_provider import (
    LocalTestMediaProviderError,
    LocalTestVideoProvider,
)
from src.video_automation.models import ProviderRequest
from src.video_automation.provider_registry import ProviderRegistry


def _write_fixture(directory: Path, payload: bytes = b"local-test-video") -> Path:
    fixture = directory / "placeholder.mp4"
    fixture.write_bytes(payload)
    return fixture


def _request(
    *,
    provider_name: str = "local-test",
    operation: str = "video.generate",
    request_id: str = "dispatch-1",
    job_id: str = "job-1",
) -> ProviderRequest:
    return ProviderRequest(
        request_id=request_id,
        job_id=job_id,
        provider_name=provider_name,
        operation=operation,
        payload={},
    )


def test_provider_is_free_and_test_mode_compatible() -> None:
    with TemporaryDirectory() as directory_name:
        fixture = _write_fixture(Path(directory_name))
        provider = LocalTestVideoProvider(fixture)

        assert provider.capabilities.provider_name == "local-test"
        assert provider.capabilities.operations == ("video.generate",)
        assert provider.capabilities.is_paid is False
        assert provider.capabilities.metadata["execution_mode"] == "test"
        assert provider.capabilities.metadata["media_type"] == "video"

        policy = VideoAutomationPolicy.test_default()
        assert policy.can_use_provider(
            provider.capabilities.provider_name,
            is_paid=provider.capabilities.is_paid,
        )


def test_provider_registers_through_existing_registry() -> None:
    with TemporaryDirectory() as directory_name:
        fixture = _write_fixture(Path(directory_name))
        provider = LocalTestVideoProvider(fixture)
        registry = ProviderRegistry((provider,))

        assert registry.contains("local-test")
        assert registry.get("local-test") is provider
        assert registry.providers_supporting(
            "video.generate",
            include_paid=False,
        ) == (provider,)


def test_execute_returns_deterministic_local_fixture_result() -> None:
    with TemporaryDirectory() as directory_name:
        fixture = _write_fixture(Path(directory_name))
        provider = LocalTestVideoProvider(fixture)

        first = provider.execute(_request())
        second = provider.execute(_request())

        assert first.success is True
        assert first.external_id is not None
        assert first.external_id == second.external_id
        assert first.request_id == "dispatch-1"
        assert first.provider_name == "local-test"

        expected_checksum = sha256(b"local-test-video").hexdigest()

        assert first.metadata["checksum_sha256"] == expected_checksum
        assert first.metadata["asset_path"] == str(fixture.resolve())
        assert first.metadata["source_reference"] == "local://placeholder.mp4"
        assert first.metadata["execution_mode"] == "test"
        assert first.metadata["media_type"] == "video"


def test_different_request_identity_changes_external_id() -> None:
    with TemporaryDirectory() as directory_name:
        fixture = _write_fixture(Path(directory_name))
        provider = LocalTestVideoProvider(fixture)

        first = provider.execute(_request(request_id="dispatch-1"))
        second = provider.execute(_request(request_id="dispatch-2"))

        assert first.success is True
        assert second.success is True
        assert first.external_id != second.external_id


def test_fixture_checksum_is_captured_deterministically() -> None:
    with TemporaryDirectory() as directory_name:
        fixture = _write_fixture(Path(directory_name), b"fixture-payload")
        provider = LocalTestVideoProvider(fixture)

        assert provider.fixture_path == fixture.resolve()
        assert provider.fixture_sha256 == sha256(b"fixture-payload").hexdigest()


def test_missing_fixture_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        missing = Path(directory_name) / "missing.mp4"

        with pytest.raises(LocalTestMediaProviderError, match="does not exist"):
            LocalTestVideoProvider(missing)


def test_directory_fixture_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        directory = Path(directory_name)

        with pytest.raises(
            LocalTestMediaProviderError,
            match="must reference a file",
        ):
            LocalTestVideoProvider(directory)


def test_empty_fixture_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        fixture = _write_fixture(Path(directory_name), b"")

        with pytest.raises(
            LocalTestMediaProviderError,
            match="must not reference an empty file",
        ):
            LocalTestVideoProvider(fixture)


def test_blank_provider_name_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        fixture = _write_fixture(Path(directory_name))

        with pytest.raises(LocalTestMediaProviderError, match="provider_name"):
            LocalTestVideoProvider(fixture, provider_name=" ")


def test_wrong_provider_name_returns_failed_result() -> None:
    with TemporaryDirectory() as directory_name:
        fixture = _write_fixture(Path(directory_name))
        provider = LocalTestVideoProvider(fixture)

        result = provider.execute(_request(provider_name="other-provider"))

        assert result.success is False
        assert result.error_code == "invalid_request"
        assert result.error_message is not None


def test_wrong_operation_returns_failed_result() -> None:
    with TemporaryDirectory() as directory_name:
        fixture = _write_fixture(Path(directory_name))
        provider = LocalTestVideoProvider(fixture)

        result = provider.execute(_request(operation="image.generate"))

        assert result.success is False
        assert result.error_code == "invalid_request"
        assert result.error_message is not None


def test_fixture_mutation_after_initialization_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        fixture = _write_fixture(Path(directory_name), b"original")
        provider = LocalTestVideoProvider(fixture)

        fixture.write_bytes(b"changed")

        result = provider.execute(_request())

        assert result.success is False
        assert result.error_code == "fixture_changed"
        assert result.external_id is None


def test_fixture_deletion_after_initialization_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        fixture = _write_fixture(Path(directory_name))
        provider = LocalTestVideoProvider(fixture)

        fixture.unlink()

        result = provider.execute(_request())

        assert result.success is False
        assert result.error_code == "fixture_unavailable"
        assert result.external_id is None


def test_provider_performs_no_network_or_paid_operation_contract() -> None:
    with TemporaryDirectory() as directory_name:
        fixture = _write_fixture(Path(directory_name))
        provider = LocalTestVideoProvider(fixture)

        result = provider.execute(_request())

        assert result.success is True
        assert provider.capabilities.is_paid is False
        assert result.metadata["execution_mode"] == "test"
        assert "url" not in result.metadata
        assert "api_key" not in result.metadata
