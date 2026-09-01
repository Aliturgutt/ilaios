from pathlib import Path

import pytest

from services.control_plane.api import ControlPlane, ControlPlaneConfig, ControlPlaneError
from services.control_plane.proposals import (
    BudgetEnvelope,
    DataClass,
    ProposedTask,
    RiskClass,
)


def _plane(tmp_path: Path) -> ControlPlane:
    return ControlPlane(ControlPlaneConfig(tmp_path / "control-plane.db", "token"))


def test_goal_admission_compiles_amateur_web_prompt(tmp_path: Path) -> None:
    plane = _plane(tmp_path)

    goal = plane.create_goal("token", "bana modern bir diş kliniği sitesi yap")

    assert goal.objective == "website task: bana modern bir diş kliniği sitesi yap"
    assert plane.get_goal("token", goal.goal_id) == goal


def test_goal_admission_compiles_video_prompt_for_same_governed_flow(tmp_path: Path) -> None:
    plane = _plane(tmp_path)

    goal = plane.create_goal("token", "ürünüm için 20 saniye video yap")
    job = plane.create_job("token", goal.goal_id)

    assert goal.objective == "ürünüm için 20 saniye video yap"
    assert job.goal_id == goal.goal_id
    assert job.state.value == "PENDING"


def test_compiled_goal_flows_into_bounded_non_authoritative_proposal(
    tmp_path: Path,
) -> None:
    plane = _plane(tmp_path)
    goal = plane.create_goal("token", "bana modern bir web sitesi yap")
    job = plane.create_job("token", goal.goal_id)

    proposal = plane.create_proposal(
        "token",
        goal.goal_id,
        acceptance_criteria=("validated finished product",),
        risk_class=RiskClass.LOW,
        data_class=DataClass.PUBLIC,
        budget=BudgetEnvelope(max_attempts=2, max_runtime_seconds=300),
        tasks=(ProposedTask("build", "build the requested product"),),
    )

    proposal_goal = proposal["goal"]
    assert isinstance(proposal_goal, dict)
    assert job.state.value == "PENDING"
    assert proposal_goal["objective"] == goal.objective
    assert proposal["privileged_execution_authorized"] is False
    assert [event["event_type"] for event in plane.list_events("token")] == [
        "goal.created",
        "job.created",
        "proposal.created",
    ]


def test_goal_admission_preserves_app_and_software_route_hints(tmp_path: Path) -> None:
    plane = _plane(tmp_path)

    app = plane.create_goal("token", "Windows için desktop app yap")
    software = plane.create_goal("token", "basit bir müşteri takip yazılımı yap")

    assert "desktop app" in app.objective
    assert "yazılım" in software.objective


def test_explicit_multi_capability_goal_is_admitted_without_false_clarification(
    tmp_path: Path,
) -> None:
    plane = _plane(tmp_path)

    goal = plane.create_goal("token", "bir web sitesi ve video yap")

    assert goal.objective.startswith("video website task:")


def test_general_existing_goal_behavior_is_backward_compatible(tmp_path: Path) -> None:
    plane = _plane(tmp_path)
    objective = "yarınki toplantı için hazırlık listesi çıkar"

    goal = plane.create_goal("token", objective)

    assert goal.objective == objective
    events = plane.list_events("token")
    assert events[-1]["payload"] == {"objective": objective}


def test_true_alternative_cross_domain_conflict_fails_closed_before_goal_creation(
    tmp_path: Path,
) -> None:
    plane = _plane(tmp_path)

    with pytest.raises(ControlPlaneError, match="clarification required") as captured:
        plane.create_goal("token", "web sitesi veya video yap")

    assert "web" in str(captured.value)
    assert "video" in str(captured.value)
    assert plane.list_events("token") == ()


def test_prompt_compiler_does_not_bypass_authentication(tmp_path: Path) -> None:
    plane = _plane(tmp_path)

    with pytest.raises(PermissionError):
        plane.create_goal("wrong-token", "web sitesi yap")

    assert plane.list_events("token") == ()
