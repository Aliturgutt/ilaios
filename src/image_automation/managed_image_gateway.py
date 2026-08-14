"""Managed Image Factory fallback through the shared durable FinOps boundary."""

from __future__ import annotations

from src.video_automation.configuration import VideoAutomationPolicy
from src.video_automation.managed_credit_store import (
    ManagedCreditLedgerStore,
    ProviderSideEffectLedger,
)
from src.video_automation.managed_credits import (
    ManagedCreditAccount,
    ManagedCreditError,
    ProviderCostQuote,
)
from src.video_automation.managed_provider_execution import (
    ManagedPaidVideoExecutionCoordinator,
)
from src.video_automation.models import ProviderRequest, ProviderResult
from src.video_automation.providers import ImageGenerationProvider


class ManagedImageGatewayError(ValueError):
    """Raised before paid image dispatch when governance evidence is insufficient."""


class ManagedImageGateway:
    """Authorize and submit one already-routed paid image request at most once."""

    def __init__(
        self,
        *,
        policy: VideoAutomationPolicy,
        credit_store: ManagedCreditLedgerStore,
    ) -> None:
        self._policy = policy
        self._credit_store = credit_store

    def submit(
        self,
        *,
        account: ManagedCreditAccount,
        request: ProviderRequest,
        quote: ProviderCostQuote,
        routing_decision_id: str,
        provider: ImageGenerationProvider,
    ) -> ProviderResult:
        if request.operation != "generate_image":
            raise ManagedImageGatewayError("managed image gateway requires generate_image")
        if not provider.capabilities.is_paid:
            raise ManagedImageGatewayError("managed image fallback requires paid provider")
        if provider.capabilities.provider_name != request.provider_name:
            raise ManagedImageGatewayError("image provider does not match governed request")

        side_effect_ledger = ProviderSideEffectLedger(self._credit_store)
        try:
            side_effect_ledger.get(request.request_id)
        except ManagedCreditError as exc:
            if str(exc) != "provider side effect does not exist":
                raise ManagedImageGatewayError(
                    "paid image side-effect history could not be validated"
                ) from exc
        else:
            raise ManagedImageGatewayError(
                "paid image request_id already has side-effect history; "
                "create a new governed retry request"
            )

        coordinator = ManagedPaidVideoExecutionCoordinator(
            policy=self._policy,
            store=self._credit_store,
            side_effect_ledger=side_effect_ledger,
        )
        plan = coordinator.authorize(
            account=account,
            request=request,
            quote=quote,
            routing_decision_id=routing_decision_id,
        )
        return coordinator.execute(provider=provider, plan=plan)
