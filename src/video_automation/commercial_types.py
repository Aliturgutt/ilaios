"""Exact-money policy and cost models for ILAIOS Video Factory."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

BPS = 10_000


class CommercialAdmissionError(ValueError):
    """Commercial safety could not be proven; paid execution must stop."""


def require_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CommercialAdmissionError(f"{name} must not be blank")
    if value != value.strip():
        raise CommercialAdmissionError(f"{name} has surrounding whitespace")
    return value


def nonnegative_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CommercialAdmissionError(f"{name} must be a non-negative integer")
    return value


def positive_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CommercialAdmissionError(f"{name} must be a positive integer")
    return value


def rate_bps(name: str, value: int, *, allow_full: bool = False) -> int:
    nonnegative_int(name, value)
    upper = BPS if allow_full else BPS - 1
    if value > upper:
        raise CommercialAdmissionError(f"{name} exceeds basis-point range")
    return value


def digest_material(*parts: str) -> str:
    return sha256("\n".join(parts).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TaxProfile:
    """Jurisdiction-scoped indirect tax; never a global hard-coded rate."""

    profile_id: str
    jurisdiction: str
    tax_rate_bps: int

    def __post_init__(self) -> None:
        require_text("profile_id", self.profile_id)
        require_text("jurisdiction", self.jurisdiction)
        rate_bps("tax_rate_bps", self.tax_rate_bps, allow_full=True)

    @classmethod
    def turkey_general_vat(cls) -> "TaxProfile":
        return cls("TR_GENERAL_VAT_20", "TR", 2_000)


@dataclass(frozen=True, slots=True)
class CommercialPricingPolicy:
    target_margin_bps: int = 4_000
    hard_min_margin_bps: int = 3_000
    contingency_bps: int = 1_000
    payment_fee_rate_bps: int = 0
    payment_fixed_fee_microusd: int = 0
    quote_ttl_seconds: int = 300
    max_provider_attempts: int = 2
    max_repair_generations: int = 1

    def __post_init__(self) -> None:
        for name in (
            "target_margin_bps", "hard_min_margin_bps",
            "contingency_bps", "payment_fee_rate_bps",
        ):
            rate_bps(name, getattr(self, name))
        nonnegative_int(
            "payment_fixed_fee_microusd", self.payment_fixed_fee_microusd
        )
        positive_int("quote_ttl_seconds", self.quote_ttl_seconds)
        positive_int("max_provider_attempts", self.max_provider_attempts)
        nonnegative_int("max_repair_generations", self.max_repair_generations)
        if self.target_margin_bps < self.hard_min_margin_bps:
            raise CommercialAdmissionError(
                "target margin cannot be below hard minimum margin"
            )


@dataclass(frozen=True, slots=True)
class ProviderPricingSnapshot:
    provider_name: str
    model_id: str
    pricing_fingerprint: str
    observed_at_epoch_s: int
    expires_at_epoch_s: int
    estimated_job_cost_microusd: int
    max_job_cost_microusd: int

    def __post_init__(self) -> None:
        require_text("provider_name", self.provider_name)
        require_text("model_id", self.model_id)
        require_text("pricing_fingerprint", self.pricing_fingerprint)
        nonnegative_int("observed_at_epoch_s", self.observed_at_epoch_s)
        positive_int("expires_at_epoch_s", self.expires_at_epoch_s)
        positive_int("estimated_job_cost_microusd", self.estimated_job_cost_microusd)
        positive_int("max_job_cost_microusd", self.max_job_cost_microusd)
        if self.observed_at_epoch_s >= self.expires_at_epoch_s:
            raise CommercialAdmissionError("pricing snapshot lifetime is invalid")
        if self.estimated_job_cost_microusd > self.max_job_cost_microusd:
            raise CommercialAdmissionError("estimated provider cost exceeds maximum")

    def require_fresh(self, now_epoch_s: int) -> None:
        nonnegative_int("now_epoch_s", now_epoch_s)
        if now_epoch_s >= self.expires_at_epoch_s:
            raise CommercialAdmissionError(
                "provider pricing snapshot is stale; requote required"
            )


@dataclass(frozen=True, slots=True)
class VideoCostEnvelope:
    provider_generation_microusd: int
    retry_microusd: int = 0
    repair_microusd: int = 0
    voice_audio_microusd: int = 0
    storage_microusd: int = 0
    egress_microusd: int = 0
    infrastructure_microusd: int = 0
    fx_reserve_microusd: int = 0
    risk_reserve_microusd: int = 0
    other_variable_microusd: int = 0

    def __post_init__(self) -> None:
        positive_int(
            "provider_generation_microusd", self.provider_generation_microusd
        )
        for name in self.__dataclass_fields__:
            if name != "provider_generation_microusd":
                nonnegative_int(name, getattr(self, name))

    @property
    def raw_cost_microusd(self) -> int:
        return sum(getattr(self, name) for name in self.__dataclass_fields__)

    @property
    def external_provider_ceiling_microusd(self) -> int:
        return (
            self.provider_generation_microusd + self.retry_microusd
            + self.repair_microusd + self.voice_audio_microusd
        )

    def protected_cost_microusd(self, contingency_bps: int) -> int:
        rate_bps("contingency_bps", contingency_bps)
        return (
            self.raw_cost_microusd * (BPS + contingency_bps) + BPS - 1
        ) // BPS

    @property
    def fingerprint(self) -> str:
        return digest_material(
            *(f"{name}={getattr(self, name)}" for name in self.__dataclass_fields__)
        )
