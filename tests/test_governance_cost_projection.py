from __future__ import annotations

import json

import pytest

from services.governance.cost_projection import CostProjectionError, project_explicit_costs


def _stored(result: dict[str, object]) -> str:
    return json.dumps({"_ilaios_admission": {"schema_version": 1}, "result": result})


def test_cost_projection_sums_only_explicit_usd_and_microusd() -> None:
    state = project_explicit_costs(
        (
            ("req-usd", _stored({"actual_cost_usd": 1.25, "actual_minor": 999999})),
            ("req-micro", _stored({"cost_microusd": 750_000, "reserved_minor": 888888})),
        )
    )

    assert state["currency"] == "USD"
    assert state["coverage"] == "explicit_currency_only"
    assert state["total_cost_usd"] == 2.0
    assert state["records"] == [
        {
            "request_id": "req-usd",
            "amount_usd": 1.25,
            "source_field": "actual_cost_usd",
            "source_unit": "USD",
        },
        {
            "request_id": "req-micro",
            "amount_usd": 0.75,
            "source_field": "cost_microusd",
            "source_unit": "microUSD",
        },
    ]


def test_cost_projection_does_not_treat_opaque_minor_units_as_usd() -> None:
    state = project_explicit_costs(
        (
            (
                "req-opaque",
                _stored(
                    {
                        "reserved_minor": 5000,
                        "actual_minor": 4500,
                        "quoted_minor": 6000,
                    }
                ),
            ),
        )
    )

    assert state == {
        "currency": "USD",
        "coverage": "explicit_currency_only",
        "records": [],
    }
    assert "total_cost_usd" not in state


def test_cost_projection_prefers_one_explicit_field_per_request() -> None:
    state = project_explicit_costs(
        (
            (
                "req-one",
                _stored(
                    {
                        "actual_cost_usd": 3.0,
                        "total_cost_usd": 99.0,
                        "cost_microusd": 2_000_000,
                    }
                ),
            ),
        )
    )

    assert state["total_cost_usd"] == 3.0
    records = state["records"]
    assert isinstance(records, list)
    assert len(records) == 1


def test_cost_projection_rejects_untrusted_explicit_money_values() -> None:
    for value in (-1, float("inf"), float("nan"), True, "1.25"):
        with pytest.raises(CostProjectionError):
            project_explicit_costs((("req-invalid", _stored({"cost_usd": value})),))


def test_cost_projection_fails_closed_on_malformed_persisted_result() -> None:
    with pytest.raises(CostProjectionError, match="malformed"):
        project_explicit_costs((("req-bad", "not-json"),))

    with pytest.raises(CostProjectionError, match="malformed"):
        project_explicit_costs((("req-bad", json.dumps({"result": [1, 2, 3]})),))
