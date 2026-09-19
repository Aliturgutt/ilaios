"""Cloud isolation and deployment-profile acceptance for PLATFORM.P19."""

import pytest

from services.cloud import (
    CloudPolicyError,
    DeploymentProfile,
    TenantBoundary,
    TenantPolicy,
)


def _boundary() -> TenantBoundary:
    boundary = TenantBoundary()
    boundary.register(TenantPolicy("a", "eu-west", DeploymentProfile.SHARED, 1, "bill-a"))
    boundary.register(TenantPolicy("b", "us-east", DeploymentProfile.PRIVATE, 2, "bill-b"))
    return boundary


def test_profile_isolation_residency_quota_and_billing_acceptance() -> None:
    boundary = _boundary()
    assert boundary.authorize("a", resource_tenant="a", region="eu-west") is DeploymentProfile.SHARED
    assert boundary.authorize("b", resource_tenant="b", region="us-east") is DeploymentProfile.PRIVATE
    with pytest.raises(CloudPolicyError, match="quota"):
        boundary.authorize("a", resource_tenant="a", region="eu-west")


def test_cross_tenant_region_and_abuse_fail_closed() -> None:
    boundary = _boundary()
    with pytest.raises(CloudPolicyError, match="cross-tenant"):
        boundary.authorize("a", resource_tenant="b", region="eu-west")
    with pytest.raises(CloudPolicyError, match="residency"):
        boundary.authorize("a", resource_tenant="a", region="us-east")
    boundary.block_for_abuse("b")
    with pytest.raises(CloudPolicyError, match="blocked"):
        boundary.authorize("b", resource_tenant="b", region="us-east")


def test_tenant_policy_replacement_is_denied() -> None:
    boundary = _boundary()
    with pytest.raises(CloudPolicyError, match="replacement denied"):
        boundary.register(
            TenantPolicy("a", "us-east", DeploymentProfile.PRIVATE, 100, "attacker-billing")
        )
    assert boundary.authorize("a", resource_tenant="a", region="eu-west") is DeploymentProfile.SHARED


def test_tenant_identity_and_region_are_required() -> None:
    boundary = TenantBoundary()
    with pytest.raises(CloudPolicyError, match="identity, region"):
        boundary.register(TenantPolicy("", "eu-west", DeploymentProfile.SHARED, 1, "bill-a"))
    with pytest.raises(CloudPolicyError, match="identity, region"):
        boundary.register(TenantPolicy("a", "", DeploymentProfile.SHARED, 1, "bill-a"))
