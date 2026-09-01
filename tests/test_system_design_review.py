"""Tests for ILAIOS architecture and failure review rules."""

from __future__ import annotations

from src.system_design.architecture_reviewer import (
    ArchitectureReviewInput,
    review_architecture,
)
from src.system_design.bottleneck_detector import BottleneckInput, detect_bottlenecks
from src.system_design.failure_analyzer import FailureScenario, analyze_failures


def _codes(data: ArchitectureReviewInput) -> set[str]:
    return {issue.code for issue in review_architecture(data)}


def test_high_slo_rejects_single_failure_domain() -> None:
    codes = _codes(
        ArchitectureReviewInput(
            availability_slo=0.9999,
            failure_domain_count=1,
            database_replica_count=0,
            has_rate_limiting=True,
            has_overload_protection=True,
            has_observability=True,
            has_sli_slo_monitoring=True,
            has_secrets_boundary=True,
            has_trust_boundaries=True,
            rto_defined=True,
            rpo_defined=True,
        )
    )
    assert "HIGH_SLO_SINGLE_FAILURE_DOMAIN" in codes
    assert "HIGH_SLO_DATABASE_REDUNDANCY_MISSING" in codes


def test_queue_requires_idempotency_bounded_retries_and_dead_letter_handling() -> None:
    codes = _codes(
        ArchitectureReviewInput(
            uses_queue=True,
            has_rate_limiting=True,
            has_overload_protection=True,
            has_observability=True,
            has_sli_slo_monitoring=True,
            has_secrets_boundary=True,
            has_trust_boundaries=True,
            rto_defined=True,
            rpo_defined=True,
        )
    )
    assert {
        "QUEUE_IDEMPOTENCY_MISSING",
        "UNBOUNDED_RETRY_RISK",
        "DEAD_LETTER_HANDLING_MISSING",
    } <= codes


def test_cache_requires_invalidation_and_stampede_controls() -> None:
    codes = _codes(
        ArchitectureReviewInput(
            uses_cache=True,
            has_rate_limiting=True,
            has_overload_protection=True,
            has_observability=True,
            has_sli_slo_monitoring=True,
            has_secrets_boundary=True,
            has_trust_boundaries=True,
            rto_defined=True,
            rpo_defined=True,
        )
    )
    assert "CACHE_INVALIDATION_UNRESOLVED" in codes
    assert "CACHE_STAMPEDE_CONTROL_MISSING" in codes


def test_database_sharding_requires_benchmark_evidence() -> None:
    codes = _codes(
        ArchitectureReviewInput(
            proposes_database_sharding=True,
            has_rate_limiting=True,
            has_overload_protection=True,
            has_observability=True,
            has_sli_slo_monitoring=True,
            has_secrets_boundary=True,
            has_trust_boundaries=True,
            rto_defined=True,
            rpo_defined=True,
        )
    )
    assert "PREMATURE_SHARDING" in codes


def test_governed_execution_bypass_is_critical() -> None:
    issues = review_architecture(
        ArchitectureReviewInput(bypasses_governed_execution=True)
    )
    finding = next(
        issue for issue in issues if issue.code == "ILAIOS_GOVERNANCE_BYPASS"
    )
    assert finding.severity == "critical"


def test_bottleneck_detector_uses_supplied_evidence() -> None:
    findings = detect_bottlenecks(
        BottleneckInput(
            app_utilization=0.91,
            database_connection_utilization=0.80,
            cache_hit_ratio=0.40,
            queue_oldest_message_seconds=80,
            queue_slo_seconds=100,
            single_failure_domain=True,
        )
    )
    codes = {finding.code for finding in findings}
    assert "APP_SATURATION" in codes
    assert "DATABASE_CONNECTION_PRESSURE" in codes
    assert "LOW_CACHE_EFFECTIVENESS" in codes
    assert "QUEUE_LAG_PRESSURE" in codes
    assert "SINGLE_FAILURE_DOMAIN" in codes


def test_failure_analyzer_exposes_spof_recovery_and_retry_risks() -> None:
    findings = analyze_failures(
        (
            FailureScenario(
                component="queue",
                failure_mode="consumer outage",
                critical=True,
                redundant=False,
                detection_defined=False,
                recovery_defined=False,
                bounded_retry=False,
            ),
        )
    )
    codes = {finding.code for finding in findings}
    assert {
        "CRITICAL_SINGLE_POINT_OF_FAILURE",
        "FAILURE_DETECTION_MISSING",
        "RECOVERY_PATH_MISSING",
        "UNBOUNDED_RETRY_AMPLIFICATION",
        "BLAST_RADIUS_UNKNOWN",
    } <= codes
