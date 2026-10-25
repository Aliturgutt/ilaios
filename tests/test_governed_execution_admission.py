from __future__ import annotations

from pathlib import Path

import pytest

from services.control_plane.migrations import migrate_database
from services.governance import GateError, GovernedRuntimeGateway
from services.runtime import GovernedRuntime


def _gateway(tmp_path: Path) -> GovernedRuntimeGateway:
    state = tmp_path / "runtime.sqlite3"
    migrate_database(state)
    return GovernedRuntimeGateway(
        tmp_path / "governance.sqlite3",
        GovernedRuntime(state),
        hard_cap_minor=100,
    )


def _submit(gateway: GovernedRuntimeGateway, request_id: str, *, risk: str) -> None:
    gateway.submit(
        request_id,
        "principal-requester",
        "video-agent",
        "video-chain-v30",
        "video",
        {"goal_id": "goal-1", "job_id": "job-1"},
        (),
        risk=risk,
    )


def test_medium_admission_is_durable_and_does_not_fabricate_approval(
    tmp_path: Path,
) -> None:
    gateway = _gateway(tmp_path)
    _submit(gateway, "request-medium", risk="medium")

    admission = gateway.admission_snapshot("request-medium")
    assert admission == {
        "risk": "medium",
        "admission_decision": "ALLOW",
        "human_approval_required": False,
        "approval_proven": False,
        "admission_proven": True,
    }

    restarted = _gateway(tmp_path)
    assert restarted.admission_snapshot("request-medium") == admission
    assert restarted.authorize_billable("request-medium") == 10


def test_high_risk_remains_hitl_and_cannot_be_downgraded_at_execution(
    tmp_path: Path,
) -> None:
    gateway = _gateway(tmp_path)
    _submit(gateway, "request-high", risk="high")

    admission = gateway.admission_snapshot("request-high")
    assert admission["risk"] == "high"
    assert admission["human_approval_required"] is True
    assert admission["admission_proven"] is False
    with pytest.raises(GateError, match="durable human approval"):
        gateway.authorize_billable("request-high")

    with pytest.raises(GateError, match="independent human approver"):
        gateway.decide("request-high", "principal-requester", "approved")
    gateway.decide("request-high", "principal-approver", "approved")

    assert gateway.admission_snapshot("request-high")["admission_proven"] is True
    assert gateway.authorize_billable("request-high") == 10


def test_denial_is_terminal_and_medium_work_cannot_receive_fake_hitl(
    tmp_path: Path,
) -> None:
    high = _gateway(tmp_path)
    _submit(high, "request-denied", risk="high")
    high.decide("request-denied", "principal-approver", "denied")
    assert high.state()["work"] == [
        {
            "request_id": "request-denied",
            "requester_id": "principal-requester",
            "status": "denied",
        }
    ]
    with pytest.raises(GateError, match="cannot execute more than once"):
        high.authorize_billable("request-denied")

    other_root = tmp_path / "medium"
    medium = _gateway(other_root)
    _submit(medium, "request-medium", risk="medium")
    with pytest.raises(GateError, match="does not require human approval"):
        medium.decide("request-medium", "principal-approver", "approved")
