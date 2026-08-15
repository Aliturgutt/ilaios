"""RAG.14 FinOps evidence must use observed usage, live rates and a hard budget."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from services.rag14_finops_evidence import FinOpsEvidenceError, _usd_rate_for_usage


def _price_list(usage: str, unit: str, rate: str) -> dict[str, object]:
    return {
        "products": {
            "sku-1": {"attributes": {"usagetype": usage}},
        },
        "terms": {
            "OnDemand": {
                "sku-1": {
                    "term-1": {
                        "priceDimensions": {
                            "dimension-1": {
                                "unit": unit,
                                "pricePerUnit": {"USD": rate},
                            }
                        }
                    }
                }
            }
        },
    }


def test_price_parser_accepts_one_exact_public_rate() -> None:
    rate = _usd_rate_for_usage(
        _price_list("EUC1-Fargate-vCPU-Hours:perCPU", "hours", "0.123"),
        usage_contains="Fargate-vCPU-Hours",
        unit="hours",
    )

    assert rate == Decimal("0.123")


def test_price_parser_fails_closed_on_ambiguous_rates() -> None:
    payload = cast(
        dict[str, Any],
        _price_list("EUC1-Fargate-vCPU-Hours:perCPU", "hours", "0.123"),
    )
    products = cast(dict[str, Any], payload["products"])
    products["sku-2"] = {
        "attributes": {"usagetype": "EUC1-Fargate-vCPU-Hours:perCPU"}
    }
    terms = cast(dict[str, Any], payload["terms"])
    on_demand = cast(dict[str, Any], terms["OnDemand"])
    on_demand["sku-2"] = {
        "term-2": {
            "priceDimensions": {
                "dimension-2": {
                    "unit": "hours",
                    "pricePerUnit": {"USD": "0.456"},
                }
            }
        }
    }

    with pytest.raises(FinOpsEvidenceError, match="expected one AWS USD rate"):
        _usd_rate_for_usage(
            cast(dict[str, object], payload),
            usage_contains="Fargate-vCPU-Hours",
            unit="hours",
        )


def test_finops_source_has_no_hardcoded_currency_rates() -> None:
    repository = Path(__file__).resolve().parents[1]
    source = (repository / "services/rag14_finops_evidence.py").read_text(
        encoding="utf-8"
    )

    assert "pricing.us-east-1.amazonaws.com" in source
    assert "RAG14_MAX_CANARY_USD" in source
    assert "billed_duration_seconds" in source
    assert "vcpu_seconds" in source
    assert "memory_gib_seconds" in source
    assert "efs_state_bytes" in source
    assert '"budget_guard_active": True' in source
    assert '"currency_cost_claimed": True' in source
    assert '"aws_compute_cost_is_zero": False' in source
    assert "SELF_HOSTED_NO_EXTERNAL_EMBEDDING_API_FEE" in source
