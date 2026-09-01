from __future__ import annotations

from pathlib import Path

from services.governance import GovernedRuntimeGateway
from services.runtime import GovernedRuntime


def _gateway(tmp_path: Path) -> GovernedRuntimeGateway:
    return GovernedRuntimeGateway(
        tmp_path / "governance.sqlite3",
        GovernedRuntime(tmp_path / "runtime.sqlite3"),
        hard_cap_minor=10_000,
    )


def _submit(gateway: GovernedRuntimeGateway, request_id: str) -> None:
    gateway.submit(
        request_id,
        "principal-requester",
        "video-agent",
        "video-skill",
        "video",
        {"goal_id": "goal-1", "job_id": request_id},
        (),
        risk="medium",
    )
    gateway.authorize_billable(request_id)


def test_governance_state_projects_explicit_microusd_for_desktop(tmp_path: Path) -> None:
    gateway = _gateway(tmp_path)
    _submit(gateway, "request-video")
    gateway.reconcile_billable(
        "request-video",
        actual_minor=10,
        status="executed",
        result={
            "total_cost_microusd": 1_500_000,
            "provider_boundary": "provider-video",
            "actual_minor": 10,
        },
    )

    state = gateway.state()
    assert state["costs"] == {
        "currency": "USD",
        "coverage": "explicit_currency_only",
        "records": [
            {
                "request_id": "request-video",
                "amount_usd": 1.5,
                "source_field": "total_cost_microusd",
                "source_unit": "microUSD",
            }
        ],
        "total_cost_usd": 1.5,
    }


def test_governance_state_keeps_opaque_minor_ledger_out_of_usd(tmp_path: Path) -> None:
    gateway = _gateway(tmp_path)
    _submit(gateway, "request-opaque")
    gateway.reconcile_billable(
        "request-opaque",
        actual_minor=10,
        status="executed",
        result={
            "reserved_minor": 10,
            "actual_minor": 10,
            "quoted_minor": 10,
        },
    )

    state = gateway.state()
    costs = state["costs"]
    assert isinstance(costs, dict)
    assert costs == {
        "currency": "USD",
        "coverage": "explicit_currency_only",
        "records": [],
    }
    assert "total_cost_usd" not in costs
    assert state["ledger"] != {}
