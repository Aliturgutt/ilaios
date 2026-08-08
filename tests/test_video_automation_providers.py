"""Tests for provider-independent ILAIOS Video Automation interfaces."""

from typing import cast

import pytest

from src.video_automation.models import (
    MediaAsset,
    MediaType,
    ProviderRequest,
    ProviderResult,
)
from src.video_automation.providers import (
    BaseProvider,
    MediaProviderOutput,
    Provider,
    ProviderCapabilities,
    PublishingProviderOutput,
)


class FakeProvider(BaseProvider):
    """Minimal deterministic provider used for interface tests."""

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self._validate_request(request)
        return ProviderResult(
            request_id=request.request_id,
            provider_name=self.capabilities.provider_name,
            success=True,
            external_id="external-1",
        )


def make_capabilities() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="local-test",
        operations=("generate_video", "generate_image"),
        is_paid=False,
        metadata={"tier": "test"},
    )


def test_capabilities_support_known_operation() -> None:
    capabilities = make_capabilities()
    assert capabilities.supports("generate_video") is True
    assert capabilities.supports("publish") is False


def test_capabilities_require_operations() -> None:
    with pytest.raises(ValueError, match="operations must not be empty"):
        ProviderCapabilities(
            provider_name="provider",
            operations=(),
            is_paid=False,
        )


def test_capabilities_reject_duplicate_operations() -> None:
    with pytest.raises(ValueError, match="duplicate operation"):
        ProviderCapabilities(
            provider_name="provider",
            operations=("generate", "generate"),
            is_paid=False,
        )


def test_capability_metadata_is_sorted_and_read_only() -> None:
    capabilities = ProviderCapabilities(
        provider_name="provider",
        operations=("generate",),
        is_paid=False,
        metadata={"z": 2, "a": 1},
    )

    assert tuple(capabilities.metadata.items()) == (("a", 1), ("z", 2))
    with pytest.raises(TypeError):
        capabilities.metadata["x"] = 3  # type: ignore[index]


def test_base_provider_exposes_capabilities() -> None:
    provider = FakeProvider(make_capabilities())
    assert provider.capabilities.provider_name == "local-test"


def test_provider_runtime_protocol_matches_fake_provider() -> None:
    provider = FakeProvider(make_capabilities())
    assert isinstance(provider, Provider)
    typed_provider = cast(Provider, provider)
    assert typed_provider.capabilities.is_paid is False


def test_provider_rejects_mismatched_provider_name() -> None:
    provider = FakeProvider(make_capabilities())

    with pytest.raises(ValueError, match="does not match"):
        provider.execute(
            ProviderRequest(
                request_id="req-1",
                job_id="job-1",
                provider_name="other-provider",
                operation="generate_video",
            )
        )


def test_provider_rejects_unsupported_operation() -> None:
    provider = FakeProvider(make_capabilities())

    with pytest.raises(ValueError, match="does not support operation"):
        provider.execute(
            ProviderRequest(
                request_id="req-1",
                job_id="job-1",
                provider_name="local-test",
                operation="publish",
            )
        )


def test_provider_executes_supported_request() -> None:
    provider = FakeProvider(make_capabilities())

    result = provider.execute(
        ProviderRequest(
            request_id="req-1",
            job_id="job-1",
            provider_name="local-test",
            operation="generate_video",
        )
    )

    assert result.success is True
    assert result.external_id == "external-1"


def test_successful_media_output_requires_asset() -> None:
    result = ProviderResult(
        request_id="req-1",
        provider_name="local-test",
        success=True,
        external_id="external-1",
    )

    with pytest.raises(ValueError, match="requires an asset"):
        MediaProviderOutput(provider_result=result, asset=None)


def test_failed_media_output_rejects_asset() -> None:
    result = ProviderResult(
        request_id="req-1",
        provider_name="local-test",
        success=False,
        error_message="provider failed",
    )
    asset = MediaAsset(
        asset_id="asset-1",
        job_id="job-1",
        media_type=MediaType.VIDEO,
        file_path="media/clip.mp4",
        checksum_sha256="a" * 64,
        provider_name="local-test",
        source_reference="fixture://clip",
    )

    with pytest.raises(ValueError, match="must not contain an asset"):
        MediaProviderOutput(provider_result=result, asset=asset)


def test_successful_media_output_accepts_asset() -> None:
    result = ProviderResult(
        request_id="req-1",
        provider_name="local-test",
        success=True,
        external_id="external-1",
    )
    asset = MediaAsset(
        asset_id="asset-1",
        job_id="job-1",
        media_type=MediaType.VIDEO,
        file_path="media/clip.mp4",
        checksum_sha256="a" * 64,
        provider_name="local-test",
        source_reference="fixture://clip",
    )

    output = MediaProviderOutput(provider_result=result, asset=asset)
    assert output.asset is asset


def test_successful_publishing_output_requires_post_id() -> None:
    result = ProviderResult(
        request_id="req-1",
        provider_name="youtube",
        success=True,
        external_id="external-1",
    )

    with pytest.raises(ValueError, match="requires platform_post_id"):
        PublishingProviderOutput(provider_result=result)


def test_failed_publishing_output_rejects_identifiers() -> None:
    result = ProviderResult(
        request_id="req-1",
        provider_name="youtube",
        success=False,
        error_message="upload failed",
    )

    with pytest.raises(ValueError, match="must not contain publication identifiers"):
        PublishingProviderOutput(
            provider_result=result,
            platform_post_id="post-1",
        )
