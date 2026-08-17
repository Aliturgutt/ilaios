"""Tests for the bounded ILAIOS system-design pipeline."""

from __future__ import annotations

import pytest

from src.system_design.capacity_analyzer import CapacityInput
from src.system_design.pipeline import SystemDesignRequest, run_system_design


def test_pipeline_builds_schema_only_diagram_contract() -> None:
    result = run_system_design(
        SystemDesignRequest(
            system_id="million-user-web",
            capacity=CapacityInput(
                concurrent_users=100_000,
                requests_per_user_per_second=0.1,
                peak_factor=2,
                sustainable_rps_per_instance=1_000,
                availability_slo=0.9999,
            ),
            availability_slo=0.9999,
            asynchronous_workload_fraction=0.2,
            latency_slo_ms=250,
        )
    )
    assert result.architecture["diagram_contract"] == {
        "consumer_skill": "ilaios-diagram-design",
        "coupling": "schema_only",
    }
    node_ids = {node["id"] for node in result.architecture["nodes"]}
    assert "cache" in node_ids
    assert "work-queue" in node_ids
    assert "database-replica" in node_ids
    assert "representative_load_test" in result.evidence_required
    assert "LOAD_TEST_EVIDENCE_MISSING" in result.review_issue_codes


def test_pipeline_does_not_claim_actionable_capacity_from_user_count_alone() -> None:
    result = run_system_design(
        SystemDesignRequest(
            system_id="ambiguous-demand",
            capacity=CapacityInput(
                concurrent_users=1_000_000,
                availability_slo=0.999,
            ),
            availability_slo=0.999,
        )
    )
    assert result.capacity.peak_rps is None
    assert not result.capacity.is_actionable
    decision = result.architecture["decisions"][0]
    assert decision["confidence"] == "low"
    assert decision["evidence_status"] == "estimated"


def test_pipeline_keeps_database_sharding_out_without_evidence() -> None:
    result = run_system_design(
        SystemDesignRequest(
            system_id="write-heavy",
            capacity=CapacityInput(
                requests_per_second=20_000,
                peak_factor=2,
                read_ratio=0.2,
                write_ratio=0.8,
                availability_slo=0.999,
            ),
            availability_slo=0.999,
        )
    )
    assert any(
        item["category"] == "database"
        and item["decision"] == "do not shard by default"
        for item in result.architecture["decisions"]
    )


def test_pipeline_rejects_conflicting_availability_truth() -> None:
    with pytest.raises(ValueError, match="availability_slo must match"):
        run_system_design(
            SystemDesignRequest(
                system_id="bad-slo",
                capacity=CapacityInput(
                    requests_per_second=10,
                    availability_slo=0.99,
                ),
                availability_slo=0.999,
            )
        )
