from __future__ import annotations

from pathlib import Path

import pytest

from src.video_automation.managed_credit_store import (
    CreditAuthorizationState,
    ManagedCreditLedgerStore,
    ProviderSideEffectLedger,
    ProviderSubmissionState,
    ReconciliationState,
)
from src.video_automation.managed_credits import (
    CreditAuthorizationOutcome,
    ManagedCreditAccount,
    ManagedCreditError,
    ProviderCostQuote,
)
from src.video_automation.models import ProviderRequest


def _account(*, available: int = 2_000_000) -> ManagedCreditAccount:
    return ManagedCreditAccount(
        tenant_id="tenant-001",
        user_id="user-001",
        available_microusd=available,
    )


def _quote(*, maximum: int = 500_000) -> ProviderCostQuote:
    return ProviderCostQuote(
        provider_name="openrouter-video-managed",
        model_id="bytedance/seedance-2.0-fast",
        estimated_cost_microusd=400_000,
        max_cost_microusd=maximum,
    )


def _request(*, request_id: str = "request-001") -> ProviderRequest:
    return ProviderRequest(
        request_id=request_id,
        job_id="job-001",
        provider_name="openrouter-video-managed",
        operation="video.generate",
        payload={
            "model_id": "bytedance/seedance-2.0-fast",
            "request_count": 1,
            "items_json": "[]",
        },
    )


def _reserve(
    store: ManagedCreditLedgerStore, *, request_id: str = "request-001"
) -> CreditAuthorizationOutcome:
    return store.reserve(
        account=_account(),
        request_id=request_id,
        routing_decision_id="route-001",
        quote=_quote(),
    )


def test_reservation_survives_store_restart(tmp_path: Path) -> None:
    store = ManagedCreditLedgerStore(tmp_path)
    outcome = _reserve(store)

    restarted = ManagedCreditLedgerStore(tmp_path)
    account = restarted.get_account(tenant_id="tenant-001", user_id="user-001")
    authorization = restarted.get_authorization(outcome.authorization.authorization_id)

    assert account.available_microusd == 1_500_000
    assert account.reserved_microusd == 500_000
    assert authorization.state is CreditAuthorizationState.RESERVED
    assert authorization.routing_decision_id == "route-001"


def test_same_request_reservation_is_idempotent_and_does_not_double_charge(
    tmp_path: Path,
) -> None:
    store = ManagedCreditLedgerStore(tmp_path)
    first = _reserve(store)
    second = _reserve(store)

    assert second.authorization.authorization_id == first.authorization.authorization_id
    assert second.account.available_microusd == 1_500_000
    assert second.account.reserved_microusd == 500_000


def test_request_id_cannot_be_rebound_to_different_financial_material(tmp_path: Path) -> None:
    store = ManagedCreditLedgerStore(tmp_path)
    _reserve(store)

    with pytest.raises(ManagedCreditError, match="different authorization material"):
        store.reserve(
            account=_account(),
            request_id="request-001",
            routing_decision_id="route-002",
            quote=_quote(),
        )


def test_settlement_is_persistent_and_identical_duplicate_is_idempotent(
    tmp_path: Path,
) -> None:
    store = ManagedCreditLedgerStore(tmp_path)
    authorized = _reserve(store)

    first = store.settle(
        authorization_id=authorized.authorization.authorization_id,
        actual_cost_microusd=350_000,
        provider_job_id="provider-job-001",
    )
    second = store.settle(
        authorization_id=authorized.authorization.authorization_id,
        actual_cost_microusd=350_000,
        provider_job_id="provider-job-001",
    )

    assert first.account.available_microusd == 1_650_000
    assert first.account.reserved_microusd == 0
    assert second.account == first.account
    persistent = store.get_authorization(authorized.authorization.authorization_id)
    assert persistent.state is CreditAuthorizationState.SETTLED
    assert persistent.actual_cost_microusd == 350_000
    assert persistent.provider_job_id == "provider-job-001"


