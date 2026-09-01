"""Routing and skill supply-chain tests for PLATFORM.P09."""

from __future__ import annotations

import pytest

from services.runtime import (
    AgentProfile,
    ProviderProfile,
    RuntimeError,
    SkillArtifact,
    SkillRegistry,
    route_provider,
)


def _approved() -> tuple[AgentProfile, SkillArtifact, SkillRegistry]:
    agent = AgentProfile("agent-1", frozenset({"read", "render"}))
    artifact = SkillArtifact("render", b"immutable skill", frozenset({"render"}))
    registry = SkillRegistry()
    registry.approve("render", artifact.digest, frozenset({"render"}))
    return agent, artifact, registry


def test_routing_is_deterministic_first_and_evidenced() -> None:
    agent, artifact, registry = _approved()
    decision = route_provider(
        agent,
        artifact,
        registry,
        (
            ProviderProfile("z-remote", frozenset({"render"}), deterministic=False),
            ProviderProfile("b-local", frozenset({"render"}), deterministic=True),
            ProviderProfile("a-local", frozenset({"render"}), deterministic=True),
        ),
        capability="render",
    )

    assert decision.provider_id == "a-local"
    assert decision.deterministic_first is True
    assert decision.evidence[-1] == "provider=a-local"


def test_unapproved_or_tampered_skills_are_blocked() -> None:
    agent, artifact, registry = _approved()
    providers = (ProviderProfile("local", frozenset({"render"}), True),)

    with pytest.raises(RuntimeError, match="not approved"):
        route_provider(
            agent,
            SkillArtifact("unknown", b"x", frozenset()),
            registry,
            providers,
            capability="render",
        )
    with pytest.raises(RuntimeError, match="digest"):
        route_provider(
            agent,
            SkillArtifact(artifact.skill_id, b"tampered", artifact.requested_authorities),
            registry,
            providers,
            capability="render",
        )


def test_skill_cannot_expand_agent_or_registry_authority() -> None:
    agent, _, registry = _approved()
    elevated = SkillArtifact("render", b"immutable skill", frozenset({"admin"}))

    with pytest.raises(RuntimeError, match="outside approval"):
        registry.validate(elevated, agent)
