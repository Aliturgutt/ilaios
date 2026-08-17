from __future__ import annotations

from decimal import Decimal

import pytest

from src.video_automation.adaptive_production import (
    AdaptiveProductionError,
    AdaptiveProviderRouter,
    AdaptiveShotPlanner,
    ProductionLane,
    ShotRole,
    ShotRoutingPolicy,
    VideoModelCapability,
    parse_pricing_skus,
)


def _capability(
    model_id: str,
    *,
    price: str,
    quality_rank: int = 50,
    audio: bool = True,
    references: bool = True,
) -> VideoModelCapability:
    return VideoModelCapability(
        provider_id="openrouter-video",
        model_id=model_id,
        supported_durations=tuple(range(2, 13)),
        supported_resolutions=("720p",),
        supported_aspect_ratios=("16:9",),
        supported_frame_images=("first_frame", "last_frame"),
        supports_audio=audio,
        supports_input_references=references,
        pricing_skus=parse_pricing_skus({"per-video-second": price}),
        quality_rank=quality_rank,
    )


def test_default_plan_prefers_short_shots_without_limiting_finished_duration() -> None:
    plan = AdaptiveShotPlanner().plan(180)

    assert plan.requested_duration_seconds == 180
    assert plan.generated_duration_seconds == 180
    assert all(4 <= shot.duration_seconds <= 6 for shot in plan.shots)
    assert plan.shots[0].role is ShotRole.ESTABLISHING
    assert plan.shots[-1].role is ShotRole.HERO


def test_provider_discrete_durations_are_respected() -> None:
    plan = AdaptiveShotPlanner().plan(30, supported_durations=(4, 6, 8))

    assert sum(shot.duration_seconds for shot in plan.shots) == 30
    assert {shot.duration_seconds for shot in plan.shots}.issubset({4, 6, 8})


def test_roles_drive_duration_and_continuity_requirements() -> None:
    plan = AdaptiveShotPlanner().plan(
        16,
        roles=(ShotRole.ESTABLISHING, ShotRole.DIALOGUE, ShotRole.TRANSITION),
    )

    assert tuple(shot.role for shot in plan.shots) == (
        ShotRole.ESTABLISHING,
        ShotRole.DIALOGUE,
        ShotRole.TRANSITION,
    )
    assert plan.shots[1].requires_native_audio
    assert plan.shots[1].requires_first_frame
    assert plan.shots[1].requires_last_frame
    assert plan.shots[1].requires_input_reference


def test_impossible_provider_duration_partition_fails_closed() -> None:
    with pytest.raises(AdaptiveProductionError, match="cannot be exactly partitioned"):
        AdaptiveShotPlanner().plan(7, supported_durations=(4, 6))


def test_router_prefers_explicit_zero_cost_model() -> None:
    plan = AdaptiveShotPlanner().plan(20)
    free = _capability("provider/free-video", price="0", quality_rank=40)
    paid = _capability("provider/paid-video", price="0.02", quality_rank=95)

    routed = AdaptiveProviderRouter().route(
        plan,
        (paid, free),
        ShotRoutingPolicy(),
        resolution="720p",
        aspect_ratio="16:9",
    )

    assert all(route.model_id == "provider/free-video" for route in routed.routes)
    assert all(route.lane is ProductionLane.FREE for route in routed.routes)
    assert routed.estimated_provider_cost_usd == Decimal("0")


def test_paid_route_requires_explicit_hard_caps() -> None:
    with pytest.raises(AdaptiveProductionError, match="hard caps"):
        ShotRoutingPolicy(allow_paid=True)


def test_paid_route_uses_cost_for_standard_shots_and_quality_for_hero() -> None:
    plan = AdaptiveShotPlanner().plan(12, roles=(ShotRole.CINEMATIC, ShotRole.HERO))
    economy = _capability("provider/economy", price="0.01", quality_rank=50)
    quality = _capability("provider/quality", price="0.02", quality_rank=95)
    policy = ShotRoutingPolicy(
        allow_paid=True,
        max_total_provider_cost_usd=Decimal("1.00"),
        max_cost_per_shot_usd=Decimal("0.20"),
    )

    routed = AdaptiveProviderRouter().route(
        plan,
        (quality, economy),
        policy,
        resolution="720p",
        aspect_ratio="16:9",
    )

    assert routed.routes[0].model_id == "provider/economy"
    assert routed.routes[0].lane is ProductionLane.STANDARD
    assert routed.routes[1].model_id == "provider/quality"
    assert routed.routes[1].lane is ProductionLane.PREMIUM
    assert routed.estimated_provider_cost_usd > Decimal("0")


def test_unknown_pricing_units_cannot_be_used_for_paid_budget_estimate() -> None:
    plan = AdaptiveShotPlanner().plan(10)
    unknown = VideoModelCapability(
        provider_id="openrouter-video",
        model_id="provider/unknown-pricing",
        supported_durations=tuple(range(2, 13)),
        supported_resolutions=("720p",),
        supported_aspect_ratios=("16:9",),
        supported_frame_images=("first_frame", "last_frame"),
        supports_audio=True,
        supports_input_references=True,
        pricing_skus=parse_pricing_skus({"generate": "0.50"}),
    )
    policy = ShotRoutingPolicy(
        allow_paid=True,
        max_total_provider_cost_usd=Decimal("10"),
        max_cost_per_shot_usd=Decimal("10"),
    )

    with pytest.raises(AdaptiveProductionError, match="no zero-cost route"):
        AdaptiveProviderRouter().route(
            plan,
            (unknown,),
            policy,
            resolution="720p",
            aspect_ratio="16:9",
        )
