from __future__ import annotations

from unittest.mock import patch

import pytest

from services.software_factory_external_validation import (
    ExternalRepositoryEvidence,
    SoftwareFactoryExternalValidationError,
    assess_commercial_readiness,
    prove_repository_provider_route,
    validate_public_github_repository,
)


def test_provider_route_reuses_canonical_router() -> None:
    evidence = prove_repository_provider_route()
    assert evidence.provider_id == "github.readonly"
    assert evidence.capability == "software.repository.read"
    assert evidence.deterministic_first is True
    assert any(item == "provider=github.readonly" for item in evidence.evidence)


def test_public_repository_probe_binds_exact_head_and_license() -> None:
    responses = iter(
        (
            {"private": False, "default_branch": "main", "archived": False},
            {"sha": "a" * 40},
            {"license": {"spdx_id": "MIT"}},
        )
    )
    with patch(
        "services.software_factory_external_validation._github_json",
        side_effect=lambda *args, **kwargs: next(responses),
    ):
        evidence = validate_public_github_repository("example/project")
    assert evidence.repository == "example/project"
    assert evidence.head_sha == "a" * 40
    assert evidence.license_spdx == "MIT"
    assert evidence.read_only is True


def test_repository_probe_fails_closed_for_private_repo() -> None:
    with patch(
        "services.software_factory_external_validation._github_json",
        return_value={"private": True, "default_branch": "main"},
    ):
        with pytest.raises(SoftwareFactoryExternalValidationError, match="public"):
            validate_public_github_repository("example/private")


def test_commercial_readiness_passes_only_bounded_zero_cost_case() -> None:
    repo = ExternalRepositoryEvidence(
        repository="example/project",
        provider="github",
        default_branch="main",
        head_sha="b" * 40,
        license_spdx="MIT",
        private=False,
        archived=False,
        read_only=True,
    )
    evidence = assess_commercial_readiness(repo, provider_cost_usd=0.0)
    assert evidence.technical_gate_passed is True
    assert evidence.legal_clearance_claimed is False
    assert evidence.production_release_claimed is False


def test_commercial_readiness_rejects_unproven_license_or_paid_provider() -> None:
    repo = ExternalRepositoryEvidence(
        repository="example/project",
        provider="github",
        default_branch="main",
        head_sha="c" * 40,
        license_spdx="GPL-3.0",
        private=False,
        archived=False,
        read_only=True,
    )
    evidence = assess_commercial_readiness(repo, provider_cost_usd=0.01)
    assert evidence.technical_gate_passed is False
    assert "LICENSE_NOT_IN_BOUNDED_PERMISSIVE_SET" in evidence.reasons
    assert "NONZERO_PROVIDER_COST_REQUIRES_SEPARATE_BUDGET_APPROVAL" in evidence.reasons


def test_negative_provider_cost_is_rejected() -> None:
    repo = ExternalRepositoryEvidence(
        repository="example/project",
        provider="github",
        default_branch="main",
        head_sha="d" * 40,
        license_spdx="MIT",
        private=False,
        archived=False,
        read_only=True,
    )
    with pytest.raises(SoftwareFactoryExternalValidationError, match="negative"):
        assess_commercial_readiness(repo, provider_cost_usd=-0.01)
