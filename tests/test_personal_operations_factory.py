"""Tests for bounded Personal Operations Factory authority and approval gates."""

import pytest

from services.personal_operations_factory import PersonalOperationsError, PersonalOperationsFactory


def _steps() -> tuple[tuple[str, str, str, str], ...]:
    return (
        ("step-1", "checklist_draft", "project://ilaios", "Review release evidence"),
        ("step-2", "reminder_draft", "local://owner", "Check pending approval"),
    )


def test_plan_is_deterministic_and_review_projection_contains_hashed_payloads() -> None:
    first = PersonalOperationsFactory()
    first_plan = first.propose(
        "plan-1",
        objective="Prepare bounded operational follow-up.",
        steps=_steps(),
    )
    approved = first.approve_for_review("plan-1", approver="human-owner")
    projection = first.review_projection("plan-1")

    second = PersonalOperationsFactory()
    second_plan = second.propose(
        "plan-1",
        objective="Prepare bounded operational follow-up.",
        steps=_steps(),
    )

    assert first_plan.plan_sha256 == second_plan.plan_sha256
    assert approved.approved_for_review is True
    assert approved.external_applied is False
    assert projection["external_applied"] is False
    assert projection["steps"][0]["step_id"] == "step-1"
    assert len(projection["steps"][0]["payload_sha256"]) == 64


def test_unsupported_action_and_duplicate_step_ids_fail_closed() -> None:
    factory = PersonalOperationsFactory()
    with pytest.raises(PersonalOperationsError, match="unsupported personal operation action"):
        factory.propose(
            "unsafe-plan",
            objective="Unsafe external action",
            steps=(("step-1", "send_email", "external://mail", "send now"),),
        )
    with pytest.raises(PersonalOperationsError, match="step_id must be unique"):
        factory.propose(
            "duplicate-plan",
            objective="Duplicate steps",
            steps=(
                ("step-1", "note_draft", "local://notes", "one"),
                ("step-1", "note_draft", "local://notes", "two"),
            ),
        )


def test_empty_plan_and_duplicate_plan_ids_fail_closed() -> None:
    factory = PersonalOperationsFactory()
    with pytest.raises(PersonalOperationsError, match="at least one step"):
        factory.propose("empty-plan", objective="Empty", steps=())
    factory.propose("plan-1", objective="First", steps=_steps())
    with pytest.raises(PersonalOperationsError, match="plan_id already exists"):
        factory.propose("plan-1", objective="Second", steps=_steps())


def test_unapproved_projection_and_external_mutation_are_forbidden() -> None:
    factory = PersonalOperationsFactory()
    factory.propose("plan-1", objective="Review-only", steps=_steps())
    with pytest.raises(PersonalOperationsError, match="only approved operation plans"):
        factory.review_projection("plan-1")
    factory.approve_for_review("plan-1", approver="human-owner")
    with pytest.raises(PersonalOperationsError, match="external personal-operation mutation is forbidden"):
        factory.apply_external("plan-1")
