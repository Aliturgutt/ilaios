from services.agent_registry import (
    CANONICAL_AGENT_REGISTRY,
    INDEPENDENT_VERIFIER_ID,
    registration_for,
)
from services.operations_meta_agent_execution import (
    OPERATIONS_META_AGENT_BINDINGS,
    OPERATIONS_META_GOVERNED_AI_CAPABILITIES,
    _bounded_provider_failure_classification,
    operations_meta_binding_for,
)
from services.runtime.ai_provider_adapter import AIProviderTransportError


def test_operations_meta_bindings_cover_exact_canonical_6_plus_2() -> None:
    expected = {
        item.manifest.agent_id
        for item in CANONICAL_AGENT_REGISTRY
        if item.manifest.team in {"operations", "meta"}
    }
    assert len(expected) == 8
    assert {item.agent_id for item in OPERATIONS_META_AGENT_BINDINGS} == expected


def test_operations_meta_bindings_never_exceed_manifest_authority() -> None:
    for binding in OPERATIONS_META_AGENT_BINDINGS:
        manifest = registration_for(binding.agent_id).manifest
        assert binding.capability in manifest.capabilities
        assert binding.permission in manifest.permissions


def test_independent_verifier_remains_outside_generic_provider_boundary() -> None:
    verifier = operations_meta_binding_for(INDEPENDENT_VERIFIER_ID)
    assert verifier.execution_mode == "independent-verification"
    assert verifier.capability == "evidence.verify"
    assert "evidence.verify" not in OPERATIONS_META_GOVERNED_AI_CAPABILITIES


def test_operations_and_self_development_are_bounded_proposal_paths() -> None:
    assert len(OPERATIONS_META_GOVERNED_AI_CAPABILITIES) == 7
    assert operations_meta_binding_for(
        "ilaios.agent.operations.automation.v1"
    ).permission == "workflow.read"
    assert operations_meta_binding_for(
        "ilaios.agent.operations.recovery.v1"
    ).permission == "evidence.read"
    assert operations_meta_binding_for(
        "ilaios.agent.operations.provider-watcher.v1"
    ).permission == "provider-health.read"
    assert operations_meta_binding_for(
        "ilaios.agent.meta.self-development.v1"
    ).permission == "repository.read"
    assert "provider.request" not in OPERATIONS_META_GOVERNED_AI_CAPABILITIES
    assert "social.publish" not in OPERATIONS_META_GOVERNED_AI_CAPABILITIES


def test_provider_failure_classification_exposes_only_bounded_metadata() -> None:
    raw_secret = "sk-proj-never-log-this"
    cause = ValueError(raw_secret)
    failure = AIProviderTransportError(
        f"provider response included {raw_secret}",
        retryable=True,
        retry_after_seconds=7.5,
    )
    failure.__cause__ = cause

    classification = _bounded_provider_failure_classification(failure)

    assert classification == (
        "AIProviderTransportError(retryable=true,retry_after_seconds=7.5)>ValueError"
    )
    assert raw_secret not in classification
