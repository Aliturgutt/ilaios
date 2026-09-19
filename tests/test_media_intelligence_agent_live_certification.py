from datetime import datetime, timezone
from pathlib import Path

import pytest

from services.agent_readiness import effective_readiness
from services.agent_registry import RuntimeReadiness, registration_for
from services.media_intelligence_agent_execution import (
    MEDIA_INTELLIGENCE_AGENT_BINDINGS,
)
from services.media_intelligence_agent_live_certification import (
    MediaIntelligenceAgentLiveCertificationError,
    _assert_projected_verified,
    _invocation,
    _verified_proof,
    run_media_intelligence_agent_live_certification,
)


def test_live_certification_requires_exact_source_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GITHUB_SHA", raising=False)

    with pytest.raises(
        MediaIntelligenceAgentLiveCertificationError,
        match="exact lowercase GITHUB_SHA is required",
    ):
        run_media_intelligence_agent_live_certification(
            repository_root=tmp_path,
            output_dir=tmp_path / "proof",
            now=datetime(2026, 8, 20, tzinfo=timezone.utc),
        )


def test_live_certification_fails_closed_without_provider_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    monkeypatch.setattr(
        "services.media_intelligence_agent_live_certification."
        "discover_free_openrouter_agent_configuration",
        lambda: None,
    )

    with pytest.raises(
        MediaIntelligenceAgentLiveCertificationError,
        match="OPENROUTER_API_KEY is unavailable",
    ):
        run_media_intelligence_agent_live_certification(
            repository_root=tmp_path,
            output_dir=tmp_path / "proof",
            now=datetime(2026, 8, 20, tzinfo=timezone.utc),
        )


def test_certification_invocation_keeps_exact_manifest_authority() -> None:
    binding = next(
        item
        for item in MEDIA_INTELLIGENCE_AGENT_BINDINGS
        if item.agent_id == "ilaios.agent.media.publishing.v1"
    )
    prompt = "Return a bounded publication proposal only."

    invocation = _invocation(
        binding.agent_id,
        binding.capability,
        binding.permission,
        prompt=prompt,
    )

    manifest = registration_for(binding.agent_id).manifest
    assert invocation.target_id == binding.agent_id
    assert invocation.capability == "social.publish-propose"
    assert invocation.permission == "artifact.read"
    assert invocation.capability in manifest.capabilities
    assert invocation.permission in manifest.permissions
    assert invocation.requested_output_class == "proposal"
    assert invocation.prompt == prompt
    assert invocation.external_egress is True
    assert invocation.dlp_approved is True
    assert invocation.security_scan_passed is True
    assert invocation.contains_secret is False


def test_verified_proof_requires_all_readiness_gates() -> None:
    agent_id = "ilaios.agent.intelligence.research.v1"
    proof = _verified_proof(agent_id, "b" * 64)

    assert proof.verifier_id == registration_for(agent_id).manifest.verifier_id
    assert proof.invocation_passed is True
    assert proof.skill_passed is True
    assert proof.permission_passed is True
    assert proof.provider_passed is True
    assert proof.output_passed is True
    assert proof.independent_verification_passed is True
    assert proof.evidence_persisted is True
    assert proof.desktop_projection_passed is True
    assert proof.regression_e2e_passed is True
    assert effective_readiness(proof) is RuntimeReadiness.VERIFIED


def test_desktop_projection_must_show_every_expected_agent_verified() -> None:
    expected = {
        "ilaios.agent.media.story.v1",
        "ilaios.agent.intelligence.research.v1",
    }
    projection: dict[str, object] = {
        "agents": [
            {
                "agent_id": "ilaios.agent.media.story.v1",
                "readiness": "verified",
            },
            {
                "agent_id": "ilaios.agent.intelligence.research.v1",
                "readiness": "verified",
            },
        ]
    }

    _assert_projected_verified(projection, expected)

    poisoned: dict[str, object] = {
        "agents": [
            {
                "agent_id": "ilaios.agent.media.story.v1",
                "readiness": "verified",
            },
            {
                "agent_id": "ilaios.agent.intelligence.research.v1",
                "readiness": "registered",
            },
        ]
    }
    with pytest.raises(
        MediaIntelligenceAgentLiveCertificationError,
        match="Desktop projection failed",
    ):
        _assert_projected_verified(poisoned, expected)
