"""Multi-tenant deployment, residency, quota, and abuse boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CloudPolicyError(PermissionError):
    """Raised when cloud isolation or quota policy fails closed."""


class DeploymentProfile(str, Enum):
    SHARED = "shared"
    DEDICATED = "dedicated"
    PRIVATE = "private"


@dataclass(frozen=True, slots=True)
class TenantPolicy:
    tenant_id: str
    region: str
    profile: DeploymentProfile
    request_quota: int
    billing_account: str


class TenantBoundary:
    def __init__(self) -> None:
        self._policies: dict[str, TenantPolicy] = {}
        self._usage: dict[str, int] = {}
        self._blocked: set[str] = set()

    def register(self, policy: TenantPolicy) -> None:
        if (
            not policy.tenant_id
            or not policy.region
            or policy.request_quota < 1
            or not policy.billing_account
        ):
            raise CloudPolicyError("tenant requires identity, region, quota and billing")
        existing = self._policies.get(policy.tenant_id)
        if existing is not None and existing != policy:
            raise CloudPolicyError("tenant policy replacement denied")
        self._policies[policy.tenant_id] = policy

    def authorize(
        self, tenant_id: str, *, resource_tenant: str, region: str
    ) -> DeploymentProfile:
        policy = self._policies.get(tenant_id)
        if policy is None or tenant_id in self._blocked:
            raise CloudPolicyError("unknown or blocked tenant")
        if resource_tenant != tenant_id:
            raise CloudPolicyError("cross-tenant access denied")
        if region != policy.region:
            raise CloudPolicyError("data residency violation")
        usage = self._usage.get(tenant_id, 0)
        if usage >= policy.request_quota:
            raise CloudPolicyError("tenant quota exceeded")
        self._usage[tenant_id] = usage + 1
        return policy.profile

    def block_for_abuse(self, tenant_id: str) -> None:
        self._blocked.add(tenant_id)
