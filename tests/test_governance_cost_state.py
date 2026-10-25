from __future__ import annotations

from pathlib import Path

from services.control_plane.migrations import migrate_database
from services.governance import GovernedRuntimeGateway
from services.runtime import GovernedRuntime


def _gateway(tmp_path: Path) -> GovernedRuntimeGateway:
    runtime_path = tmp_path / "runtime.sqlite3"
    migrate_database(runtime_path)
    return GovernedRuntimeGateway(
        tmp_path / "governance.sqlite3",
        GovernedRuntime(runtime_path),
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


def test_governance_state_exposes_truthful_usage_projection(tmp_path: Path) -> None:
    gateway = _gateway(tmp_path)
    state = gateway.state()
    usage = state["usage"]
    assert isinstance(usage, dict)
    assert usage["schema_version"] == "ilaios.usage-stats.v1"
    assert usage["scope"] == "local_authenticated_control_plane"
    assert usage["route_count"] == 0
    assert usage["costs"] == {
        "coverage": "explicit_currency_only",
        "currency": "USD",
        "total_cost": None,
        "record_count": 0,
    }
    coverage = usage["coverage"]
    assert isinstance(coverage, dict)
    assert coverage["tokens"] == "unavailable"
    assert coverage["latency"] == "unavailable"
    assert coverage["models"] == "unavailable"
    assert coverage["evidence"] == "unavailable"