def test_duplicate_settlement_with_different_cost_is_rejected(tmp_path: Path) -> None:
    store = ManagedCreditLedgerStore(tmp_path)
    authorized = _reserve(store)
    store.settle(
        authorization_id=authorized.authorization.authorization_id,
        actual_cost_microusd=350_000,
        provider_job_id="provider-job-001",
    )

    with pytest.raises(ManagedCreditError, match="already settled differently"):
        store.settle(
            authorization_id=authorized.authorization.authorization_id,
            actual_cost_microusd=360_000,
            provider_job_id="provider-job-001",
        )


def test_cost_above_authorized_maximum_persists_policy_violation(tmp_path: Path) -> None:
    store = ManagedCreditLedgerStore(tmp_path)
    authorized = _reserve(store)

    with pytest.raises(ManagedCreditError, match="exceeded authorized maximum"):
        store.settle(
            authorization_id=authorized.authorization.authorization_id,
            actual_cost_microusd=500_001,
            provider_job_id="provider-job-001",
        )

    persistent = store.get_authorization(authorized.authorization.authorization_id)
    assert persistent.state is CreditAuthorizationState.COST_POLICY_VIOLATION
    assert persistent.actual_cost_microusd == 500_001
    account = store.get_account(tenant_id="tenant-001", user_id="user-001")
    assert account.reserved_microusd == 500_000


def test_unused_reservation_can_be_released_exactly_once(tmp_path: Path) -> None:
    store = ManagedCreditLedgerStore(tmp_path)
    authorized = _reserve(store)

    released = store.release(authorization_id=authorized.authorization.authorization_id)
    duplicate = store.release(authorization_id=authorized.authorization.authorization_id)

    assert released.available_microusd == 2_000_000
    assert released.reserved_microusd == 0
    assert duplicate == released
    assert (
        store.get_authorization(authorized.authorization.authorization_id).state
        is CreditAuthorizationState.RELEASED
    )


def test_ambiguous_submission_blocks_second_paid_post_until_reconciliation(
    tmp_path: Path,
) -> None:
    store = ManagedCreditLedgerStore(tmp_path)
    authorized = _reserve(store)
    ledger = ProviderSideEffectLedger(store)
    request = _request()

    prepared = ledger.prepare(
        request=request,
        authorization=authorized.authorization,
        routing_decision_id="route-001",
    )
    assert prepared.submission_state is ProviderSubmissionState.SUBMITTING

    ambiguous = ledger.ambiguous(
        request_id=request.request_id,
        observed_status="transport_error",
    )
    assert ambiguous.submission_state is ProviderSubmissionState.AMBIGUOUS
    assert ambiguous.reconciliation_state is ReconciliationState.PENDING

    with pytest.raises(ManagedCreditError, match="reconcile instead of redispatch"):
        ledger.prepare(
            request=request,
            authorization=authorized.authorization,
            routing_decision_id="route-001",
        )

    reconciled = ledger.reconcile(
        request_id=request.request_id,
        external_job_id="provider-job-001",
        observed_status="pending",
    )
    assert reconciled.submission_state is ProviderSubmissionState.ACCEPTED
    assert reconciled.external_job_id == "provider-job-001"
    assert reconciled.reconciliation_state is ReconciliationState.RECONCILED


def test_provider_side_effect_identity_cannot_be_mutated(tmp_path: Path) -> None:
    store = ManagedCreditLedgerStore(tmp_path)
    authorized = _reserve(store)
    ledger = ProviderSideEffectLedger(store)
    request = _request()
    ledger.prepare(
        request=request,
        authorization=authorized.authorization,
        routing_decision_id="route-001",
    )
    ledger.failed(request_id=request.request_id, observed_status="http_400")

    changed = ProviderRequest(
        request_id=request.request_id,
        job_id=request.job_id,
        provider_name=request.provider_name,
        operation=request.operation,
        payload={
            "model_id": "bytedance/seedance-2.0-fast",
            "request_count": 1,
            "items_json": "[{\"prompt\":\"changed\"}]",
        },
    )
    with pytest.raises(ManagedCreditError, match="different provider side effect"):
        ledger.prepare(
            request=changed,
            authorization=authorized.authorization,
            routing_decision_id="route-001",
        )
