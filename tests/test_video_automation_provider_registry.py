"""Tests for the ILAIOS Video Automation provider registry."""

from types import MappingProxyType

import pytest

from src.video_automation.models import ProviderRequest, ProviderResult
from src.video_automation.provider_registry import ProviderRegistry
from src.video_automation.providers import BaseProvider, ProviderCapabilities


class FakeProvider(BaseProvider):
    """Deterministic provider for registry tests."""

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self._validate_request(request)
        return ProviderResult(
            request_id=request.request_id,
            provider_name=self.capabilities.provider_name,
            success=True,
            external_id=f"{self.capabilities.provider_name}-result",
        )


def make_provider(
    name: str,
    *,
    operations: tuple[str, ...],
    is_paid: bool,
) -> FakeProvider:
    return FakeProvider(
        ProviderCapabilities(
            provider_name=name,
            operations=operations,
            is_paid=is_paid,
        )
    )


def test_registry_starts_empty() -> None:
    registry = ProviderRegistry()
    assert len(registry) == 0
    assert registry.list_provider_names() == ()


def test_registry_can_register_and_get_provider() -> None:
    provider = make_provider(
        "local-test",
        operations=("generate_video",),
        is_paid=False,
    )
    registry = ProviderRegistry()

    registry.register(provider)

    assert len(registry) == 1
    assert registry.contains("local-test") is True
    assert registry.get("local-test") is provider


def test_registry_rejects_duplicate_provider_name() -> None:
    first = make_provider(
        "provider-a",
        operations=("generate_video",),
        is_paid=False,
    )
    second = make_provider(
        "provider-a",
        operations=("generate_image",),
        is_paid=True,
    )
    registry = ProviderRegistry((first,))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(second)


def test_registry_get_rejects_unknown_provider() -> None:
    registry = ProviderRegistry()

    with pytest.raises(KeyError, match="provider not registered"):
        registry.get("missing")


def test_registry_unregister_returns_removed_provider() -> None:
    provider = make_provider(
        "provider-a",
        operations=("generate_video",),
        is_paid=False,
    )
    registry = ProviderRegistry((provider,))

    removed = registry.unregister("provider-a")

    assert removed is provider
    assert len(registry) == 0


def test_registry_unregister_rejects_unknown_provider() -> None:
    registry = ProviderRegistry()

    with pytest.raises(KeyError, match="provider not registered"):
        registry.unregister("missing")


def test_registry_lists_provider_names_deterministically() -> None:
    registry = ProviderRegistry(
        (
            make_provider(
                "z-provider",
                operations=("generate_video",),
                is_paid=False,
            ),
            make_provider(
                "a-provider",
                operations=("generate_video",),
                is_paid=False,
            ),
        )
    )

    assert registry.list_provider_names() == ("a-provider", "z-provider")


def test_registry_lists_capabilities_in_provider_order() -> None:
    registry = ProviderRegistry(
        (
            make_provider(
                "z-provider",
                operations=("generate_video",),
                is_paid=False,
            ),
            make_provider(
                "a-provider",
                operations=("generate_image",),
                is_paid=True,
            ),
        )
    )

    capabilities = registry.list_capabilities()

    assert tuple(item.provider_name for item in capabilities) == (
        "a-provider",
        "z-provider",
    )


def test_registry_filters_providers_by_operation() -> None:
    image_provider = make_provider(
        "image-provider",
        operations=("generate_image",),
        is_paid=False,
    )
    video_provider = make_provider(
        "video-provider",
        operations=("generate_video",),
        is_paid=False,
    )
    registry = ProviderRegistry((video_provider, image_provider))

    matches = registry.providers_supporting("generate_video")

    assert matches == (video_provider,)


def test_registry_can_exclude_paid_providers() -> None:
    free_provider = make_provider(
        "free-provider",
        operations=("generate_video",),
        is_paid=False,
    )
    paid_provider = make_provider(
        "paid-provider",
        operations=("generate_video",),
        is_paid=True,
    )
    registry = ProviderRegistry((paid_provider, free_provider))

    matches = registry.providers_supporting(
        "generate_video",
        include_paid=False,
    )

    assert matches == (free_provider,)


def test_registry_capability_map_is_read_only_and_sorted() -> None:
    registry = ProviderRegistry(
        (
            make_provider(
                "z-provider",
                operations=("generate_video",),
                is_paid=False,
            ),
            make_provider(
                "a-provider",
                operations=("generate_image",),
                is_paid=False,
            ),
        )
    )

    capability_map = registry.capability_map()

    assert isinstance(capability_map, MappingProxyType)
    assert tuple(capability_map) == ("a-provider", "z-provider")
    with pytest.raises(TypeError):
        capability_map["x"] = capability_map["a-provider"]  # type: ignore[index]


def test_registry_descriptors_are_deterministic() -> None:
    registry = ProviderRegistry(
        (
            make_provider(
                "b-provider",
                operations=("generate_video",),
                is_paid=False,
            ),
            make_provider(
                "a-provider",
                operations=("generate_image",),
                is_paid=False,
            ),
        )
    )

    descriptors = registry.descriptors()

    assert tuple(item.provider_name for item in descriptors) == (
        "a-provider",
        "b-provider",
    )
    assert descriptors[0].provider_name == descriptors[0].capabilities.provider_name
