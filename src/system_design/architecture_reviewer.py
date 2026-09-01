"""Rule-based review of system-design decisions against ILAIOS invariants."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ArchitectureReviewInput:
    """Declared controls and properties of a proposed architecture."""

    internet_facing: bool = True
    availability_slo: float = 0.999
    failure_domain_count: int = 1
    has_authentication: bool = True
    has_authorization: bool = True
    has_rate_limiting: bool = False
    has_overload_protection: bool = False
    has_observability: bool = False
    has_sli_slo_monitoring: bool = False
    has_secrets_boundary: bool = False
    has_trust_boundaries: bool = False
    uses_cache: bool = False
    has_cache_invalidation_strategy: bool = False
    has_stampede_protection: bool = False
    uses_queue: bool = False
    has_idempotency: bool = False
    has_bounded_retries: bool = False
    has_dead_letter_handling: bool = False
    database_replica_count: int = 0
    proposes_database_sharding: bool = False
    sharding_evidence_supplied: bool = False
    rto_defined: bool = False
    rpo_defined: bool = False
    budget_defined: bool = False
    cost_evidence_supplied: bool = False
    load_test_evidence_supplied: bool = False
    bypasses_governed_execution: bool = False


@dataclass(frozen=True, slots=True)
class ReviewIssue:
    code: str
    severity: str
    message: str


def _issue(code: str, severity: str, message: str) -> ReviewIssue:
    return ReviewIssue(code=code, severity=severity, message=message)


def review_architecture(data: ArchitectureReviewInput) -> tuple[ReviewIssue, ...]:
    """Review declared architecture properties without inventing missing evidence."""

    if not 0 < data.availability_slo <= 1:
        raise ValueError("availability_slo must be in (0, 1]")
    if data.failure_domain_count < 1:
        raise ValueError("failure_domain_count must be at least 1")
    if data.database_replica_count < 0:
        raise ValueError("database_replica_count must be non-negative")

    issues: list[ReviewIssue] = []

    if data.bypasses_governed_execution:
        issues.append(
            _issue(
                "ILAIOS_GOVERNANCE_BYPASS",
                "critical",
                "The design bypasses ILAIOS governed execution. Planning output may "
                "advise, but implementation side effects still require policy, budget, "
                "approval and evidence gates.",
            )
        )

    if data.internet_facing and not data.has_authentication:
        issues.append(
            _issue("AUTHENTICATION_MISSING", "critical", "Authentication is missing.")
        )
    if data.internet_facing and not data.has_authorization:
        issues.append(
            _issue("AUTHORIZATION_MISSING", "critical", "Authorization is missing.")
        )
    if data.internet_facing and not data.has_rate_limiting:
        issues.append(
            _issue(
                "RATE_LIMITING_MISSING",
                "high",
                "Internet-facing traffic has no declared rate-limiting control.",
            )
        )
    if data.internet_facing and not data.has_overload_protection:
        issues.append(
            _issue(
                "OVERLOAD_PROTECTION_MISSING",
                "high",
                "No overload-shedding or admission control is declared.",
            )
        )

    if data.availability_slo >= 0.9999 and data.failure_domain_count < 2:
        issues.append(
            _issue(
                "HIGH_SLO_SINGLE_FAILURE_DOMAIN",
                "critical",
                "A high availability target cannot rely on one failure domain.",
            )
        )
    if data.availability_slo >= 0.9999 and data.database_replica_count < 1:
        issues.append(
            _issue(
                "HIGH_SLO_DATABASE_REDUNDANCY_MISSING",
                "high",
                "High availability is declared without a database redundancy plan.",
            )
        )

    if data.uses_cache and not data.has_cache_invalidation_strategy:
        issues.append(
            _issue(
                "CACHE_INVALIDATION_UNRESOLVED",
                "high",
                "A cache is present without an explicit invalidation strategy.",
            )
        )
    if data.uses_cache and not data.has_stampede_protection:
        issues.append(
            _issue(
                "CACHE_STAMPEDE_CONTROL_MISSING",
                "medium",
                "A cache is present without stampede protection.",
            )
        )

    if data.uses_queue:
        if not data.has_idempotency:
            issues.append(
                _issue(
                    "QUEUE_IDEMPOTENCY_MISSING",
                    "high",
                    "Queued work has no idempotency contract.",
                )
            )
        if not data.has_bounded_retries:
            issues.append(
                _issue(
                    "UNBOUNDED_RETRY_RISK",
                    "critical",
                    "Queued work has no bounded retry/backoff policy.",
                )
            )
        if not data.has_dead_letter_handling:
            issues.append(
                _issue(
                    "DEAD_LETTER_HANDLING_MISSING",
                    "high",
                    "Queued work has no poison-message or dead-letter handling path.",
                )
            )

    if data.proposes_database_sharding and not data.sharding_evidence_supplied:
        issues.append(
            _issue(
                "PREMATURE_SHARDING",
                "medium",
                "Database sharding is proposed without benchmark evidence that simpler "
                "scaling strategies are insufficient.",
            )
        )

    if not data.has_observability:
        issues.append(
            _issue(
                "OBSERVABILITY_MISSING",
                "high",
                "The architecture lacks declared telemetry for verification and "
                "recovery.",
            )
        )
    if not data.has_sli_slo_monitoring:
        issues.append(
            _issue(
                "SLI_SLO_MONITORING_MISSING",
                "medium",
                "No SLI/SLO measurement contract is declared.",
            )
        )
    if not data.has_secrets_boundary:
        issues.append(
            _issue(
                "SECRETS_BOUNDARY_MISSING",
                "high",
                "Secrets are not separated from ordinary application "
                "data/configuration.",
            )
        )
    if not data.has_trust_boundaries:
        issues.append(
            _issue(
                "TRUST_BOUNDARIES_MISSING",
                "high",
                "Trust boundaries and untrusted-input transitions are not declared.",
            )
        )
    if not data.rto_defined or not data.rpo_defined:
        issues.append(
            _issue(
                "RECOVERY_OBJECTIVES_INCOMPLETE",
                "medium",
                "Both RTO and RPO are required to review recovery design.",
            )
        )
    if data.budget_defined and not data.cost_evidence_supplied:
        issues.append(
            _issue(
                "COST_EVIDENCE_MISSING",
                "medium",
                "Budget is declared without measured or quoted cost evidence.",
            )
        )
    if not data.load_test_evidence_supplied:
        issues.append(
            _issue(
                "LOAD_TEST_EVIDENCE_MISSING",
                "info",
                "Capacity estimates remain unverified until representative load tests "
                "pass.",
            )
        )

    return tuple(issues)
