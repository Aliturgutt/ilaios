"""Governed paid-provider execution through durable ILAIOS-managed credits."""

from __future__ import annotations

from dataclasses import dataclass

from .configuration import ExecutionMode, VideoAutomationPolicy
from .managed_credit_store import (
    ManagedCreditLedgerStore,
    ProviderSideEffectLedger,
)
from .managed_credits import (
    CreditAuthorization,
    ManagedCreditAccount,
    ProviderCostQuote,
)
from .models import ProviderRequest, ProviderResult
from .providers import Provider


class ManagedPaidVideoExecutionError(ValueError):
    """Raised when paid video execution lacks required ILAIOS authority."""


@dataclass(frozen=True, slots=True)
class ManagedPaidVideoExecutionPlan:
    """Persistently credit-reserved provider request ready for one side effect."""

    account: ManagedCreditAccount
    authorization: CreditAuthorization
    routing_decision_id: str
    request: ProviderRequest


class ManagedPaidVideoExecutionCoordinator:
    """Bind policy + durable tenant credits to the existing provider boundary."""

    def __init__(
        self,
        *,
        policy: VideoAutomationPolicy,
        store: ManagedCreditLedgerStore,
        side_effect_ledger: ProviderSideEffectLedger | None = None,
    ) -> None:
        if policy.mode is not ExecutionMode.PRODUCTION:
            raise ManagedPaidVideoExecutionError(
                "managed paid provider execution requires PRODUCTION mode"
            )
        self._policy = policy
        self._store = store
        self._side_effect_ledger = side_effect_ledger or ProviderSideEffectLedger(store)

    def authorize(
        self,
        *,
        account: ManagedCreditAccount,
        request: ProviderRequest,
        quote: ProviderCostQuote,
        routing_decision_id: str,
    ) -> ManagedPaidVideoExecutionPlan:
        """Persist credit reservation and bind canonical routing authority."""

        if quote.provider_name != request.provider_name:
            raise ManagedPaidVideoExecutionError(
                "provider quote does not match provider request"
            )
        model_id = request.payload.get("model_id")
        if not isinstance(model_id, str) or model_id != quote.model_id:
            raise ManagedPaidVideoExecutionError(
                "provider quote model does not match provider request"
            )
        if not routing_decision_id or routing_decision_id != routing_decision_id.strip():
            raise ManagedPaidVideoExecutionError(
                "paid provider execution requires canonical routing_decision_id"
            )
        if not self._policy.can_use_provider(request.provider_name, is_paid=True):
            raise ManagedPaidVideoExecutionError(
                "paid provider is not permitted by Video Automation policy"
            )
        if not self._policy.requires_approval_for_paid_provider():
            raise ManagedPaidVideoExecutionError(
                "managed paid execution requires BEFORE_PAID_PROVIDER authority boundary"
            )

        outcome = self._store.reserve(
            account=account,
            request_id=request.request_id,
            routing_decision_id=routing_decision_id,
            quote=quote,
        )
        payload = dict(request.payload)
        payload.update(
            {
                "credit_authorization_id": outcome.authorization.authorization_id,
                "credit_reserved_microusd": outcome.authorization.reserved_microusd,
                "tenant_id": account.tenant_id,
                "user_id": account.user_id,
                "routing_decision_id": routing_decision_id,
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
            routing_decision_id=routing_decision_id,
            request=authorized_request,
        )

    def execute(
        self,
        *,
        provider: Provider,
        plan: ManagedPaidVideoExecutionPlan,
    ) -> ProviderResult:
        """Execute at most one paid POST for the durable request identity.

        The side-effect ledger is moved to SUBMITTING before the provider call.
        A transport exception or transport-level failure is AMBIGUOUS rather than
        retryable: reconciliation must establish whether the provider created a
        job before another paid POST may ever be considered.
        """

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

        self._side_effect_ledger.prepare(
            request=plan.request,
            authorization=plan.authorization,
            routing_decision_id=plan.routing_decision_id,
        )
        try:
            result = provider.execute(plan.request)
        except Exception as exc:  # noqa: BLE001
            self._side_effect_ledger.ambiguous(
                request_id=plan.request.request_id,
                observed_status=f"provider exception: {exc.__class__.__name__}",
            )
            raise ManagedPaidVideoExecutionError(
                "paid provider submission became ambiguous; reconcile before redispatch"
            ) from exc

        if result.success:
            if result.external_id is None:
                self._side_effect_ledger.ambiguous(
                    request_id=plan.request.request_id,
                    observed_status="success response missing external job id",
                )
                raise ManagedPaidVideoExecutionError(
                    "paid provider response is ambiguous without external job id"
                )
            self._side_effect_ledger.accepted(
                request_id=plan.request.request_id,
                external_job_id=result.external_id,
            )
            return result

        if _is_ambiguous_provider_failure(result):
            self._side_effect_ledger.ambiguous(
                request_id=plan.request.request_id,
                observed_status=result.error_code or "transport_error",
            )
        else:
            self._side_effect_ledger.failed(
                request_id=plan.request.request_id,
                observed_status=result.error_code or "provider_rejected",
            )
        return result


def _is_ambiguous_provider_failure(result: ProviderResult) -> bool:
    """Return whether failure evidence cannot prove the POST was not accepted."""

    if result.success:
        return False
    normalized = (result.error_code or "").strip().lower()
    return normalized in {
        "transport_error",
        "timeout",
        "connection_error",
        "network_error",
        "response_lost",
    }
