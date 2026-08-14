from __future__ import annotations

from decimal import Decimal

import pytest

from src.video_automation.managed_credits import (
    ManagedCreditAccount,
    ManagedCreditAuthorizer,
    ManagedCreditError,
    ProviderCostQuote,
    microusd_to_usd,
    usd_to_microusd,
)


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


def test_exact_usd_micro_usd_conversion_avoids_float_accounting() -> None:
    assert usd_to_microusd("0.121") == 121_000
    assert usd_to_microusd(Decimal("1.234567")) == 1_234_567
    assert microusd_to_usd(1_234_567) == Decimal("1.234567")


def test_authorization_reserves_maximum_cost_before_provider_execution() -> None:
    outcome = ManagedCreditAuthorizer().authorize(
        account=_account(),
        request_id="request-001",
        quote=_quote(),
    )

    assert outcome.account.available_microusd == 1_500_000
    assert outcome.account.reserved_microusd == 500_000
    assert outcome.account.version == 2
    assert outcome.authorization.reserved_microusd == 500_000
    assert len(outcome.authorization.authorization_id) == 64


def test_same_authorization_material_is_deterministic() -> None:
    authorizer = ManagedCreditAuthorizer()
    first = authorizer.authorize(
        account=_account(), request_id="request-001", quote=_quote()
    )
    second = authorizer.authorize(
        account=_account(), request_id="request-001", quote=_quote()
    )
    assert first.authorization.authorization_id == second.authorization.authorization_id


def test_insufficient_credits_fail_before_any_paid_authority_exists() -> None:
    with pytest.raises(ManagedCreditError, match="insufficient ILAIOS credits"):
        ManagedCreditAuthorizer().authorize(
            account=_account(available=100_000),
            request_id="request-001",
            quote=_quote(),
        )


def test_settlement_charges_actual_cost_and_releases_unused_reservation() -> None:
    authorizer = ManagedCreditAuthorizer()
    authorized = authorizer.authorize(
        account=_account(),
        request_id="request-001",
        quote=_quote(),
    )
    settled = authorizer.settle(
        account=authorized.account,
        authorization=authorized.authorization,
        actual_cost_microusd=350_000,
    )

    assert settled.settlement.actual_cost_microusd == 350_000
    assert settled.settlement.released_microusd == 150_000
    assert settled.account.available_microusd == 1_650_000
    assert settled.account.reserved_microusd == 0
    assert settled.account.total_microusd == 1_650_000


def test_provider_cost_above_reserved_maximum_fails_closed() -> None:
    authorizer = ManagedCreditAuthorizer()
    authorized = authorizer.authorize(
        account=_account(),
        request_id="request-001",
        quote=_quote(),
    )
    with pytest.raises(ManagedCreditError, match="exceeded authorized maximum"):
        authorizer.settle(
            account=authorized.account,
            authorization=authorized.authorization,
            actual_cost_microusd=500_001,
        )


def test_cross_tenant_or_cross_user_settlement_is_rejected() -> None:
    authorizer = ManagedCreditAuthorizer()
    authorized = authorizer.authorize(
        account=_account(),
        request_id="request-001",
        quote=_quote(),
    )
    wrong_tenant = ManagedCreditAccount(
        tenant_id="tenant-002",
        user_id="user-001",
        available_microusd=1_500_000,
        reserved_microusd=500_000,
        version=2,
    )
    with pytest.raises(ManagedCreditError, match="tenant"):
        authorizer.settle(
            account=wrong_tenant,
            authorization=authorized.authorization,
            actual_cost_microusd=100_000,
        )
