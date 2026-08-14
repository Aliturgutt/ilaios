"""ILAIOS-managed credit authorization for paid Video Factory providers.

This module is deliberately provider-neutral. It models the financial authority
boundary that must be satisfied before a paid provider request may leave ILAIOS.
End users never receive or manage provider credentials; provider secrets remain
server-side. Money is represented as integer micro-USD to avoid floating-point
accounting errors.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha256

_MICRO_USD_PER_USD = 1_000_000


class ManagedCreditError(ValueError):
    """Raised when managed-credit authorization or settlement fails closed."""


def _require_text(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ManagedCreditError(f"{name} must not be blank")
    if value != value.strip():
        raise ManagedCreditError(f"{name} must not contain surrounding whitespace")


def usd_to_microusd(value: str | Decimal) -> int:
    """Convert an exact USD amount to integer micro-USD."""

    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ManagedCreditError("USD amount must be numeric") from exc
    if not amount.is_finite() or amount < 0:
        raise ManagedCreditError("USD amount must be finite and non-negative")
    scaled = (amount * _MICRO_USD_PER_USD).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    return int(scaled)


def microusd_to_usd(value: int) -> Decimal:
    """Convert integer micro-USD to an exact Decimal USD amount."""

    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ManagedCreditError("micro-USD amount must be a non-negative integer")
    return Decimal(value) / Decimal(_MICRO_USD_PER_USD)


@dataclass(frozen=True, slots=True)
class ManagedCreditAccount:
    """Tenant/user-scoped ILAIOS credit balance.

    ``available_microusd`` is spendable balance. ``reserved_microusd`` is already
    authorized for in-flight provider work and cannot be spent twice.
    """

    tenant_id: str
    user_id: str
    available_microusd: int
    reserved_microusd: int = 0
    version: int = 1

    def __post_init__(self) -> None:
        _require_text("tenant_id", self.tenant_id)
        _require_text("user_id", self.user_id)
        for name in ("available_microusd", "reserved_microusd"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ManagedCreditError(f"{name} must be a non-negative integer")
        if self.version < 1:
            raise ManagedCreditError("version must be >= 1")

    @property
    def total_microusd(self) -> int:
        return self.available_microusd + self.reserved_microusd


@dataclass(frozen=True, slots=True)
class ProviderCostQuote:
    """Bounded provider-cost quote used before an external paid side effect."""

    provider_name: str
    model_id: str
    estimated_cost_microusd: int
    max_cost_microusd: int

    def __post_init__(self) -> None:
        _require_text("provider_name", self.provider_name)
        _require_text("model_id", self.model_id)
        for name in ("estimated_cost_microusd", "max_cost_microusd"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ManagedCreditError(f"{name} must be a positive integer")
        if self.estimated_cost_microusd > self.max_cost_microusd:
            raise ManagedCreditError("estimated cost cannot exceed maximum authorized cost")


@dataclass(frozen=True, slots=True)
class CreditAuthorization:
    """Immutable authority evidence for one paid provider request."""

    authorization_id: str
    request_id: str
    tenant_id: str
    user_id: str
    provider_name: str
    model_id: str
    reserved_microusd: int
    account_version: int

    def __post_init__(self) -> None:
        for name in (
            "authorization_id",
            "request_id",
            "tenant_id",
            "user_id",
            "provider_name",
            "model_id",
        ):
            _require_text(name, getattr(self, name))
        if len(self.authorization_id) != 64:
            raise ManagedCreditError("authorization_id must be a SHA-256 digest")
        try:
            int(self.authorization_id, 16)
        except ValueError as exc:
            raise ManagedCreditError("authorization_id must be hexadecimal") from exc
        if self.reserved_microusd <= 0:
            raise ManagedCreditError("reserved_microusd must be positive")
        if self.account_version < 1:
            raise ManagedCreditError("account_version must be >= 1")


@dataclass(frozen=True, slots=True)
class CreditAuthorizationOutcome:
    account: ManagedCreditAccount
    authorization: CreditAuthorization


@dataclass(frozen=True, slots=True)
class CreditSettlement:
    """Actual provider-cost settlement bound to an authorization."""

    authorization_id: str
    actual_cost_microusd: int
    released_microusd: int

    def __post_init__(self) -> None:
        _require_text("authorization_id", self.authorization_id)
        for name in ("actual_cost_microusd", "released_microusd"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ManagedCreditError(f"{name} must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class CreditSettlementOutcome:
    account: ManagedCreditAccount
    settlement: CreditSettlement


class ManagedCreditAuthorizer:
    """Pure deterministic reserve/settle authority for provider spend."""

    def authorize(
        self,
        *,
        account: ManagedCreditAccount,
        request_id: str,
        quote: ProviderCostQuote,
    ) -> CreditAuthorizationOutcome:
        _require_text("request_id", request_id)
        if account.available_microusd < quote.max_cost_microusd:
            raise ManagedCreditError("insufficient ILAIOS credits for provider authorization")

        material = "\n".join(
            (
                f"tenant_id={account.tenant_id}",
                f"user_id={account.user_id}",
                f"account_version={account.version}",
                f"request_id={request_id}",
                f"provider_name={quote.provider_name}",
                f"model_id={quote.model_id}",
                f"estimated_cost_microusd={quote.estimated_cost_microusd}",
                f"max_cost_microusd={quote.max_cost_microusd}",
            )
        )
        authorization = CreditAuthorization(
            authorization_id=sha256(material.encode("utf-8")).hexdigest(),
            request_id=request_id,
            tenant_id=account.tenant_id,
            user_id=account.user_id,
            provider_name=quote.provider_name,
            model_id=quote.model_id,
            reserved_microusd=quote.max_cost_microusd,
            account_version=account.version,
        )
        updated_account = replace(
            account,
            available_microusd=account.available_microusd - quote.max_cost_microusd,
            reserved_microusd=account.reserved_microusd + quote.max_cost_microusd,
            version=account.version + 1,
        )
        return CreditAuthorizationOutcome(updated_account, authorization)

    def settle(
        self,
        *,
        account: ManagedCreditAccount,
        authorization: CreditAuthorization,
        actual_cost_microusd: int,
    ) -> CreditSettlementOutcome:
        if isinstance(actual_cost_microusd, bool) or not isinstance(
            actual_cost_microusd, int
        ):
            raise ManagedCreditError("actual_cost_microusd must be an integer")
        if actual_cost_microusd < 0:
            raise ManagedCreditError("actual provider cost must be non-negative")
        if account.tenant_id != authorization.tenant_id:
            raise ManagedCreditError("authorization tenant does not match credit account")
        if account.user_id != authorization.user_id:
            raise ManagedCreditError("authorization user does not match credit account")
        if account.reserved_microusd < authorization.reserved_microusd:
            raise ManagedCreditError("reserved balance does not cover authorization")
        if actual_cost_microusd > authorization.reserved_microusd:
            raise ManagedCreditError("actual provider cost exceeded authorized maximum")

        released = authorization.reserved_microusd - actual_cost_microusd
        updated_account = replace(
            account,
            available_microusd=account.available_microusd + released,
            reserved_microusd=account.reserved_microusd
            - authorization.reserved_microusd,
            version=account.version + 1,
        )
        settlement = CreditSettlement(
            authorization_id=authorization.authorization_id,
            actual_cost_microusd=actual_cost_microusd,
            released_microusd=released,
        )
        return CreditSettlementOutcome(updated_account, settlement)
