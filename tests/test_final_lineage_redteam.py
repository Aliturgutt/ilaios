"""Final lineage red-team invariants for active ILAIOS identities and promoted factories."""

from services.agent_registry import CANONICAL_AGENT_REGISTRY
from services.capability_registry import CAPABILITIES
from services.enterprise_hardening import PROMOTED_FACTORY_IDS


_LEGACY = ("hermes", "ilakos", "ilaten")


def test_active_machine_ids_use_only_ilaios_namespaces() -> None:
    for definition in CAPABILITIES:
        assert definition.capability_id.startswith("ilaios.capability.")
        assert not any(name in definition.capability_id.casefold() for name in _LEGACY)

    for registration in CANONICAL_AGENT_REGISTRY:
        agent_id = registration.manifest.agent_id
        assert agent_id.startswith("ilaios.agent.")
        assert not any(name in agent_id.casefold() for name in _LEGACY)


def test_promoted_factories_have_unique_bound_implementation_roots() -> None:
    promoted = [item for item in CAPABILITIES if item.capability_id in PROMOTED_FACTORY_IDS]
    assert {item.capability_id for item in promoted} == set(PROMOTED_FACTORY_IDS)

    roots: list[str] = []
    for definition in promoted:
        assert definition.domain == "factory"
        assert definition.implementation_roots
        roots.extend(definition.implementation_roots)

    assert len(roots) == len(set(roots))


def test_legacy_names_remain_provenance_only() -> None:
    assert any(definition.legacy_sources for definition in CAPABILITIES)
    assert any(
        registration.manifest.alias == "Integration Bridge"
        for registration in CANONICAL_AGENT_REGISTRY
    )
    assert all(
        registration.manifest.agent_id != registration.manifest.alias
        for registration in CANONICAL_AGENT_REGISTRY
    )
