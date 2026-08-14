"""Governed paid-provider execution through ILAIOS-managed credits."""

from __future__ import annotations

from dataclasses import dataclass

from .configuration import ExecutionMode, VideoAutomationPolicy
from .managed_credits import (
    CreditAuthorization,
    ManagedCreditAccount,
    ManagedCreditAuthorizer,
    ProviderCostQuote,
)
from .models import ProviderRequest, ProviderResult
from .providers import Provider


class ManagedPaidVideoExecutionError(ValueError):
    """Raised when paid video execution lacks required ILAIOS authority."""


@dataclass(frozen=True, slots=True)
class ManagedPaidVideoExecutionPlan:
    """Credit-reserved provider request ready for one external side effect."""

    account: ManagedCreditAccount
    authorization: CreditAuthorization
    request: ProviderRequest


class ManagedPaidVideoExecutionCoordinator:
    """Bind policy + tenant credits to the existing provider boundary."""

    def __init__(
        self,
        *,
        policy: VideoAutomationPolicy,
        authorizer: ManagedCreditAuthorizer | None = None,
    ) -> None:
        if policy.mode is not ExecutionMode.PRODUCTION:
            raise ManagedPaidVideoExecutionError(
                "managed paid provider execution requires PRODUCTION mode"
            )
        self._policy = policy
        self._authorizer = authorizer or ManagedCreditAuthorizer()

    def authorize(
        self,
        *,
        account: ManagedCreditAccount,
        request: ProviderRequest,
        quote: ProviderCostQuote,
    ) -> ManagedPaidVideoExecutionPlan:
        """Reserve ILAIOS credits and bind authority into the provider request."""

        if quote.provider_name != request.provider_name:
            raise ManagedPaidVideoExecutionError(
                "provider quote does not match provider request"
            )
        model_id = request.payload.get("model_id")
        if not isinstance(model_id, str) or model_id != quote.model_id:
            raise ManagedPaidVideoExecutionError(
                "provider quote model does not match provider request"
            )
        if not self._policy.can_use_provider(request.provider_name, is_paid=True):
            raise ManagedPaidVideoExecutionError(
                "paid provider is not permitted by Video Automation policy"
            )
        if not self._policy.requires_approval_for_paid_provider():
            raise ManagedPaidVideoExecutionError(
                "managed paid execution requires BEFORE_PAID_PROVIDER authority boundary"
            )

        outcome = self._authorizer.authorize(
            account=account,
            request_id=request.request_id,
            quote=quote,
        )
        payload = dict(request.payload)
        payload.update(
            {
                "credit_authorization_id": outcome.authorization.authorization_id,
                "credit_reserved_microusd": outcome.authorization.reserved_microusd,
                "tenant_id": account.tenant_id,
                "user_id": account.user_id,
            }
        )
        authorized_request = ProviderRequest(
            request_id=request.request_id,
            job_id=request.job_id,
            provider_name=request.provider_name,
            operation=request.operation,
            payload=payload,
        )
        return ManagedPaidVideoExecutionPlan(
            account=outcome.account,
            authorization=outcome.authorization,
            request=authorized_request,
        )

    def execute(
        self,
        *,
        provider: Provider,
        plan: ManagedPaidVideoExecutionPlan,
    ) -> ProviderResult:
        """Execute exactly one already-authorized provider request."""

        capabilities = provider.capabilities
        if not capabilities.is_paid:
            raise ManagedPaidVideoExecutionError(
                "managed paid execution requires a paid provider capability"
            )
        if capabilities.provider_name != plan.request.provider_name:
            raise ManagedPaidVideoExecutionError(
                "provider does not match authorized request"
            )
        if not self._policy.can_use_provider(
            capabilities.provider_name,
            is_paid=True,
        ):
            raise ManagedPaidVideoExecutionError(
                "provider became disallowed before execution"
            )
        return provider.execute(plan.request)
