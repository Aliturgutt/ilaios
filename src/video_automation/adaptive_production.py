"""Adaptive shot production planning for the canonical ILAIOS Video Factory.

The user-facing finished-product duration is intentionally decoupled from a
provider's individual clip duration.  This module plans short visual units,
models live provider capabilities/pricing, and routes each shot under an
explicit fail-closed budget policy.

It is deliberately provider-neutral and side-effect free.  Network discovery,
provider execution, editing, QA, and billing reconciliation remain in their
existing governed layers.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from math import ceil
from types import MappingProxyType


class AdaptiveProductionError(ValueError):
    """Raised when a safe adaptive production plan cannot be formed."""


class ShotRole(Enum):
    """Editorial role used to choose duration, quality, and routing priority."""

    ESTABLISHING = "establishing"
    CINEMATIC = "cinematic"
    HERO = "hero"
    DIALOGUE = "dialogue"
    ACTION = "action"
    REACTION = "reaction"
    INSERT = "insert"
    TRANSITION = "transition"


class ProductionLane(Enum):
    """Internal routing lane; users do not need to select a provider/model."""

    FREE = "free"
    STANDARD = "standard"
    PREMIUM = "premium"


@dataclass(frozen=True, slots=True)
class ShotDurationWindow:
    minimum_seconds: int
    target_seconds: int
    maximum_seconds: int

    def __post_init__(self) -> None:
        if self.minimum_seconds <= 0:
            raise AdaptiveProductionError("minimum_seconds must be positive")
        if not self.minimum_seconds <= self.target_seconds <= self.maximum_seconds:
            raise AdaptiveProductionError("target_seconds must be inside duration bounds")


_ROLE_WINDOWS: Mapping[ShotRole, ShotDurationWindow] = MappingProxyType(
    {
        ShotRole.ESTABLISHING: ShotDurationWindow(5, 6, 8),
        ShotRole.CINEMATIC: ShotDurationWindow(4, 5, 6),
        ShotRole.HERO: ShotDurationWindow(4, 6, 8),
        ShotRole.DIALOGUE: ShotDurationWindow(5, 7, 10),
        ShotRole.ACTION: ShotDurationWindow(3, 4, 5),
        ShotRole.REACTION: ShotDurationWindow(2, 3, 4),
        ShotRole.INSERT: ShotDurationWindow(2, 3, 4),
        ShotRole.TRANSITION: ShotDurationWindow(2, 3, 4),
    }
)


_ROLE_IMPORTANCE: Mapping[ShotRole, int] = MappingProxyType(
    {
        ShotRole.HERO: 100,
        ShotRole.DIALOGUE: 90,
        ShotRole.ACTION: 80,
        ShotRole.ESTABLISHING: 70,
        ShotRole.CINEMATIC: 60,
        ShotRole.REACTION: 50,
        ShotRole.INSERT: 35,
        ShotRole.TRANSITION: 10,
    }
)


@dataclass(frozen=True, slots=True)
class AdaptiveShot:
    """One provider-neutral visual unit in an adaptive production plan."""

    sequence: int
    role: ShotRole
    duration_seconds: int
    importance: int
    requires_native_audio: bool = False
    requires_first_frame: bool = False
    requires_last_frame: bool = False
    requires_input_reference: bool = False

    def __post_init__(self) -> None:
        if self.sequence <= 0:
            raise AdaptiveProductionError("shot sequence must be positive")
        if self.duration_seconds <= 0:
            raise AdaptiveProductionError("shot duration must be positive")
        if not 0 <= self.importance <= 100:
            raise AdaptiveProductionError("shot importance must be between 0 and 100")


@dataclass(frozen=True, slots=True)
class AdaptiveShotPlan:
    """Ordered short-shot plan for one requested finished-product duration."""

    requested_duration_seconds: int
    shots: tuple[AdaptiveShot, ...]

    def __post_init__(self) -> None:
        if self.requested_duration_seconds <= 0:
            raise AdaptiveProductionError("requested duration must be positive")
        if not self.shots:
            raise AdaptiveProductionError("adaptive shot plan must contain shots")
        expected_sequences = tuple(range(1, len(self.shots) + 1))
        if tuple(shot.sequence for shot in self.shots) != expected_sequences:
            raise AdaptiveProductionError("shot sequences must be contiguous from one")
        if self.generated_duration_seconds != self.requested_duration_seconds:
            raise AdaptiveProductionError(
                "adaptive shot durations must exactly equal requested duration"
            )

    @property
    def generated_duration_seconds(self) -> int:
        return sum(shot.duration_seconds for shot in self.shots)


class AdaptiveShotPlanner:
    """Plan editorially useful short clips without limiting final video length."""

    def __init__(
        self,
        *,
        absolute_min_seconds: int = 2,
        absolute_max_seconds: int = 12,
    ) -> None:
        if absolute_min_seconds <= 0:
            raise AdaptiveProductionError("absolute_min_seconds must be positive")
        if absolute_max_seconds < absolute_min_seconds:
            raise AdaptiveProductionError(
                "absolute_max_seconds must be >= absolute_min_seconds"
            )
        self._absolute_min = absolute_min_seconds
        self._absolute_max = absolute_max_seconds

    def plan(
        self,
        requested_duration_seconds: int,
        *,
        roles: Sequence[ShotRole] | None = None,
        supported_durations: Sequence[int] | None = None,
    ) -> AdaptiveShotPlan:
        """Return an exact-duration plan using provider-compatible clips when supplied."""

        if requested_duration_seconds <= 0:
            raise AdaptiveProductionError("requested_duration_seconds must be positive")
        allowed = self._allowed_durations(supported_durations)
        if requested_duration_seconds < min(allowed):
            raise AdaptiveProductionError(
                "requested duration is shorter than the minimum admissible shot"
            )

        role_sequence = tuple(roles) if roles is not None else ()
        if role_sequence:
            durations = self._partition_for_roles(
                requested_duration_seconds,
                role_sequence,
                allowed,
            )
            resolved_roles = role_sequence
        else:
            durations = self._partition_generic(requested_duration_seconds, allowed)
            resolved_roles = self._default_roles(len(durations))

        shots = tuple(
            AdaptiveShot(
                sequence=index,
                role=role,
                duration_seconds=duration,
                importance=_ROLE_IMPORTANCE[role],
                requires_native_audio=role is ShotRole.DIALOGUE,
                requires_first_frame=index > 1,
                requires_last_frame=index < len(durations),
                requires_input_reference=role
                in {ShotRole.HERO, ShotRole.DIALOGUE, ShotRole.ACTION},
            )
            for index, (role, duration) in enumerate(
                zip(resolved_roles, durations, strict=True),
                start=1,
            )
        )
        return AdaptiveShotPlan(requested_duration_seconds, shots)

    def _allowed_durations(self, values: Sequence[int] | None) -> tuple[int, ...]:
        if values is None:
            return tuple(range(self._absolute_min, self._absolute_max + 1))
        normalized = tuple(
            sorted(
                {
                    int(value)
                    for value in values
                    if self._absolute_min <= int(value) <= self._absolute_max
                }
            )
        )
        if not normalized:
            raise AdaptiveProductionError(
                "provider exposes no duration inside adaptive shot bounds"
            )
        return normalized

    def _partition_generic(self, total: int, allowed: tuple[int, ...]) -> tuple[int, ...]:
        preferred = tuple(value for value in allowed if 4 <= value <= 6)
        target = min(preferred or allowed, key=lambda value: (abs(value - 5), value))
        count_hint = max(1, round(total / target))
        solution = _exact_duration_partition(total, allowed, count_hint=count_hint)
        if solution is None:
            raise AdaptiveProductionError(
                "requested duration cannot be exactly partitioned by provider durations"
            )
        return solution

    def _partition_for_roles(
        self,
        total: int,
        roles: tuple[ShotRole, ...],
        allowed: tuple[int, ...],
    ) -> tuple[int, ...]:
        if not roles:
            raise AdaptiveProductionError("roles must not be empty")
        candidates: list[tuple[int, ...]] = []
        for role in roles:
            window = _ROLE_WINDOWS[role]
            role_allowed = tuple(
                value
                for value in allowed
                if window.minimum_seconds <= value <= window.maximum_seconds
            )
            candidates.append(role_allowed or allowed)
        solution = _exact_role_partition(total, tuple(candidates), roles)
        if solution is None:
            raise AdaptiveProductionError(
                "requested duration cannot be exactly partitioned for requested shot roles"
            )
        return solution

    @staticmethod
    def _default_roles(count: int) -> tuple[ShotRole, ...]:
        if count == 1:
            return (ShotRole.HERO,)
        roles = [ShotRole.CINEMATIC for _ in range(count)]
        roles[0] = ShotRole.ESTABLISHING
        roles[-1] = ShotRole.HERO
        return tuple(roles)


def _exact_duration_partition(
    total: int,
    allowed: tuple[int, ...],
    *,
    count_hint: int,
) -> tuple[int, ...] | None:
    """Find an exact sum while preferring 4-6 second clips and a target shot count."""

    minimum = min(allowed)
    maximum = max(allowed)
    min_count = max(1, ceil(total / maximum))
    max_count = total // minimum
    candidate_counts = sorted(
        range(min_count, max_count + 1),
        key=lambda count: (abs(count - count_hint), count),
    )
    preference = tuple(
        sorted(allowed, key=lambda value: (0 if 4 <= value <= 6 else 1, abs(value - 5), value))
    )
    for count in candidate_counts:
        result = _search_exact_sum(total, count, preference)
        if result is not None:
            return result
    return None


def _search_exact_sum(
    total: int,
    count: int,
    preference: tuple[int, ...],
) -> tuple[int, ...] | None:
    minimum = min(preference)
    maximum = max(preference)

    def visit(remaining: int, slots: int) -> tuple[int, ...] | None:
        if slots == 0:
            return () if remaining == 0 else None
        if remaining < slots * minimum or remaining > slots * maximum:
            return None
        for duration in preference:
            tail = visit(remaining - duration, slots - 1)
            if tail is not None:
                return (duration, *tail)
        return None

    return visit(total, count)


def _exact_role_partition(
    total: int,
    candidates: tuple[tuple[int, ...], ...],
    roles: tuple[ShotRole, ...],
) -> tuple[int, ...] | None:
    def visit(index: int, remaining: int) -> tuple[int, ...] | None:
        if index == len(candidates):
            return () if remaining == 0 else None
        remaining_slots = candidates[index + 1 :]
        minimum_tail = sum(min(values) for values in remaining_slots)
        maximum_tail = sum(max(values) for values in remaining_slots)
        role = roles[index]
        target = _ROLE_WINDOWS[role].target_seconds
        ordered = sorted(candidates[index], key=lambda value: (abs(value - target), value))
        for duration in ordered:
            next_remaining = remaining - duration
            if next_remaining < minimum_tail or next_remaining > maximum_tail:
                continue
            tail = visit(index + 1, next_remaining)
            if tail is not None:
                return (duration, *tail)
        return None

    return visit(0, total)


@dataclass(frozen=True, slots=True)
class VideoModelCapability:
    """Live provider-model capability snapshot used for shot-level routing."""

    provider_id: str
    model_id: str
    supported_durations: tuple[int, ...]
    supported_resolutions: tuple[str, ...]
    supported_aspect_ratios: tuple[str, ...]
    supported_frame_images: tuple[str, ...] = ()
    supports_audio: bool = False
    supports_input_references: bool = False
    pricing_skus: Mapping[str, Decimal] = field(default_factory=dict)
    quality_rank: int = 50

    def __post_init__(self) -> None:
        _require_text("provider_id", self.provider_id)
        _require_text("model_id", self.model_id)
        if not self.supported_durations:
            raise AdaptiveProductionError("supported_durations must not be empty")
        if any(value <= 0 for value in self.supported_durations):
            raise AdaptiveProductionError("supported durations must be positive")
        if not 0 <= self.quality_rank <= 100:
            raise AdaptiveProductionError("quality_rank must be between 0 and 100")
        normalized: dict[str, Decimal] = {}
        for key, value in self.pricing_skus.items():
            _require_text("pricing SKU", key)
            cost = _decimal_price(value)
            if cost is None:
                raise AdaptiveProductionError(f"invalid pricing value for {key}")
            normalized[key] = cost
        object.__setattr__(
            self,
            "supported_durations",
            tuple(sorted(set(self.supported_durations))),
        )
        object.__setattr__(self, "pricing_skus", MappingProxyType(normalized))

    @property
    def is_explicitly_zero_cost(self) -> bool:
        return bool(self.pricing_skus) and all(
            value == Decimal("0") for value in self.pricing_skus.values()
        )

    def supports_shot(
        self,
        shot: AdaptiveShot,
        *,
        resolution: str,
        aspect_ratio: str,
    ) -> bool:
        if shot.duration_seconds not in self.supported_durations:
            return False
        if self.supported_resolutions and resolution not in self.supported_resolutions:
            return False
        if self.supported_aspect_ratios and aspect_ratio not in self.supported_aspect_ratios:
            return False
        if shot.requires_native_audio and not self.supports_audio:
            return False
        if shot.requires_first_frame and "first_frame" not in self.supported_frame_images:
            return False
        if shot.requires_last_frame and "last_frame" not in self.supported_frame_images:
            return False
        if shot.requires_input_reference and not self.supports_input_references:
            return False
        return True

    def estimated_cost_usd(self, *, duration_seconds: int, resolution: str) -> Decimal | None:
        if self.is_explicitly_zero_cost:
            return Decimal("0")
        resolution_key = f"per-video-second-{resolution}"
        if resolution_key in self.pricing_skus:
            return self.pricing_skus[resolution_key] * Decimal(duration_seconds)
        if "per-video-second" in self.pricing_skus:
            return self.pricing_skus["per-video-second"] * Decimal(duration_seconds)
        return None


@dataclass(frozen=True, slots=True)
class ShotRoutingPolicy:
    """Fail-closed spend policy for shot-level provider selection."""

    allow_paid: bool = False
    max_total_provider_cost_usd: Decimal = Decimal("0")
    max_cost_per_shot_usd: Decimal = Decimal("0")
    prefer_zero_cost: bool = True
    premium_importance_threshold: int = 85
    credits_per_usd: Decimal = Decimal("100")

    def __post_init__(self) -> None:
        for name in (
            "max_total_provider_cost_usd",
            "max_cost_per_shot_usd",
            "credits_per_usd",
        ):
            value = getattr(self, name)
            if value < Decimal("0"):
                raise AdaptiveProductionError(f"{name} must not be negative")
        if self.credits_per_usd <= Decimal("0"):
            raise AdaptiveProductionError("credits_per_usd must be positive")
        if not 0 <= self.premium_importance_threshold <= 100:
            raise AdaptiveProductionError(
                "premium_importance_threshold must be between 0 and 100"
            )
        if self.allow_paid and (
            self.max_total_provider_cost_usd <= Decimal("0")
            or self.max_cost_per_shot_usd <= Decimal("0")
        ):
            raise AdaptiveProductionError(
                "paid routing requires explicit positive total and per-shot hard caps"
            )


@dataclass(frozen=True, slots=True)
class RoutedShot:
    shot: AdaptiveShot
    provider_id: str
    model_id: str
    lane: ProductionLane
    estimated_cost_usd: Decimal
    estimated_credits: Decimal


@dataclass(frozen=True, slots=True)
class ShotRoutingPlan:
    routes: tuple[RoutedShot, ...]
    generated_seconds: int
    estimated_provider_cost_usd: Decimal
    estimated_credits: Decimal


class AdaptiveProviderRouter:
    """Choose the cheapest capable model per shot while protecting hard spend caps."""

    def route(
        self,
        shot_plan: AdaptiveShotPlan,
        capabilities: Sequence[VideoModelCapability],
        policy: ShotRoutingPolicy,
        *,
        resolution: str,
        aspect_ratio: str,
    ) -> ShotRoutingPlan:
        if not capabilities:
            raise AdaptiveProductionError("no video model capabilities are available")
        routes: list[RoutedShot] = []
        running_cost = Decimal("0")
        for shot in shot_plan.shots:
            candidates = [
                capability
                for capability in capabilities
                if capability.supports_shot(
                    shot,
                    resolution=resolution,
                    aspect_ratio=aspect_ratio,
                )
            ]
            if not candidates:
                raise AdaptiveProductionError(
                    f"no model satisfies shot {shot.sequence} capability requirements"
                )
            zero_cost = [candidate for candidate in candidates if candidate.is_explicitly_zero_cost]
            chosen: VideoModelCapability | None = None
            estimated = Decimal("0")
            lane = ProductionLane.FREE
            if zero_cost:
                chosen = max(zero_cost, key=lambda item: (item.quality_rank, item.model_id))
            elif policy.allow_paid:
                priced: list[tuple[Decimal, VideoModelCapability]] = []
                for candidate in candidates:
                    cost = candidate.estimated_cost_usd(
                        duration_seconds=shot.duration_seconds,
                        resolution=resolution,
                    )
                    if cost is None or cost > policy.max_cost_per_shot_usd:
                        continue
                    priced.append((cost, candidate))
                if priced:
                    if shot.importance >= policy.premium_importance_threshold:
                        estimated, chosen = min(
                            priced,
                            key=lambda item: (-item[1].quality_rank, item[0], item[1].model_id),
                        )
                        lane = ProductionLane.PREMIUM
                    else:
                        estimated, chosen = min(
                            priced,
                            key=lambda item: (item[0], -item[1].quality_rank, item[1].model_id),
                        )
                        lane = ProductionLane.STANDARD
            if chosen is None:
                raise AdaptiveProductionError(
                    f"shot {shot.sequence} has no zero-cost route and paid routing is unavailable"
                )
            if running_cost + estimated > policy.max_total_provider_cost_usd and estimated > 0:
                raise AdaptiveProductionError("adaptive shot plan would exceed total provider hard cap")
            running_cost += estimated
            routes.append(
                RoutedShot(
                    shot=shot,
                    provider_id=chosen.provider_id,
                    model_id=chosen.model_id,
                    lane=lane,
                    estimated_cost_usd=estimated,
                    estimated_credits=estimated * policy.credits_per_usd,
                )
            )
        return ShotRoutingPlan(
            routes=tuple(routes),
            generated_seconds=sum(route.shot.duration_seconds for route in routes),
            estimated_provider_cost_usd=running_cost,
            estimated_credits=running_cost * policy.credits_per_usd,
        )


def parse_pricing_skus(values: Mapping[str, object]) -> Mapping[str, Decimal]:
    """Normalize live catalog pricing without guessing unknown pricing units."""

    normalized: dict[str, Decimal] = {}
    for key, raw in values.items():
        _require_text("pricing SKU", key)
        price = _decimal_price(raw)
        if price is None:
            raise AdaptiveProductionError(f"invalid live catalog price for {key}")
        normalized[key] = price
    return MappingProxyType(normalized)


def _decimal_price(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if not isinstance(value, (str, int, float, Decimal)):
        return None
    try:
        price = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not price.is_finite() or price < Decimal("0"):
        return None
    return price


def _require_text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise AdaptiveProductionError(f"{name} must be non-blank without surrounding whitespace")
