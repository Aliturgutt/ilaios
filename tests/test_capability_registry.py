"""Canonical ILAIOS capability-registry consolidation proofs."""

from services.capability_registry import (
    CAPABILITIES,
    capabilities_for_domain,
    capability,
    validate_capability_registry,
)


def test_all_active_capability_ids_use_single_ilaios_namespace() -> None:
    validate_capability_registry()
    assert CAPABILITIES
    assert all(item.capability_id.startswith("ilaios.capability.") for item in CAPABILITIES)
    assert all(
        legacy not in item.capability_id.casefold()
        for item in CAPABILITIES
        for legacy in ("hermes", "ilakos", "ilaten")
    )


def test_factories_are_single_capabilities_not_legacy_parallel_products() -> None:
    factories = {item.capability_id: item for item in capabilities_for_domain("factory")}
    assert {
        "ilaios.capability.video-media-factory",
        "ilaios.capability.web-factory",
        "ilaios.capability.software-factory",
        "ilaios.capability.security-factory",
        "ilaios.capability.app-factory",
        "ilaios.capability.research-data",
        "ilaios.capability.creative-document",
        "ilaios.capability.commerce-growth",
        "ilaios.capability.personal-operations",
    } <= factories.keys()
    assert factories["ilaios.capability.video-media-factory"].implementation_roots == (
        "src/video_automation",
    )
    assert factories["ilaios.capability.security-factory"].implementation_roots == (
        "services/security_factory.py",
    )


def test_legacy_lineage_is_preserved_only_as_provenance_metadata() -> None:
    video = capability("ilaios.capability.video-media-factory")
    assert video.legacy_sources == frozenset({"Hermes", "ILAKOS"})
    enterprise = capability("ilaios.capability.policy-governance")
    assert enterprise.legacy_sources == frozenset({"Hermes", "ILAKOS", "ILATEN"})


def test_every_dependency_resolves_to_one_canonical_capability() -> None:
    known = {item.capability_id for item in CAPABILITIES}
    for item in CAPABILITIES:
        assert item.dependencies <= known
