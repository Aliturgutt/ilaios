"""Tests for bounded Commerce/Growth Factory governance and cost gates."""

import pytest

from services.commerce_growth_factory import CommerceGrowthError, CommerceGrowthFactory


def _factory() -> CommerceGrowthFactory:
    factory = CommerceGrowthFactory()
    factory.register_source(
        "market-evidence",
        locator="fixture://commerce/market-evidence",
        content=b"bounded market evidence",
        trusted=True,
    )
    return factory


def test_growth_plan_is_deterministic_and_review_projection_preserves_provenance() -> None:
    first = _factory()
    first_plan = first.propose(
        "plan-1",
        objective="Explain a verified product capability.",
        audience="Technical founders",
        channels=("content_draft", "sales_enablement"),
        source_ids=("market-evidence",),
    )
    approved = first.approve_for_review("plan-1", approver="human-owner")
    projection = first.review_projection("plan-1")

    second = _factory()
    second_plan = second.propose(
        "plan-1",
        objective="Explain a verified product capability.",
        audience="Technical founders",
        channels=("content_draft", "sales_enablement"),
        source_ids=("market-evidence",),
    )

    assert first_plan.plan_sha256 == second_plan.plan_sha256
    assert approved.approved_for_review is True
    assert approved.external_applied is False
    assert projection["plan_sha256"] == approved.plan_sha256
    assert projection["paid_spend_cents"] == 0
    assert projection["sources"][0]["source_id"] == "market-evidence"
    assert len(projection["sources"][0]["content_sha256"]) == 64


def test_paid_spend_and_unsupported_channels_fail_closed() -> None:
    factory = _factory()
    with pytest.raises(CommerceGrowthError, match="paid spend"):
        factory.propose(
            "paid-plan",
            objective="Paid acquisition",
            audience="Prospects",
            channels=("content_draft",),
            source_ids=("market-evidence",),
            paid_spend_cents=1,
        )
    with pytest.raises(CommerceGrowthError, match="unsupported growth channels"):
        factory.propose(
            "unsupported-plan",
            objective="Unsupported channel",
            audience="Prospects",
            channels=("ad_network",),
            source_ids=("market-evidence",),
        )


def test_unknown_untrusted_and_duplicate_sources_fail_closed() -> None:
    factory = _factory()
    factory.register_source(
        "untrusted",
        locator="fixture://commerce/untrusted",
        content=b"untrusted evidence",
        trusted=False,
    )
    with pytest.raises(CommerceGrowthError, match="unknown sources"):
        factory.propose(
            "missing-plan",
            objective="Missing evidence",
            audience="Prospects",
            channels=("email_draft",),
            source_ids=("missing",),
        )
    with pytest.raises(CommerceGrowthError, match="sources must be trusted"):
        factory.propose(
            "untrusted-plan",
            objective="Untrusted evidence",
            audience="Prospects",
            channels=("email_draft",),
            source_ids=("untrusted",),
        )
    with pytest.raises(CommerceGrowthError, match="duplicates"):
        factory.propose(
            "duplicate-plan",
            objective="Duplicate evidence",
            audience="Prospects",
            channels=("email_draft",),
            source_ids=("market-evidence", "market-evidence"),
        )


def test_unapproved_projection_and_external_mutation_are_forbidden() -> None:
    factory = _factory()
    factory.propose(
        "plan-1",
        objective="Review-only outreach draft",
        audience="Prospects",
        channels=("email_draft",),
        source_ids=("market-evidence",),
    )
    with pytest.raises(CommerceGrowthError, match="only approved growth plans"):
        factory.review_projection("plan-1")
    factory.approve_for_review("plan-1", approver="human-owner")
    with pytest.raises(CommerceGrowthError, match="external commerce/growth mutation is forbidden"):
        factory.apply_external("plan-1")
