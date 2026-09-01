"""Deterministic orchestration for the ILAIOS system-design analysis skill."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .architecture_reviewer import ArchitectureReviewInput, review_architecture
from .capacity_analyzer import CapacityEstimate, CapacityInput, analyze_capacity


@dataclass(frozen=True, slots=True)
class SystemDesignRequest:
    """Bounded design request. It performs analysis and creates no side effects."""

    system_id: str
    capacity: CapacityInput
    availability_slo: float
    internet_facing: bool = True
    asynchronous_workload_fraction: float = 0.0
    latency_slo_ms: int | None = None


@dataclass(frozen=True, slots=True)
class SystemDesignResult:
    """Architecture artifact suitable for evidence storage and diagram rendering."""

    architecture: dict[str, Any]
    capacity: CapacityEstimate
    review_issue_codes: tuple[str, ...]
    evidence_required: tuple[str, ...]


def _node(
    node_id: str,
    kind: str,
    layer: str,
    *,
    stateful: bool,
    failure_domain: str,
) -> dict[str, Any]:
    return {
        "id": node_id,
        "kind": kind,
        "layer": layer,
        "stateful": stateful,
        "failure_domain": failure_domain,
        "criticality": "critical",
    }


def run_system_design(request: SystemDesignRequest) -> SystemDesignResult:
    """Build a bounded reference architecture from explicit demand assumptions.

    The function intentionally does not provision infrastructure, choose a cloud
    provider, fetch live prices or claim that the design supports a traffic level.
    Those are later governed execution and evidence steps.
    """

    if not request.system_id.strip():
        raise ValueError("system_id must be non-empty")
    if not 0 <= request.asynchronous_workload_fraction <= 1:
        raise ValueError("asynchronous_workload_fraction must be in [0, 1]")
    if request.latency_slo_ms is not None and request.latency_slo_ms <= 0:
        raise ValueError("latency_slo_ms must be positive when supplied")
    if abs(request.capacity.availability_slo - request.availability_slo) > 1e-12:
        raise ValueError("capacity and system availability_slo must match")

    capacity = analyze_capacity(request.capacity)
    peak_rps = capacity.peak_rps
    high_availability = request.availability_slo >= 0.9999
    use_cache = (
        peak_rps is not None
        and peak_rps >= 1_000
        and request.capacity.read_ratio >= 0.7
    )
    use_queue = (
        request.asynchronous_workload_fraction >= 0.05
        or (peak_rps is not None and peak_rps >= 5_000)
    )
    failure_domain_count = 2 if high_availability else 1

    nodes = [
        _node(
            "edge-gateway",
            "gateway",
            "edge",
            stateful=False,
            failure_domain="multi" if high_availability else "default",
        ),
        _node(
            "rate-limiter",
            "rate_limiter",
            "edge",
            stateful=False,
            failure_domain="multi" if high_availability else "default",
        ),
        _node(
            "application",
            "application",
            "compute",
            stateful=False,
            failure_domain="multi" if high_availability else "default",
        ),
        _node(
            "primary-database",
            "database",
            "data",
            stateful=True,
            failure_domain="primary",
        ),
        _node(
            "observability",
            "observability",
            "operations",
            stateful=True,
            failure_domain="independent",
        ),
    ]
    edges: list[dict[str, str]] = [
        {"from": "edge-gateway", "to": "rate-limiter", "kind": "control_flow"},
        {"from": "rate-limiter", "to": "application", "kind": "control_flow"},
        {"from": "application", "to": "primary-database", "kind": "data_flow"},
        {"from": "application", "to": "observability", "kind": "telemetry"},
    ]

    if high_availability:
        nodes.append(
            _node(
                "database-replica",
                "database_replica",
                "data",
                stateful=True,
                failure_domain="secondary",
            )
        )
        edges.append(
            {
                "from": "primary-database",
                "to": "database-replica",
                "kind": "replication",
            }
        )
    if use_cache:
        nodes.append(
            _node(
                "cache",
                "cache",
                "data",
                stateful=True,
                failure_domain="default",
            )
        )
        edges.append({"from": "application", "to": "cache", "kind": "data_flow"})
    if use_queue:
        nodes.append(
            _node(
                "work-queue",
                "queue",
                "workflow",
                stateful=True,
                failure_domain="default",
            )
        )
        nodes.append(
            _node(
                "async-worker",
                "worker",
                "compute",
                stateful=False,
                failure_domain="multi" if high_availability else "default",
            )
        )
        edges.extend(
            (
                {"from": "application", "to": "work-queue", "kind": "data_flow"},
                {"from": "work-queue", "to": "async-worker", "kind": "data_flow"},
                {
                    "from": "async-worker",
                    "to": "primary-database",
                    "kind": "data_flow",
                },
            )
        )

    reviewer_input = ArchitectureReviewInput(
        internet_facing=request.internet_facing,
        availability_slo=request.availability_slo,
        failure_domain_count=failure_domain_count,
        has_authentication=True,
        has_authorization=True,
        has_rate_limiting=True,
        has_overload_protection=True,
        has_observability=True,
        has_sli_slo_monitoring=True,
        has_secrets_boundary=True,
        has_trust_boundaries=True,
        uses_cache=use_cache,
        has_cache_invalidation_strategy=use_cache,
        has_stampede_protection=use_cache,
        uses_queue=use_queue,
        has_idempotency=use_queue,
        has_bounded_retries=use_queue,
        has_dead_letter_handling=use_queue,
        database_replica_count=1 if high_availability else 0,
        proposes_database_sharding=False,
        sharding_evidence_supplied=False,
        rto_defined=True,
        rpo_defined=True,
        budget_defined=request.capacity.monthly_budget is not None,
        cost_evidence_supplied=request.capacity.estimated_monthly_cost is not None,
        load_test_evidence_supplied=False,
        bypasses_governed_execution=False,
    )
    review = review_architecture(reviewer_input)

    decisions: list[dict[str, str]] = [
        {
            "category": "capacity",
            "decision": "size from explicit or derived RPS, never user count alone",
            "rationale": "throughput demand must be explicit before implementation",
            "confidence": "medium" if capacity.is_actionable else "low",
            "evidence_status": "estimated",
        },
        {
            "category": "database",
            "decision": "do not shard by default",
            "rationale": "sharding requires benchmark evidence of a real bottleneck",
            "confidence": "high",
            "evidence_status": "policy",
        },
    ]
    if use_cache:
        decisions.append(
            {
                "category": "cache",
                "decision": (
                    "cache is a candidate optimization with invalidation controls"
                ),
                "rationale": "read-heavy high-throughput heuristic was met",
                "confidence": "low",
                "evidence_status": "heuristic",
            }
        )
    if use_queue:
        decisions.append(
            {
                "category": "queue",
                "decision": "use bounded asynchronous work with idempotency and DLQ",
                "rationale": "async workload or high-throughput heuristic was met",
                "confidence": "low",
                "evidence_status": "heuristic",
            }
        )

    architecture: dict[str, Any] = {
        "schema_version": "1.0",
        "system_id": request.system_id,
        "demand": {
            "concurrent_users": request.capacity.concurrent_users,
            "base_rps": capacity.base_rps,
            "peak_rps": capacity.peak_rps,
            "latency_slo_ms": request.latency_slo_ms,
            "availability_slo": request.availability_slo,
        },
        "nodes": nodes,
        "edges": edges,
        "decisions": decisions,
        "risks": [asdict(issue) for issue in review],
        "evidence_required": [
            "representative_load_test",
            "failure_injection_or_recovery_drill",
            "database_benchmark",
            "sli_slo_observability_validation",
            "measured_or_quoted_cost_evidence",
        ],
        "diagram_contract": {
            "consumer_skill": "ilaios-diagram-design",
            "coupling": "schema_only",
        },
    }
    return SystemDesignResult(
        architecture=architecture,
        capacity=capacity,
        review_issue_codes=tuple(issue.code for issue in review),
        evidence_required=tuple(architecture["evidence_required"]),
    )
